#!/usr/bin/env python3
"""workflow.py - the spine of the six-step-workflow machinery (M4: the complete step set).

WHY this file exists: the whole design rests on one idea - a *deterministic script*, not the
model, is the single author of every "did this really happen?" signal. The model does the
probabilistic acts (spawn the challenger, draft the prose); this script does every act that
*verifies* one (write a receipt, gate the advance, compute fresh/stale, place the settled prose
between markers). That way the model can never quietly vouch for its own work: if it forgets a
step, the script simply has no receipt to show, and the gap is visible rather than papered over.

It is BOTH a command-line tool (verbs: start / prepare / record / advance / status / reset /
publish) AND an importable library (load_marker + receipt_state), so the status line and hooks
(M5) will read the *exact same* freshness logic instead of re-implementing it and drifting.

Scope (M4): the publish half is now a data-driven engine (_place_block) that writes real doc
SHAPES - log-accumulate (prepend, per-task) and sectioned replace-or-create (append, per-slug) -
via both-ends-identity markers and seeded per-location anchors; the four review-style rows are
added as data. Step 4 (Implementation) and Shipping are the publish exceptions (Implementation's
team of attackers + code output; Shipping writes no doc - its docs stay human-curated).
Standard library only, ASCII source, to run on any of the developer's machines with zero installs.
"""

import sys
import os
import re
import json
import hashlib
import secrets
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout. TWO roots, split apart in M5 (Decision D-2) because ONE name was doing TWO jobs:
#
#   BUNDLE  - where THIS script and its shipped assets (rulebook.md, conductor.md)
#             live. Correctly __file__-relative: those assets travel WITH the script
#             wherever it is copied, so this is a static constant, computed once.
#   PROJECT - where a task's live state lives (.workflow/, plus the committed docs/).
#             This is NOT __file__-relative: a hook is launched from ~/.claude but must
#             act on whichever project the human is standing in. So every PROJECT path is
#             a FUNCTION of a `root` the caller resolves and passes in - never a module
#             constant (the old `ROOT = __file__.parent` was that constant; it pinned state
#             to the script's own folder, which is Decision D-2's defect).
#
# How `root` is found (D-2a): WALK UP from a start directory to the nearest ancestor that
# proves it is the project - either it already holds .workflow/marker.json (an OPEN TASK)
# or it holds .git (a REPO ROOT). Two DIFFERENT walk-ups answer two DIFFERENT questions and
# are deliberately NOT merged into one project_root() - a single default cannot serve both
# (only `start` uses the git one, because no marker exists yet to find).
# ---------------------------------------------------------------------------
BUNDLE = Path(__file__).resolve().parent   # static: ships with the script
RULEBOOK = BUNDLE / "rulebook.md"          # the nine shared rules, bundled by `prepare` (Decision A-1)
CONDUCTOR = BUNDLE / "conductor.md"        # the loop the M5 nudge reads a slice from (BUNDLE-relative)

# The six steps, in order. "Where are we?" is just an index into this list, held
# in the marker - NOT inferred from which docs are filled (those are full across
# tasks, so they cannot tell you the current step; the Need step settled this).
STEPS = ["need", "design", "architecture", "implementation", "judgment", "shipping"]


# --- PROJECT path builders: each is a function of the resolved `root` ------------
# (These WERE the WF / MARKER / CONTEXT / CHALLENGE / ENTRY constants + artifact_path.
# D-2 turned every one into root -> Path, so a caller aims it at the project IT resolved
# rather than at BUNDLE. The bodies are trivial on purpose - the intelligence is in who
# passes which `root`, resolved by the walk-ups below.)
def wf_dir(root):
    """The runtime-state dir: <root>/.workflow (gitignored, ephemeral; `start` creates it)."""
    return Path(root) / ".workflow"


def marker_path(root):
    """The one state file the whole system reads. This exact literal (`.workflow/marker.json`)
    is repeated - DELIBERATELY, as the stat-before-import guard (D-9(ii)) - in statusline_wf.py
    and nudge.py, which must test for a task WITHOUT importing this module. A test asserts all
    three spellings agree (Architecture Section 2, proof 2), so the duplication cannot rot."""
    return wf_dir(root) / "marker.json"


def context_path(root):
    """The bundle `prepare` hands the challenger."""
    return wf_dir(root) / "context.md"


def challenge_path(root):
    """Where the challenger writes its verdicts back."""
    return wf_dir(root) / "challenge.md"


def entry_path(root):
    """The model's drafted settled-prose that `publish` places. EVERY publishing step drafts
    here (need/design/architecture/judgment), which is why the name is publish-, not overview-:
    it served only Need -> OVERVIEW in M3, before the engine generalized."""
    return wf_dir(root) / "publish-entry.md"


def gitignore_path(root):
    """D-10: the self-ignoring rule `start` authors, so `git add -A` in ANY repo never stages
    task state - without needing a rule in the repo's own .gitignore."""
    return wf_dir(root) / ".gitignore"


def global_habits_path(root):
    """The hand-filled global-habits slot (usually empty) - a WARM context input, not machine
    output, so `reset` spares it (D-10)."""
    return wf_dir(root) / "global-habits.md"


def draft_path(root, step):
    """The file that IS this step's product - the draft under attack, hashed for freshness.
    Named `draft-<step>.md` (NOT `<step>.md`) on purpose: on a case-insensitive filesystem
    (Windows, default macOS) a bare `docs/architecture.md` collides with the real committed
    `docs/ARCHITECTURE.md` and would clobber it. The `draft-` prefix cannot collide with any
    canonical doc name, so every review-style step's draft is safe (keeps proof #4 honest).
    D-10 moved these OUT of docs/ and INTO .workflow/, so a plain `git add -A` never stages an
    in-flight draft (the whole dir is ignored); the file NAME is unchanged."""
    return wf_dir(root) / ("draft-" + step + ".md")


# --- root resolution (D-2a): pure, stdlib, no marker/receipt logic ---------------
def _walk_up_for_marker(start):
    """Nearest ancestor of `start` (inclusive) that holds .workflow/marker.json, else None.
    This is how EVERY verb except `start` finds its project: an open task announces itself by
    its marker, no matter which subdirectory the human ran the command from."""
    start = Path(start).resolve()
    for d in (start, *start.parents):
        if (d / ".workflow" / "marker.json").exists():
            return d
    return None


def _walk_up_for_git(start):
    """Nearest ancestor of `start` (inclusive) that holds a .git ENTRY - a directory for a
    normal repo, a FILE for a worktree or submodule - else None. This is how `start` ALONE
    finds the project root: the human's settled rule is that his projects are git repos and
    the repo root IS the project root (OPERATOR.md). `.exists()` (not `.is_dir()`) is what
    makes the file-form work, so a worktree is rooted correctly too."""
    start = Path(start).resolve()
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return None


def _project_root(root):
    """Resolve a reader's root: an explicit `root` always wins (a hook is HANDED its root by
    the platform, and every in-process caller passes the one it resolved); ONLY when it is
    None do we fall back to the marker walk-up from CWD - the single unambiguous default, used
    solely by a human or model typing a verb inside an open task. Returns Path or None.

    An explicit `root` is wrapped in Path but NOT normalized here: the CLI never needs it (its
    root comes from the walk-ups, which already .resolve()). Block 2's hooks ingest a root as a
    raw platform STRING (stdin `workspace.project_dir` / $CLAUDE_PROJECT_DIR, forward- vs
    back-slashed) and add that normalization (the D-2a `_resolve_root` primitive) at the point
    it is actually needed - so it is not built here, where nothing yet consumes it."""
    if root is not None:
        return Path(root)
    return _walk_up_for_marker(Path.cwd())


