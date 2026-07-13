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
    else:
        # No subcommand: run the everyday action (update on a git checkout, else install).
        default_action()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
