#!/usr/bin/env python3
"""nudge.py - the workflow's ambient reminder hook (M5, Decisions D-5 + D-7).

Claude Code runs this on two events (registered by `sync.py enable-workflow`):
  * UserPromptSubmit - before the model acts on a human turn. This is the ONLY channel that reaches
    a HUMAN in time (systemMessage renders here as "UserPromptSubmit says: ..."), so it emits BOTH a
    short human line (systemMessage) AND the model-facing context (additionalContext).
  * SessionStart (startup|resume|clear|compact) - a fresh or re-hydrated session. systemMessage is
    not proven to render here, so it emits additionalContext ONLY, and always injects.

What it injects: whether the current step OWES a challenge (D-5's job is "owed", not raw state - a
missing/stale receipt fires the reminder; a fresh one says "ready to advance"), followed by the
conductor's loop-and-rules slice (D-7: the model gets the how-to AND the prohibitions every time).

THE SAFETY SPINE (the honest floor, D-9):
  * stat-before-import (D-9(ii)): we STAT `.workflow/marker.json` INLINE - importing NOTHING - and
    if there is no task here we exit silently, emitting nothing (must-not #3: never nag an unrelated
    repo). No task, no import, no output.
  * fail LOUD, never silent (D-9(i) inverted for a running process): if a task IS present but the
    machinery below it is broken (workflow.py won't import, the marker is corrupt, the conductor
    sentinels are gone), we emit a visible "machinery is broken" notice - using ONLY nudge.py-local
    stdlib (json + print), calling ZERO workflow.py functions (the import is the thing that failed),
    and writing NO nudge-state (its writer lives in the dead module). That branch is TERMINAL: it
    cannot quiet itself, so it repeats every turn until the breakage is fixed - correct for a
    persistent fault. A crash we did NOT anticipate exits non-zero and the platform drops our output
    (D-9(i) accepted blindness) - never a hard block.
  * whitelist output (D-9(ii)): we emit EXACTLY systemMessage (UserPromptSubmit only) +
    hookSpecificOutput.{hookEventName, additionalContext}. Any other key would be a bug; a blacklist
    of "keys that block" was wrong three times, so this is a whitelist. Exit code is ALWAYS 0 - never
    `exit 2`, never a `decision`/`continue` field - so the hook can inform but never hard-block
    (must-not #1: warn, never block; the human keeps the wheel).
  * explicit root (the D-2 invariant): the project root comes from what the platform HANDS us
    ($CLAUDE_PROJECT_DIR, or stdin `cwd`), passed to workflow's readers EXPLICITLY - never a cwd
    walk-up, which for a hook launched from ~/.claude would bind the wrong project (or none), and a
    hook mis-root fails SILENTLY (the CLI's root-print guard is not in play here).

Standard library only. `import workflow` is a same-directory import (this file ships to
~/.claude/workflow/ beside workflow.py), so sys.path[0] already resolves it - but it happens ONLY
inside the guarded, marker-present branch, so a broken workflow.py can never stop the stat-and-exit.
"""

# json builds the whitelist output and parses stdin; os reads $CLAUDE_PROJECT_DIR; sys gives
# stdin/stdout + exit; hashlib powers the quiet-hash; Path does the inline marker stat. All stdlib.
import json
import os
import sys
import hashlib
from pathlib import Path

def _resolve_root(data):
    """Where is the project? Handed to us, never guessed: $CLAUDE_PROJECT_DIR first (the documented
    hook env var), then stdin `cwd` (the session's working dir). Returns a Path, or None when neither
    is present - in which case there is no project to nudge about. `.resolve()` canonicalizes the
    platform's path (env vs stdin disagree on slash direction; D-2a); the isinstance guard refuses a
    wrong-typed cwd (valid JSON, wrong shape) rather than crash."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    cwd = data.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd).resolve()
    return None


def _emit(event, additional_context, system_message=None):
    """Print the WHITELIST output and nothing else: hookSpecificOutput.{hookEventName,
    additionalContext}, plus systemMessage only when given (UserPromptSubmit). Building the dict
    literally - rather than starting from something and deleting keys - is what makes "no other key
    can appear" true by construction (D-9(ii))."""
    out = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": additional_context}}
    if system_message is not None:
        out["systemMessage"] = system_message
    sys.stdout.write(json.dumps(out))


def _emit_broken(event):
    """The fail-LOUD notice for a present-but-broken task. STDLIB ONLY - no workflow.py, no
    nudge-state write - because the import/read of workflow.py is exactly what failed, and its
    atomic-writer lives in that dead module (a write there would raise, exit non-zero, and the
    platform would then DISCARD this notice, collapsing "loud" back into silence)."""
    text = ("workflow machinery looks broken here: a task marker exists but its step/receipt could "
            "not be read (workflow.py did not import, the marker is corrupt, or the conductor "
            "sentinels are missing). Run `python workflow.py status` to diagnose.")
    system_message = "workflow machinery looks broken - run `workflow.py status`." if event == "UserPromptSubmit" else None
    _emit(event, text, system_message)