# ---------------------------------------------------------------------------
# The per-step RECIPE - the ONE place in this script that is step-aware, so
# nothing else has to be. Two halves (see ARCHITECTURE "M4 - completing the step
# set: the publish engine"):
#   * challenge-context half (cold_sources / warm_sources / attack_angles):
#     a FROZEN contract every review-style step shares - identical COLD/WARM
#     sources (defined ONCE just below, so a row cannot silently drift), and only
#     the per-step attack angles differ (the "specialist per step"). Consumed by
#     `prepare`.
#   * publish half (publish: {...}): WHERE this step's settled prose lands and in
#     which SHAPE - `mode:log` (accumulate, newest-first) or `mode:section`
#     (replace-or-create one section per component). Consumed by `publish` via the
#     _place_block engine. `mode` is enforced there, so a mis-moded row fails loud.
# The five review-style steps each get a row; `implementation` gets NO row - it is
# the deferred exception (its team-of-attackers + code output is a different attack
# mechanism, not this prose challenge). `shipping` has a challenge half but NO
# publish half (the SECOND publish exception - its docs stay human-curated, because
# no valid single-writer auto-target exists; M4 Design, Decision 3).
#
# Source tokens (resolved by _resolve_sources) - the small vocabulary a recipe
# draws from, so adding a step is DATA, not new code (proof #4, replication):
#   "artifact"      -> this step's own draft (the thing under attack)
#   "prior_settled" -> the artifacts of every step before this one
#   "operator"      -> docs/OPERATOR.md (how this developer actually works)
#   "global_habits" -> the hand-filled global-habits slot (usually empty)
# ---------------------------------------------------------------------------

# The FROZEN challenge-context sources, shared by every review-style step. Defined
# once and referenced by each row below, so "frozen contract" is structural (there
# is a single definition to read) rather than a copy-paste discipline that can rot.
# COLD = the step's own draft + all prior settled drafts (fresh-eyes read); WARM =
# the operator facts + the global-habits slot (habit/domain-specific pass). What
# each token RESOLVES to is step-position-aware (see _resolve_sources), so the same
# two lists produce the right per-step context without varying the data.
_REVIEW_COLD_SOURCES = ["artifact", "prior_settled"]
_REVIEW_WARM_SOURCES = ["operator", "global_habits"]

RECIPE = {
    "need": {
        "cold_sources": _REVIEW_COLD_SOURCES,
        "warm_sources": _REVIEW_WARM_SOURCES,
        "attack_angles": [
            "What need is missing, or is true but was never said aloud?",
            "What must this explicitly NOT do?",
            "Who is the real user - and is that assumption right?",
            "What is assumed about the problem that might be false?",
        ],
        # The settled Need prose accumulates in OVERVIEW under the shared
        # "current-status" anchor, newest-first, one WF:need:<task_id> block per task.
        "publish": {
            "mode": "log",                    # accumulate: prepend newest-first, per-task scope
            "doc_target": "docs/OVERVIEW.md",
            "block_key": "need",              # WF:need:<task_id> blocks
            "anchor_slug": "current-status",  # under the seeded WF:anchor:current-status
        },
    },
    "design": {
        "cold_sources": _REVIEW_COLD_SOURCES,
        "warm_sources": _REVIEW_WARM_SOURCES,
        "attack_angles": [
            "Why might the chosen option be the wrong one?",
            "What trade-off is being quietly glossed over?",
            "What stronger option was never put on the table?",
            "What does this approach make expensive or hard to change later?",
        ],
        # Decisions accumulate in DECISIONS newest-first (one WF:design:<task_id>
        # block per task) under the seeded "decisions-log" anchor - DECISIONS has no
        # `##` heading to anchor on, which is exactly why the anchor is a seeded
        # comment, not heading text (M4 Architecture, Decision 4).
        "publish": {
            "mode": "log",
            "doc_target": "docs/DECISIONS.md",
            "block_key": "design",
            "anchor_slug": "decisions-log",
        },
    },
    "architecture": {
        "cold_sources": _REVIEW_COLD_SOURCES,
        "warm_sources": _REVIEW_WARM_SOURCES,
        "attack_angles": [
            "Does this pattern truly fit THIS problem, or is it familiar-by-default?",
            "Which boundary is in the wrong place - and what leaks across it?",
            "What breaks when one part changes? Are the contracts actually stable?",
            "What did the textbook shape carry in that we do not need here?",
        ],
        # ARCHITECTURE is sectioned: one replace-or-create block per component, kept
        # in stable order under the "architecture-sections" anchor. block_key is
        # "arch" (deliberately NOT "architecture"; M4 Architecture, Decision 2), so
        # the sentinels stay short and can never collide with the step name.
        "publish": {
            "mode": "section",
            "doc_target": "docs/ARCHITECTURE.md",
            "block_key": "arch",
            "anchor_slug": "architecture-sections",
        },
    },
    "judgment": {
        "cold_sources": _REVIEW_COLD_SOURCES,
        "warm_sources": _REVIEW_WARM_SOURCES,
        "attack_angles": [
            "Which part of the proof only covers the happy path?",
            "Which stated need was never actually confirmed?",
            "Where does the evidence rest on optimism, not observation?",
            "What would have to be true for this 'done' to be false?",
        ],
        # The macro verdict accumulates in OVERVIEW status under the SAME
        # "current-status" anchor as Need, so a task's Need and its later Judgment
        # interleave newest-first under one location - the shared-anchor design
        # (anchors are per-location, not per-key; M4 Design, Decision 5).
        "publish": {
            "mode": "log",
            "doc_target": "docs/OVERVIEW.md",
            "block_key": "judgment",
            "anchor_slug": "current-status",
        },
    },
    "shipping": {
        # NO publish half - the SECOND exception alongside `implementation` (M4
        # Design, Decision 3). Shipping still runs prepare -> challenge -> record
        # (it earns a receipt like any step), but writes NO doc automatically:
        # RISKS / PLAYBOOK / CHANGELOG / the commit stay human-curated, because no
        # valid single-writer auto-target exists. `cmd_publish` refuses a step whose
        # recipe has no "publish" key, so this omission is enforced, not just documented.
        "cold_sources": _REVIEW_COLD_SOURCES,
        "warm_sources": _REVIEW_WARM_SOURCES,
        "attack_angles": [
            "What works in the chat but breaks under real load or scale?",
            "What environment assumption is baked in and unstated?",
            "What is the rollback if this goes wrong - and has it been shown?",
            "Which failure mode is unhandled and unrecorded?",
        ],
    },
    # `implementation` intentionally has NO row: it is the deferred exception whose
    # attack mechanism (a team of built-in + fidelity attackers over real code) is
    # not this prose challenge. `prepare`/`publish` fail-closed on it by design.
}


