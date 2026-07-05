#!/usr/bin/env python3
"""sync.py — deploy the working methodology into ~/.claude, or capture live edits back.

One cross-platform entry point (Windows + macOS/Linux), standard-library only, so it runs
anywhere Python 3 is present with nothing to install.

    python  sync.py install    # repo      -> ~/.claude   (backs up anything it replaces)
    python3 sync.py capture    # ~/.claude -> repo        (stage live edits for commit)

The repo is the source of truth. `install` writes the live side; `capture` writes the repo
side. There is no merge — each direction overwrites — but `install` keeps a timestamped
backup of whatever it replaced, so nothing is ever clobbered silently.
"""

# `from __future__` keeps the type hints below (e.g. `list[str] | None`) valid on the older
# Python 3.8/3.9 that a Linux box might ship — annotations become strings, never evaluated.
from __future__ import annotations

import argparse
import shutil
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
]

# Anchor every path off this script's own folder so the repo can be moved or renamed without
# breaking anything (the cross-platform equivalent of PowerShell's $PSScriptRoot).
REPO_ROOT = Path(__file__).resolve().parent   # the repo root (folder holding this script)
BUNDLE_DIR = REPO_ROOT / "claude"             # the repo's mirror of ~/.claude
# Path.home() resolves %USERPROFILE% on Windows and $HOME on macOS/Linux — this one line is
# what makes the whole script cross-platform.
TARGET_DIR = Path.home() / ".claude"          # this machine's live ~/.claude


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
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = dst.with_name(f"{dst.name}.{stamp}.bak")
        shutil.copy2(dst, bak)
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


def capture() -> None:
    """~/.claude -> repo: pull live edits back so they can be committed.

    No backup on this side: the repo is git-tracked, so `git` history (and `git diff` before
    you commit) is the safety net.
    """
    for rel in MANIFEST:
        if _copy(TARGET_DIR / rel, BUNDLE_DIR / rel, backup=False):
            print(f"  captured {rel}")
    print("\nDone. Now:  git add -A;  git commit -m 'update methodology';  git push")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy the working methodology to ~/.claude, or capture live edits back.",
    )
    # dest="command" lets us tell "no subcommand" apart from a real one below.
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("install", help="repo -> ~/.claude (backs up anything it replaces)")
    sub.add_parser("capture", help="~/.claude -> repo (stage live edits for commit)")

    args = parser.parse_args(argv)
    if args.command == "install":
        install()
    elif args.command == "capture":
        capture()
    else:
        # No/unknown subcommand: show usage and exit non-zero so a caller can detect misuse.
        parser.print_help(sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
