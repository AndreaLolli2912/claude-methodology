#!/usr/bin/env python3
"""sync.py — deploy the working methodology into ~/.claude, or capture live edits back.

One cross-platform entry point (Windows + macOS/Linux), standard-library only, so it runs
anywhere Python 3 is present with nothing to install.

    python  sync.py               # THE everyday command: update — pull the latest, then install
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
STATUSLINE_REL = "statusline.py"                # status-line script, same relative path both sides
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

    If the file exists but isn't valid JSON, json.loads raises — the caller catches that and
    ABORTS WITHOUT WRITING, because we must never overwrite a personal settings file we could
    not safely parse.
    """
    if not SETTINGS_FILE.exists():
        return {}
    return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))


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


def _hook_refers_to_check(command: str) -> bool:
    """True if a hook command points at our check script — matched on IDENTITY, not exact string.

    Matching the script path (not the whole command) means a re-run after the interpreter path
    changed still finds and refreshes the existing entry instead of adding a duplicate. Windows
    paths are case-insensitive and mix "/" and "\\", so we normalise both sides before comparing.
    """
    needle = CHECK_SCRIPT_REL.replace("/", "").replace("\\", "").lower()
    haystack = command.replace("/", "").replace("\\", "").lower()
    return needle in haystack


def enable_hook() -> None:
    """Register the SessionStart update-check hook in ~/.claude/settings.json (idempotent).

    Backs the file up first, preserves every existing setting, and either refreshes our hook in
    place (if already present) or appends it once — so re-running is always safe.
    """
    try:
        settings = _read_settings()
    except json.JSONDecodeError as exc:
        print(f"  ! {SETTINGS_FILE} is not valid JSON ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if SETTINGS_FILE.exists():
        bak = _timestamped_backup(SETTINGS_FILE)
        print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")

    command = _hook_command()
    session_start = settings.setdefault("hooks", {}).setdefault("SessionStart", [])

    # If a group already runs our script, refresh that command in place (don't duplicate).
    for group in session_start:
        for entry in group.get("hooks", []):
            if entry.get("type") == "command" and _hook_refers_to_check(entry.get("command", "")):
                entry["command"] = command
                _write_settings(settings)
                print("  refreshed the existing SessionStart update-check hook.")
                return

    # Not present yet — append one matcher group. "startup" fires only on fresh sessions (not
    # resume/compact), and a short timeout keeps a slow network from delaying session start.
    session_start.append({
        "matcher": "startup",
        "hooks": [{"type": "command", "command": command, "timeout": 10}],
    })
    _write_settings(settings)
    print("  enabled the SessionStart update-check hook.")
    print("  new Claude Code sessions will now flag when a newer methodology is published.")


def disable_hook() -> None:
    """Remove the SessionStart update-check hook from ~/.claude/settings.json (idempotent)."""
    try:
        settings = _read_settings()
    except json.JSONDecodeError as exc:
        print(f"  ! {SETTINGS_FILE} is not valid JSON ({exc}); refusing to touch it.", file=sys.stderr)
        return
    session_start = settings.get("hooks", {}).get("SessionStart", [])
    present = any(
        _hook_refers_to_check(entry.get("command", ""))
        for group in session_start
        for entry in group.get("hooks", [])
    )
    if not present:
        print("  no update-check hook was present; nothing to do.")
        return

    bak = _timestamped_backup(SETTINGS_FILE)
    print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    kept_groups = []
    for group in session_start:
        entries = [e for e in group.get("hooks", []) if not _hook_refers_to_check(e.get("command", ""))]
        if entries:                             # keep groups that still have other hooks
            group["hooks"] = entries
            kept_groups.append(group)
    # Prune emptied structures so we don't leave a dangling "SessionStart": [] / "hooks": {}.
    if kept_groups:
        settings["hooks"]["SessionStart"] = kept_groups
    else:
        settings["hooks"].pop("SessionStart", None)
        if not settings["hooks"]:
            settings.pop("hooks", None)
    _write_settings(settings)
    print("  removed the SessionStart update-check hook.")


def enable_statusline() -> None:
    """Point Claude Code's status line at the bundled statusline.py (idempotent).

    Writes a single top-level "statusLine" object into ~/.claude/settings.json that runs the
    deployed statusline.py through THIS interpreter (see `_python_command`). Backs the settings
    file up first and preserves every other key. Re-running just overwrites that one object —
    the "refresh in place" we want when, say, the interpreter path changes — so it's always safe.
    """
    try:
        settings = _read_settings()
    except json.JSONDecodeError as exc:
        print(f"  ! {SETTINGS_FILE} is not valid JSON ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if SETTINGS_FILE.exists():                      # never rewrite the personal file without a backup
        bak = _timestamped_backup(SETTINGS_FILE)
        print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    # One assignment overwrites any previous statusLine, which is exactly the idempotent behaviour
    # we want; every other setting in the dict is left untouched.
    settings["statusLine"] = {"type": "command", "command": _python_command(STATUSLINE_REL)}
    _write_settings(settings)
    print("  enabled the status line (model | effort | context | quota).")
    print("  restart Claude Code to see it under the prompt.")


def disable_statusline() -> None:
    """Remove the status line from ~/.claude/settings.json (idempotent)."""
    try:
        settings = _read_settings()
    except json.JSONDecodeError as exc:
        print(f"  ! {SETTINGS_FILE} is not valid JSON ({exc}); refusing to touch it.", file=sys.stderr)
        return
    if "statusLine" not in settings:                # nothing configured — say so and stop
        print("  no status line was configured; nothing to do.")
        return
    bak = _timestamped_backup(SETTINGS_FILE)
    print(f"  backed up {SETTINGS_FILE.name} -> {bak.name}")
    settings.pop("statusLine", None)                # drop only our key; leave the rest as-is
    _write_settings(settings)
    print("  removed the status line.")


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
    sub.add_parser("enable-hook", help="notify at Claude Code startup when an update exists")
    sub.add_parser("disable-hook", help="remove the update-check hook")
    sub.add_parser("enable-statusline", help="show model|effort|context|quota in the status line")
    sub.add_parser("disable-statusline", help="remove the status line")

    args = parser.parse_args(argv)
    if args.command == "install":
        install()
    elif args.command == "update":
        update()
    elif args.command == "capture":
        capture()
    elif args.command == "check":
        check()
    elif args.command == "enable-hook":
        enable_hook()
    elif args.command == "disable-hook":
        disable_hook()
    elif args.command == "enable-statusline":
        enable_statusline()
    elif args.command == "disable-statusline":
        disable_statusline()
    else:
        # No subcommand: run the everyday action (update on a git checkout, else install).
        default_action()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
