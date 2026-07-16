#!/usr/bin/env python3
"""sync.py — deploy the working methodology into ~/.claude, or capture live edits back.

One cross-platform entry point (Windows + macOS/Linux), standard-library only, so it runs
anywhere Python 3 is present with nothing to install.

    python  sync.py               # THE everyday command: update — pull the latest, then install
    python  sync.py status        # report where you stand: GitHub <-> repo <-> live (read-only)
    python  sync.py enable-hook   # (once) get told at Claude Code startup when an update exists

  Occasional / under the hood:
    python  sync.py update        # explicit form of the no-arg command (git pull + install)
    python  sync.py install       # deploy the files here into ~/.claude (no pull)
    python3 sync.py capture       # ~/.claude -> repo (pull your live edits back to the repo)
    python  sync.py check         # manual "is a newer version published?" (the hook does this)
    python  sync.py disable-hook  # remove the notification hook

The repo is the source of truth. `install` writes the live side; `capture` writes the repo
side. There is no merge — each direction overwrites — but `install` keeps a timestamped
backup of whatever it replaced, so nothing is ever clobbered silently.
"""

# `from __future__` keeps the type hints below (e.g. `list[str] | None`) valid on the older
# Python 3.8/3.9 that a Linux box might ship — annotations become strings, never evaluated.
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- The bundle manifest -----------------------------------------------------------------
# The SINGLE source of truth for which files this repo owns inside ~/.claude, as paths
# RELATIVE to the .claude root. Written with POSIX "/" separators; pathlib rewrites them to
# "\" on Windows automatically. Add a new bundled file here once and BOTH directions
# (install + capture) pick it up — there is no second list to keep in sync.
MANIFEST = [
    "CLAUDE.md",
    "METHODOLOGY.md",
    "skills/init-project-docs/SKILL.md",
    "VERSION",                     # machine-readable current version (single source of truth)
    "CHANGELOG.md",                # parseable release history; source of the update-notice delta
    "hooks/check_version.py",      # deployed SessionStart hook that checks GitHub for updates
    "statusline.py",               # deployed status-line renderer: model|effort|context|quota
    # M5 (D-8): the six-step workflow machinery + its M5 control layer. The SCRIPTS ship here like
    # everything else; the status line and the nudge are ACTIVATED per-machine by `enable-workflow`
    # (settings.json is deliberately NOT in the manifest, so install/capture never touch it - D-1).
    "workflow/workflow.py",        # the deterministic spine (verbs + the importable receipt_state)
    "workflow/rulebook.md",        # the nine shared challenger rules, bundled by `prepare`
    "workflow/conductor.md",       # the per-step loop; the nudge injects the slice between its sentinels
    "agents/challenger.md",        # the challenger subagent definition
    "workflow/nudge.py",           # the M5 UserPromptSubmit + SessionStart reminder hook
    "statusline_wf.py",            # the M5 workflow-aware status line (base line + wf:<step>:<state>)
]

# Anchor every path off this script's own folder so the repo can be moved or renamed without
# breaking anything (the cross-platform equivalent of PowerShell's $PSScriptRoot).
REPO_ROOT = Path(__file__).resolve().parent   # the repo root (folder holding this script)
BUNDLE_DIR = REPO_ROOT / "claude"             # the repo's mirror of ~/.claude
# Path.home() resolves %USERPROFILE% on Windows and $HOME on macOS/Linux — this one line is
# what makes the whole script cross-platform.
TARGET_DIR = Path.home() / ".claude"          # this machine's live ~/.claude