# ---------------------------------------------------------------------------
# Low-level helpers.
# ---------------------------------------------------------------------------
def sha256_bytes(path):
    """Hash a file's RAW BYTES, or return None if it cannot be read.

    Raw bytes on purpose: this repo fights Windows CRLF/LF translation via
    .gitattributes, and if `record` hashed text-mode while the status line hashed
    bytes (or vice versa) they would disagree and flash a false 'stale'. Hashing
    bytes on both sides makes them provably identical. None means 'cannot verify',
    and every caller treats it as fail-closed - never as an accidental match.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_if_present(path):
    """Return a file's text if it exists and has non-whitespace content, else ''.
    Lets `prepare` skip absent/empty context sources cleanly - an empty OPERATOR.md
    or an unfilled global-habits slot simply doesn't appear in the bundle. A decode
    error is treated as 'not present' rather than crashing the whole assembly."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return text if text.strip() else ""


def load_marker(root=None):
    """Return the marker dict, or None if no task is open here (machinery inert).

    `root=None` walks up from CWD to find an open task - the CLI convenience default. Every
    hook and every test pass an EXPLICIT root, because they are handed where the project is
    and must not re-guess it from a process cwd (that re-guess is exactly the D-2 defect: a
    hook launched in ~/.claude would 'find' the wrong project, or none)."""
    root = _project_root(root)
    if root is None:
        return None
    try:
        return json.loads(marker_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _atomic_write_text(path, text):
    """Write text by temp-file-then-replace, so a crash mid-write can never leave a
    half-written file that later reads as corrupt (os.replace is atomic on Windows
    and POSIX). Used for the marker AND for `publish`, where a torn write would land
    in a real committed doc - the worst place to tear.

    Two deliberate choices: a UNIQUE temp name (not a fixed '<name>.tmp') so two
    writers can never share one temp file and adopt each other's bytes; and we write
    ENCODED BYTES (not write_text) so `text` lands VERBATIM - no LF<->CRLF translation -
    which lets `publish` preserve a doc's exact line endings instead of silently
    rewriting the whole file's newlines on Windows, and avoids write_text/read_text's
    version-specific newline= kwarg (read_text only gained it in 3.13; this runs on 3.12)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (path.name + "." + secrets.token_hex(4) + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    try:
        os.replace(tmp, path)
    except OSError:
        # A failed replace (target locked, or a concurrent writer won the race) must not
        # leave our uniquely-named temp behind to accrete. Clean it up, then re-raise so the
        # failure stays visible rather than silently lost.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _save_marker(marker, root=None):
    """Persist the marker atomically (see _atomic_write_text). Returns 0 on success, or a
    non-zero _fail on an OSError - D-9(iii): the write guard lives HERE so every caller
    (start/record/advance) is covered in one place, and a filesystem failure becomes a clean
    one-line message instead of a raw traceback (which the platform MANGLES under a hook).
    Callers propagate the return, so a failed save never prints a false 'succeeded'."""
    root = _project_root(root)
    if root is None:
        # Match load_marker/receipt_state: with no task at or above CWD there is nowhere to write,
        # so degrade to a clean _fail rather than a TypeError inside marker_path(None) - the raw
        # traceback D-9(iii) exists to keep out of a hook. (Unreached in Block 1 - every verb passes
        # an explicit root - but this guards a future/hook caller that trusts the =None default.)
        return _fail("no task open here - cannot save the marker (run `start` first).")
    try:
        _atomic_write_text(marker_path(root), json.dumps(marker, indent=2))
    except OSError as exc:
        return _fail("could not write the marker at {} ({}).".format(marker_path(root), exc))
    return 0


def receipt_state(step, root=None, marker=None):
    """THE shared truth function - imported by the status line and the hooks (M5) so
    the fresh/stale/missing rule lives in exactly one place and can never drift.

    `root` (added in M5) locates the draft whose bytes are hashed: the status line and hooks
    pass the project root the platform handed them; a CLI/library caller may omit it to walk
    up from CWD. `marker` may be passed to avoid a re-load (e.g. cmd_status loops over steps).

    Returns one of:
      "missing" - no receipt for this step (challenge never recorded, or it failed
                  closed, or the step was force-advanced without a real challenge).
                  The honest "not done".
      "stale"   - a receipt exists but the artifact's bytes have changed since (or the
                  artifact became unreadable), so the green no longer reflects what is
                  on disk. ANY edit to the artifact flips fresh -> stale.
      "fresh"   - a receipt exists AND the live artifact still hashes to what was
                  recorded. Only this counts as "the challenge really ran against what
                  is on disk right now."
    """
    root = _project_root(root)
    if marker is None:
        marker = load_marker(root)
    # No marker, or no root to locate the draft against -> honest "not done", fail-closed.
    if not marker or root is None:
        return "missing"
    receipt = marker.get("receipts", {}).get(step)
    if not receipt:
        return "missing"
    if "artifact_hash" not in receipt:
        # A receipt with no artifact_hash is a conscious --force override on a step
        # that never had a real challenge. The honest state is "missing" (no challenge
        # happened), not "stale"; status shows "missing (overridden)".
        return "missing"
    current = sha256_bytes(draft_path(root, step))
    if current is None:
        # Had a receipt, but the artifact is gone/unreadable now -> not trustworthy.
        return "stale"
    return "fresh" if current == receipt.get("artifact_hash") else "stale"


def _fail(msg):
    """Uniform fail-closed exit: say why on stderr, return non-zero. Every refusal in
    this script routes through here, so a failure is always visible and never silently
    swallowed - the honest floor depends on that."""
    sys.stderr.write("workflow: " + msg + "\n")
    return 1


def _print_root(root):
    """Announce which project root a verb resolved to. STDERR, not stdout (human ruling,
    2026-07-16): it stays visible in a terminal AND in a Bash tool's error stream - which is
    where the guard earns its keep, catching a Claude-typed stray `cd` that silently re-rooted
    a verb - while keeping the stdout the tests (and any caller) parse completely untouched."""
    sys.stderr.write("workflow: root {}\n".format(root))


def _resolve_sources(tokens, step, root):
    """Turn a recipe's source tokens into ordered (label, path) pairs. Kept tiny and
    data-driven so ADDING A STEP is a recipe row, never new code here (proof #4,
    replication-ready). An unknown token is a recipe bug, raised loudly rather than
    silently dropping context the challenger needs (a unit test asserts the raise).
    Every path is built from the passed-in `root` (M5/D-2), never a module constant.

    `root` is REQUIRED here (no `=None` default), unlike the public readers load_marker/
    receipt_state: this is a prepare-internal helper that builds paths DIRECTLY and has no
    walk-up fallback, so a defaulted None would crash in draft_path(None, ...). Required makes
    the one caller (cmd_prepare, which always holds a resolved root) pass it, and turns any
    future misuse into an obvious missing-argument error rather than a latent crash."""
    pairs = []
    for tok in tokens:
        if tok == "artifact":
            pairs.append(("the proposal under attack (step: {})".format(step), draft_path(root, step)))
        elif tok == "prior_settled":
            # every step strictly BEFORE this one, in order (empty for the first step)
            for prior in STEPS[:STEPS.index(step)]:
                pairs.append(("settled record: {}".format(prior), draft_path(root, prior)))
        elif tok == "operator":
            pairs.append(("operator context (how this developer actually works)", Path(root) / "docs" / "OPERATOR.md"))
        elif tok == "global_habits":
            pairs.append(("global-habits slot (hand-filled; usually empty)", global_habits_path(root)))
        else:
            raise KeyError("unknown recipe source token: {!r}".format(tok))
    return pairs


def _append_sources(out, tokens, step, root):
    """Append each present source as a labelled section to the bundle list `out`.
    Returns True if it appended at least one section. Shared by the COLD and WARM
    assembly so the two are IDENTICAL by construction (a formatting change can't drift
    between them)."""
    added = False
    for label, path in _resolve_sources(tokens, step, root):
        text = _read_if_present(path)
        if text:
            added = True
            out.append("\n## {}\n\n".format(label))
            out.append(text if text.endswith("\n") else text + "\n")
    return added


# ---------------------------------------------------------------------------
# The verbs.
# ---------------------------------------------------------------------------
def _write_gitignore(root):
    """D-10: author .workflow/.gitignore = `*` then `!global-habits.md`. The `*` ignores ALL
    task state (marker, drafts, context, challenge, entry, nudge-state) AND this .gitignore
    itself; the single re-include exempts the hand-authored global-habits.md. There is NO
    `!.gitignore` line ON PURPOSE: adding it would make `start` author a git-TRACKED file in
    every repo it runs in (D-10 tested this twice), which is exactly what we are avoiding."""
    _atomic_write_text(gitignore_path(root), "*\n!global-habits.md\n")


def cmd_start(args):
    """Human-owned bootstrap. Starting a task is a deliberate act; this is the only
    way the machinery comes alive.

    M5/D-2a: `start` is the ONE verb rooted by the GIT walk-up - no marker exists yet, so it
    cannot use the marker walk-up every other verb uses. The human's settled rule is that the
    repo root IS the project root (OPERATOR.md). It refuses if a task is already open at or
    above CWD rather than silently clobbering an in-progress one (that clobber would be exactly
    the kind of invisible failure the whole design exists to prevent), and it authors the
    self-ignoring .workflow/.gitignore (D-10) so git hygiene holds in any repo."""
    root = _walk_up_for_git(Path.cwd())
    if root is None:
        return _fail("not inside a git repository (no .git at or above {}). `start` roots the "
                     "task at the repo root, so run it from within your project.".format(Path.cwd()))
    _print_root(root)
    # Refuse if any ancestor already holds an open task - the marker walk-up, used here only to
    # forbid a nested/duplicate task, never to root this one.
    open_at = _walk_up_for_marker(Path.cwd())
    if open_at is not None:
        return _fail("a task is already open at {} (run `reset` there first). Refusing to "
                     "clobber it.".format(open_at))
    marker = {
        "task_id": secrets.token_hex(4),   # short unique id for this task
        "task_title": args.title,
        "current_step": STEPS[0],          # every task starts at Need
        "receipts": {},                    # filled one step at a time by `record`
        "pending": None,                   # the in-flight challenge (set by `prepare`)
    }
    # Author the ignore rule BEFORE the marker: if this fails we have written no marker, so
    # "no task open" still holds everywhere and a re-run of `start` heals it cleanly.
    try:
        _write_gitignore(root)
    except OSError as exc:
        return _fail("could not author {} ({}); nothing started.".format(gitignore_path(root), exc))
    rc = _save_marker(marker, root)
    if rc:
        return rc
    print("started task '{}' [{}] at step: {}".format(
        marker["task_title"], marker["task_id"], marker["current_step"]))
    return 0


def cmd_prepare(args):
    """Assemble the challenger's context bundle from the step's RECIPE, plant a fresh
    secret canary in it, and record that a challenge is now pending.

    The bundle is the honest-floor mechanism made concrete. It bundles the shared
    rulebook as a framing header (Decision A-1), then delivers the context in the
    ordered COLD -> WARM shape the Design settled (alpha-1): the challenger reads and
    verdicts the COLD set first, echoing the canary, then reads WARM. This *surfaces*
    whether a genuine cold read happened; it does not *force* one (forcing is deferred
    to M4). The canary cannot prove an INDEPENDENT party read the bundle (the model can
    read the file too - the accepted permanent ceiling), but it DOES catch an honest
    mistake: a challenge run against the wrong or truncated bundle echoes the wrong
    token and gets rejected at `record`."""
    root = _walk_up_for_marker(Path.cwd())
    if root is None:
        return _fail("no task open at or above {} - run `start` first.".format(Path.cwd()))
    _print_root(root)
    marker = load_marker(root)
    if not marker:
        return _fail("no task open (run `start` first).")
    step = args.step
    if step != marker["current_step"]:
        return _fail("current step is '{}', not '{}'.".format(marker["current_step"], step))
    recipe = RECIPE.get(step)
    if not recipe:
        return _fail("no recipe for step '{}' - only `implementation` has no recipe "
                     "(its team-of-attackers mechanism is deferred; every other step has one)."
                     .format(step))

    # Fail-closed on a missing rulebook: A-1 was chosen precisely so the rules cannot
    # be silently absent from the one file the challenger reads. No rulebook, no bundle.
    rulebook = _read_if_present(RULEBOOK)
    if not rulebook:
        return _fail("rulebook not found or empty at {} - refusing to prepare a challenge "
                     "without the shared rules (Decision A-1). Nothing prepared.".format(RULEBOOK))

    # Fail-closed on a missing/empty proposal: challenging nothing is meaningless, and
    # (with the snapshot below) would otherwise let a later-written draft earn a receipt.
    if not _read_if_present(draft_path(root, step)):
        return _fail("no proposal to challenge at {} - draft the '{}' step first. "
                     "Nothing prepared.".format(draft_path(root, step), step))

    canary = "WF-CANARY-" + secrets.token_hex(8)   # fresh every prepare

    out = []
    # Decision A-1: bundle the shared rulebook as the FRAMING HEADER, so the nine rules
    # ride inside the one file the challenger provably reads (canary-adjacent), rather
    # than via a model-mediated path read that could silently miss.
    out.append(rulebook.rstrip() + "\n\n---\n\n")
    out.append("# Challenge for step: {}\n\n".format(step))
    # Two-pass instruction (rule 6 / Design alpha-1): honest ordered-visible delivery.
    out.append(
        "Work in two passes. Read the COLD section, write your COLD verdict, and echo the\n"
        "canary - all BEFORE you read the WARM section. Then read WARM and write your WARM\n"
        "verdict. Attack the proposal under these angles:\n")
    for angle in recipe["attack_angles"]:
        out.append("  - {}\n".format(angle))

    # COLD: the proposal + the settled record. The canary sits at the END of COLD, so
    # echoing it proves the cold section was read THROUGH to the end (a truncated read
    # loses it - the real honest-mistake failure mode).
    out.append("\n===== COLD (read + verdict + canary FIRST) =====\n")
    _append_sources(out, recipe["cold_sources"], step, root)
    out.append("\nCANARY (echo this token verbatim in your COLD verdict): {}\n".format(canary))

    # WARM: operator + global habits. Delivered in the same bundle (alpha-1) but ordered
    # after the cold canary and labelled "read only after the cold verdict".
    out.append("\n===== WARM (read only AFTER writing the cold verdict) =====\n")
    if not _append_sources(out, recipe["warm_sources"], step, root):
        out.append("\n(no warm context on file for this task)\n")

    bundle = "".join(out)
    wf_dir(root).mkdir(exist_ok=True)

    # Clear the PREVIOUS round's challenger result before this round's challenger runs (live
    # smoke-test finding L2 - the exact mirror of CB1's leftover-ENTRY bug, one file over).
    # `record` cannot be fooled by a stale result (this prepare plants a fresh canary, and a
    # stale file echoes the old one -> rejected), so this is not a receipt-integrity hole. It is
    # a CONTEXT-INTEGRITY one: the challenger is told to WRITE this path, so it reads whatever
    # is already there. Two live challengers did exactly that, then reported the previous
    # round's findings back as "cross-round corroboration" - contamination dressed up as
    # independent confirmation, which is precisely what "a fresh challenger each step" exists to
    # prevent. Clearing here is the only point that is after the challenger's last run and
    # before the next one's.
    # Fail CLOSED if it survives: prepare's whole job is to hand over a clean bundle, so if the
    # directory cannot be made clean we write no bundle and plant no pending - nothing is
    # prepared, exactly as when the rulebook is missing. This sits AFTER every validation check
    # above on purpose: a REFUSED prepare must not have the side effect of destroying the
    # previous round's result. A benign "already gone" is the normal case.
    try:
        challenge_path(root).unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        return _fail("prepared nothing: could not clear the previous challenger result ({}) - the "
                     "next challenger would read it as context and lose its independence. Close "
                     "whatever holds {} and re-run prepare.".format(exc, challenge_path(root)))

    # Write bytes so the file matches the string we hash below exactly (no newline
    # translation), consistent with _atomic_write_text. D-9(iii): guard the write so a locked
    # or unwritable .workflow yields a clean _fail, not a traceback the platform mangles under
    # a hook - and, because it sits before the pending is saved, a failed write prepares nothing.
    try:
        context_path(root).write_bytes(bundle.encode("utf-8"))
    except OSError as exc:
        return _fail("could not write the challenge bundle to {} ({}). Nothing prepared."
                     .format(context_path(root), exc))

    marker["pending"] = {
        "step": step,
        "canary": canary,
        "context_hash": hashlib.sha256(bundle.encode("utf-8")).hexdigest(),
        # Snapshot the artifact the challenger will actually see. `record` refuses if
        # the live artifact no longer matches this - closing the window where the draft
        # is edited AFTER the challenge but BEFORE record, which would otherwise mint a
        # "fresh" receipt for bytes nobody challenged.
        "artifact_hash": sha256_bytes(draft_path(root, step)),
    }
    rc = _save_marker(marker, root)
    if rc:
        return rc
    print("prepared challenge for '{}': bundle -> {} (rulebook + canary planted)".format(step, context_path(root)))
    return 0


def cmd_record(args):
    """Read the challenger's written result, verify it echoed THIS prepare's canary,
    confirm the artifact is unchanged since prepare, and write the receipt. FAIL-CLOSED
    on every check: a missing result, a wrong/absent canary, an unreadable artifact, or
    an artifact that changed between prepare and record writes NO receipt and returns
    non-zero. This is load-bearing - the whole honest floor collapses if there is any
    path that writes a partial 'green'."""
    root = _walk_up_for_marker(Path.cwd())
    if root is None:
        return _fail("no task open at or above {} - run `start` first.".format(Path.cwd()))
    _print_root(root)
    marker = load_marker(root)
    if not marker:
        return _fail("no task open (run `start` first).")
    step = args.step
    pending = marker.get("pending")
    if not pending or pending.get("step") != step:
        return _fail("no challenge is pending for '{}' (did you run `prepare`?).".format(step))
    if not challenge_path(root).exists():
        return _fail("no challenger result at {} - challenge did not run. No receipt written."
                     .format(challenge_path(root)))

    result_text = challenge_path(root).read_text(encoding="utf-8", errors="replace")
    if pending["canary"] not in result_text:
        # The result does not echo this bundle's token -> it did not consume the right
        # context (wrong/stale/truncated bundle, or no real challenge). Reject.
        return _fail("challenger result did not echo the current canary - wrong/stale context. "
                     "No receipt written.")

    artifact_hash = sha256_bytes(draft_path(root, step))
    if artifact_hash is None:
        return _fail("artifact for '{}' is unreadable ({}). No receipt written."
                     .format(step, draft_path(root, step)))
    if artifact_hash != pending.get("artifact_hash"):
        # The draft changed between `prepare` and `record`: the challenge ran against
        # different bytes than are on disk now. Refuse rather than certify the wrong ones.
        return _fail("artifact for '{}' changed between prepare and record - the challenge ran on "
                     "different bytes. Re-prepare and re-challenge. No receipt written.".format(step))

    # CB1 (correctness red-team): the publish gate certifies the *artifact* (the draft) was
    # challenged, but the text `publish` actually writes comes from ENTRY (publish-entry.md), which
    # is never tied to the receipt. Clear any LEFTOVER entry BEFORE writing the receipt, so a stale
    # draft from a PREVIOUS round can never publish under the fresh receipt we are about to write -
    # the model must draft a fresh entry (conductor step 6) after each record. If the entry EXISTS
    # but cannot be removed (locked by an editor / AV / sync), that is a real failure: fail closed
    # WITHOUT writing the receipt, so no fresh receipt exists and publish's gate refuses - never
    # silently leave a stale entry that could publish (convergence red-team B2, the same way
    # `reset` treats an undeletable file as reportable). A benign "no entry" is the normal case.
    # The inherent residual (a fresh-but-divergent entry - a post-settle summary that cannot be
    # hash-compared to the draft) is model-authored + human-reviewed and is documented (RISKS #13).
    try:
        entry_path(root).unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        return _fail("recorded nothing: could not clear a leftover drafted entry ({}) - a stale "
                     "entry could otherwise publish under a fresh receipt. Close whatever holds {} "
                     "and re-run record.".format(exc, entry_path(root)))

    marker.setdefault("receipts", {})[step] = {
        "challenge_ran": True,           # self-reported: "the model reports it ran" - never "verified"
        "context_hash": pending["context_hash"],
        "artifact_hash": artifact_hash,  # freshness is keyed to the artifact's live bytes
        "canary": pending["canary"],
    }
    marker["pending"] = None             # consume the pending challenge
    rc = _save_marker(marker, root)
    if rc:
        return rc
    print("recorded receipt for '{}' (challenge_ran, artifact hashed).".format(step))
    return 0


def cmd_advance(args):
    """The gate. By default refuse to leave the current step unless it has a FRESH
    receipt (challenge ran AND the artifact has not changed since). This catches a
    premature/accidental advance and a stale green.

    `--force` is the human's conscious override: it advances WITHOUT a fresh receipt and
    records that the human overrode, so the bypass is on the record, never silent. This
    reconciles "advance is gated" with "warn, never block - the human keeps the wheel",
    and gives a lighter path when a benign post-settle edit flips the hash."""
    root = _walk_up_for_marker(Path.cwd())
    if root is None:
        return _fail("no task open at or above {} - run `start` first.".format(Path.cwd()))
    _print_root(root)
    marker = load_marker(root)
    if not marker:
        return _fail("no task open (run `start` first).")
    cur = marker["current_step"]
    idx = STEPS.index(cur)
    if idx == len(STEPS) - 1:
        return _fail("already at the last step ('{}'); nothing to advance to.".format(cur))

    state = receipt_state(cur, root=root, marker=marker)
    overriding = state != "fresh" and args.force   # computed once so the record + the message agree
    if state != "fresh" and not args.force:
        return _fail("cannot advance: step '{}' is '{}', not 'fresh'. Run the challenge, or "
                     "`advance --force` to override consciously.".format(cur, state))

    if overriding:
        # Record the conscious override so it is visible in status/audit.
        marker.setdefault("receipts", {}).setdefault(cur, {})
        marker["receipts"][cur]["override"] = True
        marker["receipts"][cur]["override_state"] = state

    marker["current_step"] = STEPS[idx + 1]
    marker["pending"] = None  # a new step starts with no challenge pending
    rc = _save_marker(marker, root)
    if rc:
        return rc
    print("advanced: {} -> {}{}".format(cur, marker["current_step"], " (HUMAN OVERRIDE)" if overriding else ""))
    return 0


# ---------------------------------------------------------------------------
# The publish engine (M4). The M3 publish did ONE thing (prepend/replace a
# key-only sentinel block under a heading anchor). M4 generalizes it to the real
# document SHAPES the review steps write, but keeps it ONE engine:
#   * markers carry the full identity (key, scope) on BOTH ends, so one task's or
#     section's block can never match another's (the M3 start-only format could -
#     a second task would clobber the first; RISKS #12 key-half);
#   * a single _place_block owns identity-matching + the fail-closed guard +
#     replace-in-place; the ONLY thing that varies is where a BRAND-NEW block is
#     inserted - prepended for logs (newest-first) or appended for reference
#     sections (stable order, so a section never jumps when it is edited);
#   * anchors are SEEDED per-location comments (WF:anchor:<slug>), not prose
#     headings - DECISIONS has no stable heading, and headings drift and collide
#     (M4 Architecture, Decision 5). Shared across keys, so e.g. Need and Judgment
#     interleave under one OVERVIEW anchor.
# Everything stays column-0 whole-line + fail-closed: anything ambiguous refuses
# rather than risk corrupting a real committed doc.
# ---------------------------------------------------------------------------

# A scope is a hex task_id or a section-slug. The settled grammar (M4 Architecture,
# Decision C) is lowercase kebab - hex task_ids and human slugs both fit. Constrained
# to this charset (and re.escape'd anyway) so a slug can NEVER inject regex.
_SCOPE_RE = r"[a-z0-9-]+"

# Any standalone column-0 WF marker line - a block start/end OR an anchor, ANY
# key/scope. The key-AGNOSTIC entry guard uses this (RISKS #12 second half): a
# drafted entry may MENTION marker syntax inline in backticks (these very docs
# do), but a whole-line column-0 marker in the entry would inject bogus structure.
_ANY_MARKER_LINE = re.compile(r"(?m)^<!--\s*WF:[^\n]*?-->[ \t]*$")

# Any seeded anchor line (any slug) - used to BOUND append_section to one anchor's
# region, so a new section can never land under a different anchor.
_ANY_ANCHOR_LINE = re.compile(r"(?m)^<!-- WF:anchor:" + _SCOPE_RE + r" -->[ \t]*$")

# A Markdown code-fence delimiter line: 3+ backticks OR 3+ tildes, indented 0-3 spaces (all
# CommonMark-legal). Group 1 is the delimiter run - its character and length identify the fence;
# group 2 is the remainder (an info string on an opener, or - for a valid CLOSER - whitespace only).
_FENCE_LINE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


class _PublishError(Exception):
    """Raised by the publish engine on any fail-closed condition. cmd_publish turns
    it into a _fail() - no write, non-zero, visible - so a torn or ambiguous publish
    can never silently corrupt a committed doc."""


def _block_markers(key, scope):
    """The exact start/end comment lines the engine WRITES for a (key, scope) block.
    Both ends carry the identity, so finding one block can never grab another's."""
    return ("<!-- WF:{}:{}:start -->".format(key, scope),
            "<!-- WF:{}:{}:end -->".format(key, scope))