def _conductor_slice(workflow):
    """The text BETWEEN the conductor's <!-- WF:conductor:loop:start/end --> sentinels: the loop and
    the rules-of-the-road (D-7 ships BOTH - the how-to plus the prohibitions). Reuses workflow's own
    (key, scope)-parameterized block matcher rather than a second parser. Returns "" if the sentinels
    are missing or malformed, which the caller treats as a broken machinery signal."""
    text = workflow.CONDUCTOR.read_text(encoding="utf-8")
    start_pat, end_pat = workflow._block_patterns("conductor", "loop")
    ms, me = start_pat.search(text), end_pat.search(text)
    if not ms or not me or me.start() < ms.end():
        return ""
    return text[ms.end():me.start()].strip()


def _read_nudge_state(nudge_state_file):
    """The quiet-hash store: {session_id: hash-of-last-composed-message}. Missing/corrupt -> {} (a
    clean slate just means the next emit fires, which is safe). A valid-JSON-but-non-dict file
    (external tampering) is also treated as {}, so `.get`/`in` downstream can never crash on it."""
    try:
        store = json.loads(nudge_state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return store if isinstance(store, dict) else {}


def _write_nudge_state(workflow, nudge_state_file, store):
    """Persist the quiet-hash store atomically (workflow's writer: unique temp + os.replace, never
    torn). Takes the imported `workflow` module because its atomic writer lives there and this runs
    only on the OK branch where it is in scope. A write failure is SWALLOWED - a lost hash update
    only risks one duplicate nudge next turn (the accepted lost-update residual), and must never
    crash the hook (a non-zero exit would make the platform drop an already-emitted reminder)."""
    try:
        workflow._atomic_write_text(nudge_state_file, json.dumps(store))
    except OSError:
        pass


def main():
    # Read the event blob once. Bad input -> {} (a hook that raised on garbage would look like a
    # broken machinery to the platform); with no fields we simply find no root and exit silently.
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}                                    # valid-but-non-object JSON -> {} (no .get crash)
    event = data.get("hook_event_name", "")          # C-1: every field via .get, never an index
    session_id = data.get("session_id")
    if not isinstance(session_id, str):
        session_id = "default"                       # a non-string id would be an unhashable dict key

    root = _resolve_root(data)
    if root is None:
        sys.exit(0)                                   # no project handed to us -> nothing to do

    # STAT-BEFORE-IMPORT (D-9(ii)): a raw exists() on the exact `.workflow/marker.json` literal
    # (which a test asserts equals workflow.marker_path's spelling), importing nothing. No task here
    # -> exit silently (must-not #3). Only a present marker earns the import below.
    marker_file = root / ".workflow" / "marker.json"
    if not marker_file.exists():
        sys.exit(0)

    # A task exists. Try to read the machinery. ANY failure here (import, corrupt marker, missing
    # conductor sentinels) drops to the TERMINAL broken branch, which touches no workflow.py.
    try:
        import workflow  # noqa: E402  (same-dir; deferred + guarded on purpose - see module docstring)
        marker = workflow.load_marker(root=root)      # EXPLICIT root (D-2 invariant)
        if marker is None:
            raise RuntimeError("marker present but unreadable")
        step = marker["current_step"]
        state = workflow.receipt_state(step, root=root, marker=marker)   # EXPLICIT root
        conductor = _conductor_slice(workflow)
        if not conductor:
            raise RuntimeError("conductor sentinels missing")
    except Exception:
        _emit_broken(event)
        sys.exit(0)

    # OK branch: workflow imported cleanly, so its atomic writer IS available for the hash I/O below.
    # Compose the reminder. D-5: the message is about what is OWED, not the raw state - a non-fresh
    # receipt fires the reminder; a fresh one says the step is ready to advance. The conductor slice
    # rides along in BOTH events (D-7): even when fresh, the model needs the loop to know `advance`
    # is next.
    if state == "fresh":
        line = "{}: challenge current, ready to advance.".format(step)
    else:
        line = "{} owes a challenge (receipt: {}). Run prepare -> challenger -> record.".format(step, state)
    message = line + "\n\n" + conductor

    nudge_state_file = workflow.wf_dir(root) / "nudge-state.json"

    if event == "UserPromptSubmit":
        # QUIET-HASH: skip iff this session was already told this exact message - so a nudge that
        # hasn't changed does not re-nag every turn, but any change (step advanced, receipt flipped)
        # re-fires. We emit FIRST, then update the hash under a guard, so a failed state write can
        # never swallow the emit (the platform honours output only on exit 0).
        h = hashlib.sha256(message.encode("utf-8")).hexdigest()
        store = _read_nudge_state(nudge_state_file)
        if store.get(session_id) == h:
            sys.exit(0)                               # already delivered to this session -> stay quiet
        _emit(event, additional_context=message, system_message=line)
        store[session_id] = h
        _write_nudge_state(workflow, nudge_state_file, store)
    else:
        # SessionStart: always inject the context (additionalContext only), and RE-ARM by clearing
        # this session's hash, so the first UserPromptSubmit afterwards re-emits - the moment the
        # HUMAN-facing systemMessage can actually render.
        _emit(event, additional_context=message)
        store = _read_nudge_state(nudge_state_file)
        if session_id in store:
            del store[session_id]
            _write_nudge_state(workflow, nudge_state_file, store)

    sys.exit(0)


if __name__ == "__main__":
    main()