def _timestamped_backup(dst: Path) -> Path:
    """Copy an existing file to `dst.<YYYYMMDD-HHMMSS>.bak` and return the backup path.

    ONE backup convention shared by everything that overwrites a live file — the file installs
    below and the settings.json hook merge further down — so a replaced file is always
    recoverable. The caller guarantees `dst` already exists.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = dst.with_name(f"{dst.name}.{stamp}.bak")
    shutil.copy2(dst, bak)
    return bak


def _copy(src: Path, dst: Path, *, backup: bool) -> bool:
    """Copy one file src -> dst, creating parent folders as needed.

    If `backup` is set and `dst` already exists, first copy it to `dst.<timestamp>.bak` so a
    replaced file is always recoverable. Returns True on success, or False when `src` is
    missing — in which case we warn and carry on (parity with the old .ps1 scripts, so one
    missing file never aborts the whole run).
    """
    if not src.exists():
        print(f"  ! missing, skipped: {src}", file=sys.stderr)
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)   # ensure the destination folder exists
    if backup and dst.exists():                     # never clobber silently: back up first
        bak = _timestamped_backup(dst)
        print(f"  backed up {dst.name} -> {bak.name}")
    shutil.copy2(src, dst)                           # copy2 preserves mtime + permission bits
    return True


def install() -> None:
    """repo -> ~/.claude: deploy the bundle onto this machine, backing up replaced files."""
    for rel in MANIFEST:
        # src lives in the repo's `claude/` mirror; dst is the same relative path under ~/.claude
        if _copy(BUNDLE_DIR / rel, TARGET_DIR / rel, backup=True):
            print(f"  installed {rel}")
    print("\nDone. Restart Claude Code, then check /skills lists 'init-project-docs'.")
    print("Tip: run  python sync.py enable-hook  for in-session update notifications.")
    print("Tip: run  python sync.py enable-statusline  to show model|effort|context|quota in the status line.")
    print("Tip: run  python sync.py enable-workflow  to turn on the six-step workflow (nudge + wf status line).")


def capture() -> None:
    """~/.claude -> repo: pull live edits back so they can be committed.

    No backup on this side: the repo is git-tracked, so `git` history (and `git diff` before
    you commit) is the safety net.
    """
    for rel in MANIFEST:
        if _copy(TARGET_DIR / rel, BUNDLE_DIR / rel, backup=False):
            print(f"  captured {rel}")
    print("\nDone. Now:  git add -A;  git commit -m 'update methodology';  git push")


# --- Update-check + SessionStart hook wiring ---------------------------------------------
# The check LOGIC lives in the deployed hook script (claude/hooks/check_version.py), because
# THAT file — not sync.py — is what ships into ~/.claude and runs as the hook. sync.py loads
# that same module to power `sync.py check`, so there is exactly one copy of the logic (P4/P5).
CHECK_SCRIPT_REL = "hooks/check_version.py"     # path inside the bundle AND inside ~/.claude
STATUSLINE_REL = "statusline.py"                # the plain status-line script (both sides)
STATUSLINE_WF_REL = "statusline_wf.py"          # the M5 workflow-aware status line
NUDGE_REL = "workflow/nudge.py"                 # the M5 nudge hook (SessionStart + UserPromptSubmit)
SETTINGS_FILE = TARGET_DIR / "settings.json"    # Claude Code's user settings (personal file!)


def _load_check_module():
    """Import the bundle's check_version.py as a module so `check` reuses the hook's own logic."""
    path = BUNDLE_DIR / CHECK_SCRIPT_REL
    spec = importlib.util.spec_from_file_location("check_version", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)             # runs the file's top level, exposing run_check()
    return module


def check() -> None:
    """Manually check whether a newer methodology version is published (verbose, no throttle)."""
    _load_check_module().run_check(verbose=True, use_throttle=False)


def _read_settings() -> dict:
    """Load ~/.claude/settings.json as a dict; {} if it doesn't exist yet.

    If the file exists but cannot be used as a settings OBJECT — unparseable JSON, OR valid JSON
    that is a list/number/string — this raises ValueError (json.JSONDecodeError is itself a
    ValueError). The caller catches it and ABORTS WITHOUT WRITING, because we must never overwrite
    a personal settings file we could not safely parse into the dict every verb mutates. (Widened
    in M5: a non-object parse previously slipped past the guard and crashed a verb's `.setdefault`
    with a raw traceback instead of the graceful refuse.)
    """
    if not SETTINGS_FILE.exists():
        return {}
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))   # JSONDecodeError (a ValueError) if unparseable
    if not isinstance(data, dict):
        raise ValueError(f"settings.json is not a JSON object (got {type(data).__name__})")
    return data


def _write_settings(settings: dict) -> None:
    """Write settings.json back with 2-space indent + trailing newline (matching the live file)."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def _python_command(script_rel: str) -> str:
    """Build a command that runs THIS interpreter against a deployed bundle script.

    Like `_hook_command` below, but reusable for any relative script path (e.g. the status line).
    Uses `sys.executable` — the exact Python running sync.py — never a bare `python`, which on
    some machines is the Windows Store alias stub and would silently never run (RISK #6). Both
    paths are quoted so a space can't split the command in the shell Claude Code invokes it in.
    """
    script = TARGET_DIR / script_rel
    return f'"{sys.executable}" "{script}"'