def _block_patterns(key, scope):
    """Column-0 whole-line regexes for THIS (key, scope) block's two markers - the
    exact shape _block_markers writes. re.escape so nothing in key/scope is special."""
    start, end = _block_markers(key, scope)
    return (re.compile(r"(?m)^" + re.escape(start) + r"[ \t]*$"),
            re.compile(r"(?m)^" + re.escape(end) + r"[ \t]*$"))


def _anchor_pattern(slug):
    """Column-0 whole-line regex for the seeded WF:anchor:<slug> location marker."""
    return re.compile(r"(?m)^" + re.escape("<!-- WF:anchor:{} -->".format(slug)) + r"[ \t]*$")


def _key_end_pattern(key):
    """Column-0 end markers for ANY scope of `key` - append_section uses this to find
    the tail of the managed-section group so a new section lands after the last one."""
    return re.compile(r"(?m)^" + re.escape("<!-- WF:{}:".format(key)) + _SCOPE_RE
                      + re.escape(":end -->") + r"[ \t]*$")


def _entry_has_marker_line(entry):
    """True if the drafted entry contains a standalone column-0 WF marker line (any
    key/scope, block or anchor). Key-AGNOSTIC (RISKS #12 second half): an entry that
    merely quotes marker syntax inline is fine; a whole-line marker would inject
    structure into the real doc and is refused."""
    return _ANY_MARKER_LINE.search(entry) is not None


def _wf_marker_in_fence(doc):
    """True if any column-0 WF marker/anchor line sits INSIDE a Markdown code fence. We cannot
    safely count or place around markers when a doc quotes them as fenced examples, so publish
    REFUSES (fail-closed) - the settled RISKS #12 ruling (a cheap fail-closed guard now; safe
    *placement* around fenced markers stays deferred).

    This tracks the OPENING fence's character and length, per CommonMark: a fence opened by N
    backticks (or tildes) closes only on a line of the SAME character, at least N long, with
    nothing after but whitespace. A run of the *other* character, or a shorter run, or one with
    trailing text is literal CONTENT - not a closer. Tracking this matters (convergence red-team
    B1): a naive 'toggle on any ```/~~~ run' desyncs on a mismatched delimiter, which both HIDES
    a marker inside a fence (fail-open) AND wrongly flags a later free marker as fenced (a false
    fail-closed) for the rest of the doc. We still only flag a COLUMN-0 WF marker inside a fence,
    because only column-0 markers can fool the positional scans; an indented one can't. Real
    project docs have no such fences (grep-verified), so this never fires in practice; it exists
    so a doc that DOES grow one can never be silently mis-edited."""
    fence = None   # None, or (char, length) of the currently-open fence
    for line in doc.split("\n"):
        m = _FENCE_LINE.match(line)
        if m:
            run, rest = m.group(1), m.group(2)
            char, length = run[0], len(run)
            if fence is None:
                # Open a fence. CommonMark exception: a BACKTICK opener's info string may NOT
                # contain a backtick - if it does, the line is not a fence at all, just ordinary
                # content, so a marker after it is genuinely free (convergence round-2 BLOCKING #2:
                # treating such a line as a fence false-refused a legitimate doc).
                if not (char == "`" and "`" in rest):
                    fence = (char, length)
            elif char == fence[0] and length >= fence[1] and rest.strip(" \t") == "":
                fence = None                              # valid closer (CommonMark: ONLY spaces/tabs
                #   may follow a closer - str.strip() with no args would also eat form-feed / NBSP /
                #   C0 separators, wrongly closing the fence early and exposing a marker: round-4 fail-open)
            # else: different char / shorter run / trailing text -> literal content, ignore
        elif fence is not None and line.startswith("<!--") and "WF:" in line:
            return True
    return False