def _hook_command() -> str:
    """Build the hook command: THIS Python interpreter (absolute) + the deployed script (absolute).

    We embed `sys.executable` rather than a bare `python`, because on some machines `python`
    resolves to the Windows Store alias stub, not a real interpreter — a bare command would
    silently never run (this repo's RISK #6, now reaching the hook). Both paths are quoted so a
    space (e.g. "C:\\Program Files\\...") can't split the command.
    """
    script = TARGET_DIR / CHECK_SCRIPT_REL
    return f'"{sys.executable}" "{script}"'


def _command_refers_to(command: str, script_rel: str) -> bool:
    """True if a settings command string points at the bundle script `script_rel` — matched on the
    NORMALISED path (slashes stripped, lower-cased), not the exact string, so a re-run after the
    interpreter path changed still finds the existing entry instead of adding a duplicate. Windows
    paths are case-insensitive and mix "/" and "\\", hence the fold (the DOT is kept - only slashes
    are stripped). This is the SINGLE identity test shared by the hook predicates below AND
    enable_statusline's preserve-the-script logic (D-8).

    The two status-line scripts stay distinguishable under it: `statusline.py` normalises to
    'statusline.py', which is NOT a substring of `statusline_wf.py`'s 'statusline_wf.py' (after
    'statusline' comes '.' vs '_wf'), so neither matches the other's command. CAUTION, therefore:
    only ever match against the MORE SPECIFIC needle (STATUSLINE_WF_REL, or a hook script). Matching
    a command against the plain STATUSLINE_REL needle ('statusline.py') is done NOWHERE and must not
    be - an interpreter path literally containing 'statusline.py' would false-positive on it."""
    needle = script_rel.replace("/", "").replace("\\", "").lower()
    haystack = command.replace("/", "").replace("\\", "").lower()
    return needle in haystack


def _hook_refers_to_check(command: str) -> bool:
    """True if a hook command points at our update-check script (identity; see _command_refers_to)."""
    return _command_refers_to(command, CHECK_SCRIPT_REL)


def _hook_refers_to_nudge(command: str) -> bool:
    """True if a hook command points at our M5 nudge script (identity; see _command_refers_to)."""
    return _command_refers_to(command, NUDGE_REL)


def _register_hook(settings: dict, event: str, matcher: str | None, command: str, refers_to) -> bool:
    """Idempotently add a command hook under hooks.<event>, in place, on the settings DICT (no I/O).
    If a hook matching `refers_to` already exists, refresh ITS command (the interpreter may have
    moved) and return True; otherwise append one matcher group and return False. `matcher=None`
    registers a group with NO matcher field (UserPromptSubmit takes none). The
    setdefault -> match -> refresh-or-append idiom lives HERE so enable-hook and enable-workflow
    share exactly one implementation (P4/P5)."""
    groups = settings.setdefault("hooks", {}).setdefault(event, [])
    for group in groups:
        for entry in group.get("hooks", []):
            if entry.get("type") == "command" and refers_to(entry.get("command", "")):
                entry["command"] = command
                return True
    hook = {"type": "command", "command": command, "timeout": 10}
    groups.append({"matcher": matcher, "hooks": [hook]} if matcher is not None else {"hooks": [hook]})
    return False