def _place_block(doc, block_key, scope, anchor_slug, placement, body):
    """Insert-or-replace THIS (block_key, scope) block in `doc` (LF-space text) and
    return the new text - or raise _PublishError on ANY ambiguity (fail-closed).

    - Count MY (block_key, scope) markers: 0 pairs -> insert a new block; 1 pair ->
      replace it in place; any other count (orphan start/end, or a duplicate such as
      a same-scope marker sitting in a code fence) -> refuse. This shared count is
      also the fence guard: a stray same-scope fenced marker makes the count 2 and
      the write refuses rather than corrupting.
    - A NEW block's position depends on `placement`:
        'prepend'        -> right under the seeded anchor (newest-first: logs).
        'append_section' -> after the last existing WF:<block_key>:* block that
                            follows the anchor (stable order: reference sections);
                            if none exist yet, right under the anchor.
    """
    # Normalize ALL CommonMark line terminators to LF - CRLF *and* a lone CR - before interpreting
    # lines. A bare CR is a line ending per CommonMark, but str.split("\n") and re.MULTILINE treat
    # only \n as one, so a bare \r before a fence delimiter (or a marker) desyncs the fence guard,
    # hiding a fenced marker (fail-open) or flagging a free one (false-refuse) (convergence round-3).
    # This function interprets lines, so it owns the normalization for EVERY caller (a direct caller
    # that hands in bare CRs is otherwise silently mis-parsed). LF is re-applied by cmd_publish on write.
    doc = doc.replace("\r\n", "\n").replace("\r", "\n")
    if _wf_marker_in_fence(doc):
        raise _PublishError("target has a WF: marker line inside a ``` code fence - refusing "
                            "(cannot safely place around fenced marker examples).")
    start_pat, end_pat = _block_patterns(block_key, scope)
    n_start, n_end = len(start_pat.findall(doc)), len(end_pat.findall(doc))
    if n_start != n_end:
        raise _PublishError("malformed markers for WF:{}:{} - {} start(s) vs {} end(s)."
                            .format(block_key, scope, n_start, n_end))
    if n_start > 1:
        raise _PublishError("more than one WF:{}:{} block - refusing.".format(block_key, scope))

    start_marker, end_marker = _block_markers(block_key, scope)
    block = "{}\n{}\n{}".format(start_marker, body, end_marker)

    # Re-settle: replace the one existing block in place (identical for both modes).
    if n_start == 1:
        m_start, m_end = start_pat.search(doc), end_pat.search(doc)
        if m_end.start() < m_start.start():
            raise _PublishError("end precedes start for WF:{}:{} - refusing."
                                .format(block_key, scope))
        return doc[:m_start.start()] + block + doc[m_end.end():]

    # Insert a NEW block: locate the seeded anchor (fail-closed on missing/duplicate).
    anchor_pat = _anchor_pattern(anchor_slug)
    n_anchor = len(anchor_pat.findall(doc))
    if n_anchor != 1:
        raise _PublishError("expected exactly one WF:anchor:{}, found {} - refusing."
                            .format(anchor_slug, n_anchor))
    m_anchor = anchor_pat.search(doc)

    if placement == "prepend":
        at = m_anchor.end()
    elif placement == "append_section":
        # Append after the last WF:<block_key>:* end-marker in THIS anchor's region -
        # from the anchor to the next WF:anchor: (or EOF) - so a section under anchor X
        # can never land under a different anchor Y. No managed block yet -> right under
        # the anchor. (Fenced decoys are already excluded: _wf_marker_in_fence made the
        # whole publish fail-closed at the top.)
        region_end = len(doc)
        for m in _ANY_ANCHOR_LINE.finditer(doc):
            if m.start() > m_anchor.end():
                region_end = m.start()
                break
        at = m_anchor.end()
        for m in _key_end_pattern(block_key).finditer(doc):
            if m_anchor.end() < m.start() < region_end:
                at = m.end()
    else:
        raise _PublishError("unknown placement {!r}.".format(placement))
    return doc[:at] + "\n\n" + block + doc[at:]


def cmd_publish(args):
    """Auto-docs writer (Decision D-1, generalized in M4). The model drafts the
    settled-step prose into .workflow/publish-entry.md; THIS verb places it into the
    real doc via the publish engine (_place_block), so the model owns the wording and
    the script owns placement/replace. It is the ONLY verb that writes a committed
    doc, so it is FAIL-CLOSED throughout: anything ambiguous refuses.

    Two modes, read from the step's RECIPE publish half:
      * 'log'     -> scope = this task's id, placement = prepend (accumulate across
                     tasks under a shared anchor; DECISIONS, OVERVIEW status).
      * 'section' -> scope = a --section slug, placement = append_section (one
                     section per component; --new/--update intent guards a mistargeted
                     write; ARCHITECTURE)."""
    root = _walk_up_for_marker(Path.cwd())
    if root is None:
        return _fail("no task open at or above {} - run `start` first.".format(Path.cwd()))
    _print_root(root)
    marker = load_marker(root)
    if not marker:
        return _fail("no task open (run `start` first).")
    step = args.step
    recipe = RECIPE.get(step)
    if not recipe or "publish" not in recipe:
        return _fail("no publish target for step '{}'.".format(step))
    pub = recipe["publish"]
    mode = pub.get("mode")
    if mode not in ("log", "section"):
        return _fail("unsupported publish mode {!r} for step '{}'.".format(mode, step))

    # Gate (the honest floor): publish is the ONLY verb that writes a committed doc, so it
    # must refuse an unchallenged or non-current step. Require the step to BE current AND to
    # hold a FRESH receipt (the challenge ran against the artifact on disk) - the same honesty
    # the advance-gate enforces. Closes a publish-without-challenge and a republish-after-
    # advance path, either of which would write unvouched content into a real doc.
    if step != marker.get("current_step"):
        return _fail("current step is '{}', not '{}' - refusing to publish a non-current step."
                     .format(marker.get("current_step"), step))
    state = receipt_state(step, root=root, marker=marker)
    if state != "fresh":
        return _fail("step '{}' has no fresh receipt (state: {}) - run the challenge and `record` "
                     "before publishing.".format(step, state))

    # 1) The drafted entry: exists, non-empty, and carries no injected marker line.
    try:
        entry = entry_path(root).read_text(encoding="utf-8").strip() if entry_path(root).exists() else ""
    except (OSError, UnicodeDecodeError):
        return _fail("drafted entry at {} is unreadable. Nothing published.".format(entry_path(root)))
    if not entry:
        return _fail("no drafted entry at {} (write the settled prose there first). "
                     "Nothing published.".format(entry_path(root)))
    entry = entry.replace("\r\n", "\n")   # LF space; the doc's own newline is re-applied on write
    if _entry_has_marker_line(entry):
        return _fail("the drafted entry contains a standalone WF: marker line - refusing "
                     "(it would inject bogus structure). Remove column-0 WF: comment lines.")

    # 2) Resolve scope + placement from the mode (and, for sections, the CLI intent).
    block_key = pub["block_key"]
    anchor_slug = pub["anchor_slug"]
    if mode == "log":
        if args.section or args.new or args.update:
            return _fail("--section/--new/--update are section-mode only; step '{}' publishes a log."
                         .format(step))
        scope = marker.get("task_id", "unknown")
        placement = "prepend"
    else:   # section
        if not args.section:
            return _fail("step '{}' publishes a section; --section <slug> is required.".format(step))
        if not re.fullmatch(_SCOPE_RE, args.section):
            return _fail("--section slug {!r} must match {}.".format(args.section, _SCOPE_RE))
        if bool(args.new) == bool(args.update):
            return _fail("section publish needs exactly one of --new / --update.")
        scope = args.section
        placement = "append_section"

    # 3) The target doc must already exist - place INTO a real doc, never create one.
    #    Raw bytes preserve newlines on any Python 3; work in LF space and restore the
    #    doc's newline style on write (so a Windows publish can't flip the whole file).
    target = Path(root) / pub["doc_target"]
    try:
        raw = target.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return _fail("publish target {} does not exist. Nothing published.".format(target))
    except (OSError, UnicodeDecodeError):
        return _fail("publish target {} is unreadable. Nothing published.".format(target))
    doc_nl = "\r\n" if "\r\n" in raw else "\n"
    # Normalize ALL CommonMark line terminators to LF (CRLF *and* a lone CR), not just CRLF, so the
    # section-count check below and _place_block interpret lines exactly as a Markdown renderer does.
    # A bare \r before a fence delimiter otherwise hides/false-flags a marker (convergence round-3).
    # A rare bare-CR doc thus normalizes to LF on write (doc_nl is LF when no CRLF is present) -
    # acceptable and consistent with the existing newline homogenization (RISKS #10; docs pinned LF).
    doc = raw.replace("\r\n", "\n").replace("\r", "\n")

    # 4) Section intent check (fail-closed on count mismatch) - turns a mistargeted
    #    --section into a refusal, not a silent overwrite of the wrong section.
    if mode == "section":
        start_pat, _ = _block_patterns(block_key, scope)
        existing = len(start_pat.findall(doc))
        if args.new and existing != 0:
            return _fail("--new but WF:{}:{} already exists ({} found). Refusing."
                         .format(block_key, scope, existing))
        if args.update and existing != 1:
            return _fail("--update but WF:{}:{} has {} match(es) (need exactly 1). Refusing."
                         .format(block_key, scope, existing))

    # 5) Place the block through the fail-closed engine. `new_doc` now holds the entry's content,
    #    so the entry file itself is no longer needed.
    try:
        new_doc = _place_block(doc, block_key, scope, anchor_slug, placement, entry)
    except _PublishError as exc:
        return _fail(str(exc) + " Nothing published.")

    # 6) Consume the drafted entry BEFORE writing, and fail closed if it cannot be removed. A
    #    successful publish must NEVER leave a reusable entry: a surviving entry would be silently
    #    re-published under the NEXT publish's scope - which, for a different `--section`, emits the
    #    wrong content (convergence round-2 BLOCKING #1; the earlier "idempotent" reasoning held only
    #    for the SAME scope). Consuming first also makes every publish require a freshly-drafted entry.
    try:
        entry_path(root).unlink()
    except OSError as exc:
        return _fail("cannot consume the drafted entry ({}) - refusing to publish, because a surviving "
                     "entry could be silently re-used for another scope. Close whatever holds {} and "
                     "retry.".format(exc, entry_path(root)))

    # 7) Write atomically; a locked/failed target yields a clean _fail, not a traceback. (The entry is
    #    already consumed, so a failed write means redraft-and-retry - the safe, fail-closed trade.)
    try:
        _atomic_write_text(target, new_doc.replace("\n", doc_nl))   # restore the doc's newline style
    except OSError as exc:
        return _fail("could not write {} ({}). Nothing published; redraft the entry to retry.".format(target, exc))
    print("published '{}' -> {} (mode={}, scope={}).".format(step, target, mode, scope))
    return 0