def _deregister_hook(settings: dict, event: str, refers_to) -> bool:
    """Idempotently remove every command hook matching `refers_to` from hooks.<event> on the settings
    DICT (no I/O), pruning any emptied group and the event/hooks structures if they empty out.
    Returns True if it removed anything. Shared by disable-hook and disable-workflow."""
    groups = settings.get("hooks", {}).get(event, [])
    if not any(refers_to(e.get("command", "")) for g in groups for e in g.get("hooks", [])):
        return False
    kept = []
    for group in groups:
        entries = [e for e in group.get("hooks", []) if not refers_to(e.get("command", ""))]
        if entries:                             # keep groups that still have other hooks
            group["hooks"] = entries
            kept.append(group)
    if kept:
        settings["hooks"][event] = kept
    else:                                       # prune a dangling "<event>": [] and an empty "hooks": {}
        settings["hooks"].pop(event, None)
        if not settings.get("hooks"):
            settings.pop("hooks", None)
    return True


def enable_hook() -> None:
    """Register the SessionStart update-check hook in ~/.claude/settings.json (idempotent).

    Backs the file up first, preserves every existing setting, and either refreshes our hook in
    place (if already present) or appends it once — so re-running is always safe.
    """
    try:
        settings = _read_settings()
    except ValueError as exc:
        print(f"  ! {SETTINGS_FILE} could not be read as a settings object ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if SETTINGS_FILE.exists():
        bak = _timestamped_backup(SETTINGS_FILE)
        print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    # "startup" fires only on fresh sessions (not resume/compact); a short timeout keeps a slow
    # network from delaying session start.
    refreshed = _register_hook(settings, "SessionStart", "startup", _hook_command(), _hook_refers_to_check)
    _write_settings(settings)
    if refreshed:
        print("  refreshed the existing SessionStart update-check hook.")
    else:
        print("  enabled the SessionStart update-check hook.")
        print("  new Claude Code sessions will now flag when a newer methodology is published.")


def disable_hook() -> None:
    """Remove the SessionStart update-check hook from ~/.claude/settings.json (idempotent)."""
    try:
        settings = _read_settings()
    except ValueError as exc:
        print(f"  ! {SETTINGS_FILE} could not be read as a settings object ({exc}); refusing to touch it.", file=sys.stderr)
        return
    # _deregister_hook returns False WITHOUT mutating when nothing matches (so a no-op writes
    # nothing); on a real removal it mutates the in-memory dict, and the backup below still captures
    # the intact on-disk file before _write_settings persists the change.
    if not _deregister_hook(settings, "SessionStart", _hook_refers_to_check):
        print("  no update-check hook was present; nothing to do.")
        return
    bak = _timestamped_backup(SETTINGS_FILE)
    print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    _write_settings(settings)
    print("  removed the SessionStart update-check hook.")


def enable_statusline() -> None:
    """Point Claude Code's status line at the bundled renderer, refreshing the interpreter (idempotent).

    D-8 change: this must PRESERVE the workflow-aware statusline_wf.py that `enable-workflow` installs
    and only rewrite the interpreter. Left as a flat assign, re-running it after an interpreter move
    (RISKS #7's recorded new-box / post-move routine) would silently REVERT the wf:<step>:<state>
    segment. The plain statusline.py is assigned whenever the current renderer is NOT the wf one — a
    fresh file, an already-plain line, or anything else — and its interpreter is refreshed too. Backs
    up first; every other key untouched.
    """
    try:
        settings = _read_settings()
    except ValueError as exc:
        print(f"  ! {SETTINGS_FILE} could not be read as a settings object ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if SETTINGS_FILE.exists():                      # never rewrite the personal file without a backup
        bak = _timestamped_backup(SETTINGS_FILE)
        print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    # Always refresh the interpreter to THIS sys.executable (the RISKS #7 post-move repair); preserve
    # the SCRIPT when the wf renderer is already active, else set the plain one.
    current = settings.get("statusLine")
    keep_wf = isinstance(current, dict) and _command_refers_to(current.get("command", ""), STATUSLINE_WF_REL)
    script_rel = STATUSLINE_WF_REL if keep_wf else STATUSLINE_REL
    settings["statusLine"] = {"type": "command", "command": _python_command(script_rel)}
    _write_settings(settings)
    label = "workflow-aware: base line + wf:<step>:<state>" if keep_wf else "model | effort | context | quota"
    print(f"  enabled the status line ({label}).")
    print("  restart Claude Code to see it under the prompt.")


def disable_statusline() -> None:
    """Remove the status line from ~/.claude/settings.json (idempotent)."""
    try:
        settings = _read_settings()
    except ValueError as exc:
        print(f"  ! {SETTINGS_FILE} could not be read as a settings object ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if "statusLine" not in settings:                # nothing configured — say so and stop
        print("  no status line was configured; nothing to do.")
        return
    bak = _timestamped_backup(SETTINGS_FILE)
    print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    settings.pop("statusLine", None)                # drop only our key; leave the rest as-is
    _write_settings(settings)
    print("  removed the status line.")


def enable_workflow(which: str = "all") -> None:
    """Activate the M5 control layer on THIS machine (idempotent): the nudge hook (SessionStart +
    UserPromptSubmit) and/or the workflow-aware status line. `which` is 'nudge', 'statusline' or
    'all'. Every write targets the USER settings.json (D-1) — which is NOT in the manifest, so
    activation is per-machine and never carried by install/capture (Need 5.10's "installed AND
    used" is per box). Like enable-statusline it embeds sys.executable, so it is ALSO the repair
    command after the interpreter path moves (RISKS #6/#7)."""
    try:
        settings = _read_settings()
    except ValueError as exc:
        print(f"  ! {SETTINGS_FILE} could not be read as a settings object ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if SETTINGS_FILE.exists():
        bak = _timestamped_backup(SETTINGS_FILE)
        print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    if which in ("nudge", "all"):
        cmd = _python_command(NUDGE_REL)
        # SessionStart on all four source legs (probe-verified to fire alongside check_version's own
        # "startup" group); UserPromptSubmit takes no matcher.
        _register_hook(settings, "SessionStart", "startup|resume|clear|compact", cmd, _hook_refers_to_nudge)
        _register_hook(settings, "UserPromptSubmit", None, cmd, _hook_refers_to_nudge)
        print("  enabled the workflow nudge (SessionStart + UserPromptSubmit).")
    if which in ("statusline", "all"):
        settings["statusLine"] = {"type": "command", "command": _python_command(STATUSLINE_WF_REL)}
        print("  enabled the workflow-aware status line (adds wf:<step>:<state>).")
    _write_settings(settings)
    print("  restart Claude Code to activate. (Per machine: settings.json is not carried by sync.)")


def disable_workflow(which: str = "all") -> None:
    """Deactivate the M5 control layer on THIS machine (idempotent). `which` is 'nudge',
    'statusline' or 'all'. Removing the nudge leaves the status line alone; removing the status line
    reverts it to the plain statusline.py — but only if it currently points at the wf renderer —
    leaving the nudge alone. Nothing to revert -> says so and writes nothing (no needless backup)."""
    try:
        settings = _read_settings()
    except ValueError as exc:
        print(f"  ! {SETTINGS_FILE} could not be read as a settings object ({exc}); refusing to touch it.", file=sys.stderr)
        return
    # Work out what there is to do FIRST, so we back up + write only when something actually changes.
    nudge_present = any(
        _hook_refers_to_nudge(e.get("command", ""))
        for event in ("SessionStart", "UserPromptSubmit")
        for g in settings.get("hooks", {}).get(event, [])
        for e in g.get("hooks", []))
    remove_nudge = which in ("nudge", "all") and nudge_present
    current_sl = settings.get("statusLine")
    revert_sl = (which in ("statusline", "all") and isinstance(current_sl, dict)
                 and _command_refers_to(current_sl.get("command", ""), STATUSLINE_WF_REL))
    if not remove_nudge and not revert_sl:
        print("  nothing to disable (the workflow control layer isn't active here).")
        return
    if SETTINGS_FILE.exists():
        bak = _timestamped_backup(SETTINGS_FILE)
        print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    if remove_nudge:
        _deregister_hook(settings, "SessionStart", _hook_refers_to_nudge)
        _deregister_hook(settings, "UserPromptSubmit", _hook_refers_to_nudge)
        print("  removed the workflow nudge.")
    if revert_sl:
        settings["statusLine"] = {"type": "command", "command": _python_command(STATUSLINE_REL)}
        print("  reverted the status line to the plain statusline.py.")
    _write_settings(settings)


# --- Status: "where do I stand?" (GitHub <-> repo <-> live ~/.claude) ---------------------
# A READ-ONLY readout. `status` never commits, pushes, pulls, installs, or edits any file — it
# only looks and prints. It answers "am I fully in sync?" across the whole chain:
#     GitHub   <->   this repo   <->   the live ~/.claude on this machine
# The GitHub<->repo half mirrors what `git status` could tell you; the repo<->live half is the
# genuinely useful part, because no git command can see ~/.claude — only we can tell you
# "you pulled new files but haven't run install, so your live setup is behind the repo".


def _git(*args, timeout=None):
    """Run `git -C <repo> <args>`; return (returncode, stdout, stderr) as stripped strings.

    A defensive wrapper so the caller never crashes: if git isn't installed (FileNotFoundError)
    or a network `fetch` hangs past `timeout`, we return a non-zero code with the reason in
    stderr, and the caller turns that into a plain-English line. `GIT_TERMINAL_PROMPT=0` stops
    git from popping an interactive credential prompt (which could hang a fetch on a machine with
    no stored auth) — it fails fast instead, which we report as "couldn't reach GitHub".
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args],
            capture_output=True, text=True, env=env, timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", "git was not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, "", "git timed out"


def _git_status() -> dict:
    """Work out where the repo stands versus GitHub. Returns a small dict describing it.

    `kind` is one of:
      'not_git'   — a plain folder copy (no .git); nothing to compare to GitHub.
      'no_remote' — a git repo, but this branch has no GitHub tracking branch to compare against.
      'ok'        — comparable; the dict then also carries:
                      uncommitted (int)  how many changes aren't committed,
                      reached (bool)     did the network fetch actually reach GitHub,
                      ahead (int)        commits you have that GitHub doesn't,
                      behind (int)       commits GitHub has that you don't.
    """
    # A USB/OneDrive-style plain copy has no .git, so there's nothing git can tell us.
    if not (REPO_ROOT / ".git").exists():
        return {"kind": "not_git"}

    # Uncommitted work = every line `git status --porcelain` prints (modified/staged/untracked).
    rc, out, _ = _git("status", "--porcelain")
    uncommitted = len(out.splitlines()) if rc == 0 and out else 0

    # `@{upstream}` is this branch's GitHub tracking branch. If it isn't set, there's nothing on
    # GitHub to compare to (e.g. a brand-new local branch) — say so rather than guess.
    rc_up, _, _ = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if rc_up != 0:
        return {"kind": "no_remote", "uncommitted": uncommitted}

    # The one network step: refresh our copy of GitHub's state. Cap it so a dead network can't
    # hang the command, and remember whether it actually succeeded (offline => stale comparison).
    rc_fetch, _, _ = _git("fetch", "--quiet", timeout=15)
    reached = rc_fetch == 0

    # Count the gap. With `@{upstream}...HEAD`, the left count is commits on GitHub-not-here
    # (behind) and the right count is commits here-not-on-GitHub (ahead).
    rc_c, counts, _ = _git("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
    behind = ahead = 0
    parts = counts.split()
    if rc_c == 0 and len(parts) == 2:
        behind, ahead = int(parts[0]), int(parts[1])

    return {"kind": "ok", "uncommitted": uncommitted, "reached": reached,
            "ahead": ahead, "behind": behind}


def _live_status() -> list:
    """Compare each bundle-owned file in the repo against its live ~/.claude copy, byte for byte.

    Returns a list of (relative_path, state) for every file NOT in sync — state is 'missing'
    (never installed on this machine) or 'differs' (the live copy isn't the repo's current copy).
    An empty list means the live ~/.claude is fully up to date. Read-only: it reads bytes only.
    """
    out_of_sync = []
    for rel in MANIFEST:
        repo_file = BUNDLE_DIR / rel
        live_file = TARGET_DIR / rel
        # A file the manifest names but the repo lacks is a repo/bundle problem, not a live one;
        # install/capture already warn about a missing source, so we just skip it here.
        if not repo_file.exists():
            continue
        if not live_file.exists():
            out_of_sync.append((rel, "missing"))
        elif repo_file.read_bytes() != live_file.read_bytes():
            out_of_sync.append((rel, "differs"))
    return out_of_sync


def status() -> int:
    """Print where this machine stands across GitHub <-> repo <-> live ~/.claude, and return an
    exit code: 0 when everything is confirmed in sync, 1 when there's something to do (or we
    couldn't fully confirm, e.g. offline). Read-only — it changes nothing.
    """
    git = _git_status()
    live = _live_status()

    lines = []      # the report lines we'll print, one situation each
    todo = []       # plain-English next steps, collected as we find things out of sync
    synced = True   # flips to False on anything not confirmed in sync

    # --- GitHub <-> repo ---------------------------------------------------------------------
    if git["kind"] == "not_git":
        lines.append("  GitHub   this is a plain copy (no git) - can't compare to GitHub.")
        synced = False
    elif git["kind"] == "no_remote":
        lines.append("  GitHub   no GitHub link for this branch - nothing to compare.")
        synced = False
        if git["uncommitted"]:
            lines.append(f"           (plus {git['uncommitted']} uncommitted change(s) here.)")
    else:
        parts = []
        if git["uncommitted"]:
            parts.append(f"{git['uncommitted']} uncommitted change(s)")
            todo.append("commit your changes when ready:  git add -A; git commit")
        # Ahead AND behind at once = the histories have diverged; report that as one thing rather
        # than two, because the fix (reconcile by hand) is different from a plain push or pull.
        if git["ahead"] and git["behind"]:
            parts.append(f"DIVERGED: {git['ahead']} local vs {git['behind']} on GitHub "
                         "(reconcile by hand)")
        elif git["ahead"]:
            parts.append(f"{git['ahead']} commit(s) not pushed to GitHub yet")
            todo.append("push to GitHub when ready:  git push")
        elif git["behind"]:
            parts.append(f"GitHub is ahead by {git['behind']} commit(s)")
            todo.append("pull GitHub's changes:  python sync.py")

        if not git["reached"]:
            # We couldn't refresh from GitHub, so anything we say about ahead/behind is only as
            # current as the last successful fetch — flag that rather than imply certainty.
            synced = False
            if parts:
                lines.append("  GitHub   " + "; ".join(parts)
                             + "  (couldn't reach GitHub - may be out of date).")
            else:
                lines.append("  GitHub   couldn't reach GitHub (offline?) - in sync as far as we "
                             "last knew.")
        elif parts:
            synced = False
            lines.append("  GitHub   " + "; ".join(parts) + ".")
        else:
            lines.append("  GitHub   in sync - nothing to push or pull.")

    # --- repo <-> live ~/.claude -------------------------------------------------------------
    if live:
        synced = False
        missing = sum(1 for _, s in live if s == "missing")
        differ = sum(1 for _, s in live if s == "differs")
        detail = []
        if differ:
            detail.append(f"{differ} file(s) older than the repo")
        if missing:
            detail.append(f"{missing} file(s) not installed yet")
        lines.append("  Live     behind - " + ", ".join(detail) + ".")
        todo.append("update your live ~/.claude:  python sync.py install")
    else:
        lines.append("  Live     up to date - ~/.claude matches the repo.")

    # --- print the readout -------------------------------------------------------------------
    print("Where you stand:\n")
    print("\n".join(lines))
    if todo:
        print("\nWhat to do:")
        for step in todo:
            print(f"  - {step}")
    else:
        print("\nAll in sync. Nothing to do.")
    return 0 if synced else 1


def update() -> None:
    """One-command update: `git pull` the repo, then `install` the refreshed files into ~/.claude.

    This is the "apply" step that the update-check hook only *notifies* about. It works only from
    a git checkout with a reachable remote — a USB/OneDrive copy has no `.git`, so we say so and
    stop. We pull with `--ff-only` so it can only fast-forward: if local history has diverged (say
    you made local commits), it fails cleanly instead of creating a surprise merge, and we do NOT
    deploy a half-updated tree.
    """
    # A plain folder copy (no .git) can't pull — tell the user how to refresh it by hand.
    if not (REPO_ROOT / ".git").exists():
        print("  ! Not a git checkout, so there's nothing to pull.", file=sys.stderr)
        print("    Refresh this folder yourself (git clone / re-download / re-copy), then run:")
        print("      python sync.py install")
        return

    print("Pulling the latest methodology from the remote...")
    try:
        pull = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:                       # git isn't installed / not on PATH
        print("  ! git was not found on PATH.", file=sys.stderr)
        print("    Install git (or pull manually), then run:  python sync.py install")
        return

    # Echo git's own summary ("Already up to date." / "Fast-forward ...") so the user sees it.
    if pull.stdout.strip():
        print(pull.stdout.strip())
    if pull.returncode != 0:
        # Network down, diverged history, or local edits blocking the pull — do NOT deploy.
        print("  ! git pull failed — not deploying anything.", file=sys.stderr)
        detail = (pull.stderr or pull.stdout).strip()
        if detail:
            print("    " + detail.replace("\n", "\n    "), file=sys.stderr)
        print("    Fix it (commit/stash local edits, or check your network), then retry.", file=sys.stderr)
        return

    # Pull succeeded (fast-forwarded or already current) -> deploy the now-current files.
    print()
    install()


def default_action() -> None:
    """What `python sync.py` with NO subcommand does: bring this machine up to date.

    This is the everyday command. On a git checkout it runs `update` (pull the latest, then
    install); on a plain folder copy (no `.git`, so nothing to pull) it just `install`s what's
    here. Everything else — capture, check, enable-hook, disable-hook — is a named subcommand.
    """
    print("No command given — bringing ~/.claude up to date (run  python sync.py -h  for the rest).\n")
    if (REPO_ROOT / ".git").exists():
        update()          # git checkout: pull the latest, then install
    else:
        install()         # plain copy: nothing to pull, just deploy what's here


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync the working methodology with ~/.claude. Run with NO command to update "
                    "(pull the latest, then install) — the everyday one. The subcommands below "
                    "are for occasional cases.",
    )
    # dest="command" lets us tell "no subcommand" apart from a real one below.
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("install", help="repo -> ~/.claude (backs up anything it replaces)")
    sub.add_parser("update", help="git pull the latest, then install (one-command update)")
    sub.add_parser("capture", help="~/.claude -> repo (stage live edits for commit)")
    sub.add_parser("check", help="check GitHub for a newer methodology version (verbose)")
    sub.add_parser("status", help="report where you stand: GitHub <-> repo <-> live ~/.claude (read-only)")
    sub.add_parser("enable-hook", help="notify at Claude Code startup when an update exists")
    sub.add_parser("disable-hook", help="remove the update-check hook")
    sub.add_parser("enable-statusline", help="show model|effort|context|quota in the status line")
    sub.add_parser("disable-statusline", help="remove the status line")
    p_ew = sub.add_parser("enable-workflow", help="activate the workflow nudge + status line on this machine")
    p_ew.add_argument("which", nargs="?", choices=["nudge", "statusline", "all"], default="all",
                      help="which piece to activate (default: all)")
    p_dw = sub.add_parser("disable-workflow", help="deactivate the workflow nudge + status line on this machine")
    p_dw.add_argument("which", nargs="?", choices=["nudge", "statusline", "all"], default="all",
                      help="which piece to deactivate (default: all)")

    args = parser.parse_args(argv)
    if args.command == "install":
        install()
    elif args.command == "update":
        update()
    elif args.command == "capture":
        capture()
    elif args.command == "check":
        check()
    elif args.command == "status":
        # status returns its own exit code (0 = fully in sync, 1 = something to do) — pass it up.
        return status()
    elif args.command == "enable-hook":
        enable_hook()
    elif args.command == "disable-hook":
        disable_hook()
    elif args.command == "enable-statusline":
        enable_statusline()
    elif args.command == "disable-statusline":
        disable_statusline()
    elif args.command == "enable-workflow":
        enable_workflow(args.which)
    elif args.command == "disable-workflow":
        disable_workflow(args.which)
    else:
        # No subcommand: run the everyday action (update on a git checkout, else install).
        default_action()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