def cmd_status(args):
    """Human-readable readout of the marker. (The status line - M5 - renders its own
    compact version by importing receipt_state; this verb is for the terminal.)"""
    root = _walk_up_for_marker(Path.cwd())
    if root is None:
        print("no task open (machinery inert here).")
        return 0
    _print_root(root)
    marker = load_marker(root)
    if not marker:
        print("no task open (machinery inert here).")
        return 0
    print("task '{}' [{}]".format(marker["task_title"], marker["task_id"]))
    print("current step: {}".format(marker["current_step"]))
    cur_idx = STEPS.index(marker["current_step"])
    for i, step in enumerate(STEPS):
        if i > cur_idx:
            break
        state = receipt_state(step, root=root, marker=marker)
        rec = marker.get("receipts", {}).get(step, {})
        tag = "  <- current" if step == marker["current_step"] else ""
        over = " (overridden)" if rec.get("override") else ""
        print("  {:14s} {}{}{}".format(step, state, over, tag))
    if marker.get("pending"):
        print("challenge pending for: {}".format(marker["pending"]["step"]))
    return 0


def cmd_reset(args):
    """End the task: remove all runtime state. The committed docs remain; only this
    task's live machine output goes away, leaving the machinery inert.

    D-10 widened WHAT is cleared: the drafts now live in .workflow/ (so each draft-<step>.md
    is task output that dies with reset), and the M5 nudge's quiet-hash (nudge-state.json) dies
    too. Two files are SPARED on purpose: global-habits.md (a hand-authored WARM input, not
    machine output) and .gitignore (`start` owns it; it must persist so .workflow/ stays
    self-ignoring even after a reset). Still a FIXED list, not a glob - the single-file
    quiet-hash is what keeps it enumerable.

    A file that is already gone is the intended, benign case; a file that EXISTS but
    cannot be deleted (e.g. locked by an editor or a OneDrive sync) is a real failure
    and is reported - never swallowed under a false 'cleared'."""
    root = _walk_up_for_marker(Path.cwd())
    if root is None:
        return _fail("no task open at or above {} - nothing to reset.".format(Path.cwd()))
    _print_root(root)
    targets = [marker_path(root), context_path(root), challenge_path(root), entry_path(root),
               wf_dir(root) / "nudge-state.json"]
    targets += [draft_path(root, step) for step in STEPS]   # D-10: drafts are task output now
    failed = []
    for p in targets:
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            failed.append("{} ({})".format(p.name, exc))
    if failed:
        return _fail("could not clear: " + "; ".join(failed) + ". Task state may persist - "
                     "close whatever is holding the file and retry.")
    print("reset: task state cleared.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="workflow", description="Six-step workflow machinery (all step rows + publish engine).")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="bootstrap a task (human-owned entry)")
    s.add_argument("title")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("prepare", help="assemble the challenger bundle (rulebook + cold/warm + canary)")
    s.add_argument("step", choices=STEPS)
    s.set_defaults(func=cmd_prepare)

    s = sub.add_parser("record", help="verify the challenger result and write the receipt")
    s.add_argument("step", choices=STEPS)
    s.set_defaults(func=cmd_record)

    s = sub.add_parser("advance", help="move to the next step (gated; --force to override)")
    s.add_argument("--force", action="store_true", help="advance without a fresh receipt (recorded)")
    s.set_defaults(func=cmd_advance)

    s = sub.add_parser("publish", help="place the settled prose into its doc (log or section mode)")
    s.add_argument("step", choices=STEPS)
    s.add_argument("--section", help="section-slug (required for a section-mode publish)")
    s.add_argument("--new", action="store_true", help="section mode: require the section does NOT exist yet")
    s.add_argument("--update", action="store_true", help="section mode: require the section already exists")
    s.set_defaults(func=cmd_publish)

    s = sub.add_parser("status", help="print the current task state")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("reset", help="clear task state")
    s.set_defaults(func=cmd_reset)
    return p


def main(argv=None):
    # Make stdout/stderr tolerate non-ASCII task titles (e.g. an arrow in a title) on
    # Windows' legacy cp1252 console, so a print can never crash AFTER the state write and
    # leave "failed" and "succeeded" both looking true. Best-effort: if a stream can't be
    # reconfigured, the verbs' own literal text is ASCII anyway.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
