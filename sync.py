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
from fnmatch import fnmatchcase
from pathlib import Path

# --- The bundle definition ----------------------------------------------------------------
# The bundle is a NAMED WHITELIST whose *contents* are walked from disk — not a per-file list.
# Three small, rarely-changing constants say what this repo owns inside ~/.claude; the walker
# (`_bundle_files` below) turns them into the concrete file set by reading the filesystem. The
# payoff over the old per-file MANIFEST: a file dropped into a named directory ships automatically,
# with no code edit here (this closes RISKS #8 — a per-file list can't express "everything in this
# directory"). It stays a whitelist end to end: nothing un-named ever ships.
BUNDLE_DIRS = ["skills", "agents", "hooks", "workflow"]      # directories shipped WHOLESALE (walked, minus IGNORE)
BUNDLE_ROOT_FILES = [                                         # the loose files that live in NO directory
    "CLAUDE.md",         # the always-on core, loaded by Claude Code in every project
    "METHODOLOGY.md",    # the full rule reference, read on demand
    "VERSION",           # machine-readable current version (single source of truth)
    "CHANGELOG.md",      # parseable release history; source of the update-notice delta
    "statusline.py",     # the plain status-line renderer: model|effort|context|quota
    "statusline_wf.py",  # the M5 workflow-aware status line (base line + wf:<step>:<state>)
]
# Junk that must NEVER ship, even when it sits inside a named dir ("ignore beats ship"). Matched
# case-INSENSITIVELY (see `_is_ignored`) so junk is dropped identically on Windows and macOS/Linux.
# (Named-entry matching, by contrast, is exact / case-sensitive by design: a wrong-case name is caught
# as a stray and HALTS install rather than silently mis-shipping — fail-loud-safe.)
# (settings.json is deliberately NOT owned here — it is a personal per-machine file the enable-*
# verbs edit in place; install/capture never carry it, so activation stays per-box - D-1.)
IGNORE = ["__pycache__", "*.pyc", "*.pyo", "*.bak", ".ds_store", "*.swp", "thumbs.db"]

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


def _is_ignored(rel: Path) -> bool:
    """True if any component of a relative path is junk (an IGNORE glob). Case-normalised — we
    lowercase each part and match with `fnmatchcase` — so a file's ignore-status is IDENTICAL on
    Windows and macOS/Linux. (Bare `fnmatch` case-folds according to the host OS, which would make
    the ship set platform-dependent — a file ignored on one machine but shipped on another.)"""
    return any(fnmatchcase(part.lower(), pat) for part in rel.parts for pat in IGNORE)


def _owns_root_entry(entry: Path) -> bool:
    """The ONE test for "does the bundle own this top-level entry under a bundle root" — true for a
    named directory, a named root file, or ignorable junk. Both `_bundle_files` (which ships what it
    owns) and `_definition_problems` (whose strays are exactly what it does NOT own) consult this, so
    "what the bundle owns" is decided in a single place: the walker and the gate can never drift into
    shipping and flagging different sets (the M1 directive — one shared predicate, not two encodings)."""
    name = entry.name
    return (_is_ignored(Path(name))                          # junk (e.g. __pycache__, *.bak) — owned but skipped
            or (entry.is_dir() and name in BUNDLE_DIRS)      # a named bundle directory
            or (entry.is_file() and name in BUNDLE_ROOT_FILES))  # a named loose root file


def _bundle_files(base: Path) -> tuple[list[Path], int]:
    """Walk a bundle root (`claude/` or a live `~/.claude`) and return (ship, skipped): the shippable
    files as paths RELATIVE to `base`, and a count of junk files skipped along the way.

    "Shippable" = a named root file that exists, plus every file inside a named directory — minus
    IGNORE junk. One classified pass over the top level uses `_owns_root_entry` (the SAME test the
    coverage gate uses), so the walker and the gate agree by construction (M1). A stray top-level
    entry is simply not shipped here; complaining about it is the gate's job, not the walker's.

    Order is deterministic per machine (top level sorted, then each dir's contents sorted) so install
    and capture print the same sequence every run. Cross-OS ordering may differ, but counts and
    membership do not, so nothing downstream depends on the exact order.

    A base that does not exist yet — a fresh machine whose `~/.claude` was never created — walks to
    nothing rather than crashing on `iterdir()`, so the read verbs (status/capture, via `_live_orphans`)
    degrade gracefully instead of raising a traceback."""
    if not base.is_dir():
        return [], 0
    ship: list[Path] = []
    skipped = 0
    for entry in sorted(base.iterdir()):                     # one classified pass over the top level
        if not _owns_root_entry(entry):
            continue                                         # a stray — not ours to ship (the gate reports it)
        if _is_ignored(Path(entry.name)):
            continue                                         # owned-but-junk at the top level (e.g. __pycache__/)
        if entry.is_file():                                  # a named root file -> ship it as-is
            ship.append(Path(entry.name))
            continue
        for path in sorted(entry.rglob("*")):                # a named dir -> ship its whole interior...
            if not path.is_file():
                continue
            rel = path.relative_to(base)
            if _is_ignored(rel):                             # ...minus junk anywhere inside it (ignore beats ship)
                skipped += 1
            else:
                ship.append(rel)
    return ship, skipped


def _definition_problems(base: Path) -> tuple[list[str], list[str]]:
    """Compare the whitelist against what is actually on disk under `base` and return (strays,
    missing) — the two DISTINCT kinds of disagreement, returned SEPARATELY because install answers
    them differently (a stray HALTS the whole deploy; a missing named entry only REPORTS and ships
    the rest). Collapsing them into one flat "halt if non-empty" list would silently re-introduce
    halt-on-missing — the exact regression this gate exists to prevent — so the two must stay
    tellable-apart at every call site.

      strays  = top-level entries that are neither a named dir, a named root file, nor junk
                (over-inclusion: "what ships" is ambiguous until you classify it).
      missing = named entries (a BUNDLE_DIRS or BUNDLE_ROOT_FILES name) absent from disk
                (under-inclusion: unambiguous, but the bundle can't ship what isn't there).
    Both directions read the same three constants the walker does, so the constants are the single
    source of truth and this gate can never disagree with `_bundle_files` about the classification."""
    strays: list[str] = []
    missing: list[str] = []
    # Under-inclusion: a named thing that isn't on disk.
    for name in BUNDLE_ROOT_FILES:
        if not (base / name).is_file():
            missing.append(f"named root file '{name}' is missing — restore it, or drop it from BUNDLE_ROOT_FILES")
    for d in BUNDLE_DIRS:
        if not (base / d).is_dir():
            missing.append(f"named dir '{d}/' is missing — restore it, or drop it from BUNDLE_DIRS")
    # Over-inclusion: a top-level entry the bundle doesn't own. Coverage gaps are top-level ONLY —
    # everything deeper is inside a named dir, so it either ships or is IGNORE-junk. (A non-existent
    # base has no strays — its named entries are already reported 'missing' above — so guard iterdir.)
    if base.is_dir():
        for entry in sorted(base.iterdir()):
            if not _owns_root_entry(entry):
                strays.append(f"'{entry.name}' is neither a named bundle dir/root file nor IGNORE junk — "
                              "name it (BUNDLE_DIRS/BUNDLE_ROOT_FILES), move it into a named dir, or add it to IGNORE")
    return strays, missing


def _copy(src: Path, dst: Path, *, backup: bool) -> str:
    """Copy one file src -> dst (creating parent folders) and report what happened: "new" (dst didn't
    exist), "replaced" (dst existed and was overwritten), or "missing" (src was gone — nothing copied).

    It used to return a bool; the three-way status lets callers print honest counts and, crucially,
    never count or announce a file they did not actually write. `missing` is the TOCTOU guard: the
    gate + walk make a missing SOURCE practically unreachable, but a walked file can still vanish
    between the walk and this copy — callers treat that as an anomaly (warn + exit non-zero), never
    as success. If `backup` is set and dst already exists, dst is first copied to `dst.<timestamp>.bak`
    so a replaced live file is always recoverable."""
    if not src.exists():
        print(f"  ! missing, skipped: {src}", file=sys.stderr)
        return "missing"
    existed = dst.exists()                          # snapshot BEFORE we touch anything, so we can report new vs replaced
    dst.parent.mkdir(parents=True, exist_ok=True)   # ensure the destination folder exists
    if backup and existed:                          # never clobber silently: back up first
        bak = _timestamped_backup(dst)
        print(f"  backed up {dst.name} -> {bak.name}")
    shutil.copy2(src, dst)                           # copy2 preserves mtime + permission bits
    return "replaced" if existed else "new"


def install() -> int:
    """repo -> ~/.claude: deploy the bundle, backing up replaced files. Returns an exit code — 0 on a
    clean deploy, non-zero if a named entry was missing or a walked file vanished mid-copy.

    The coverage gate runs FIRST and answers the two disagreements differently. A stray top-level
    entry HALTS the whole install (deploy nothing — "what ships" is ambiguous, and halting is fully
    reversible), while a missing named entry only REPORTS and exits non-zero (the covered files still
    ship — a named thing is simply absent, no ambiguity). This asymmetry is the point: fail-closed on
    ambiguity, fail-loud-but-forward on a plain absence."""
    print(f"  repo {BUNDLE_DIR}  ->  {TARGET_DIR}")     # resolved roots FIRST — the cwd-audit habit, even on the halt path
    strays, missing = _definition_problems(BUNDLE_DIR)
    if strays:                                          # OVER-inclusion -> fail-closed: deploy NOTHING
        for s in strays:
            print(f"  ! {s}", file=sys.stderr)
        print("  ! a stray top-level entry makes 'what ships' ambiguous — deployed nothing.", file=sys.stderr)
        return 1
    for m in missing:                                   # UNDER-inclusion -> report each, but keep going
        print(f"  ! {m}", file=sys.stderr)
    ship, skipped = _bundle_files(BUNDLE_DIR)
    new = replaced = vanished = 0
    for rel in ship:
        outcome = _copy(BUNDLE_DIR / rel, TARGET_DIR / rel, backup=True)
        if outcome == "missing":                        # a walked file vanished before the copy (TOCTOU) — LOUD, never "installed"
            vanished += 1
            print(f"  ! vanished before copy, not shipped: {rel}", file=sys.stderr)
        else:
            new += outcome == "new"
            replaced += outcome == "replaced"
            print(f"  installed {rel}")
    reported = len(missing)                             # M4: the footer carries the missing-named count, so it agrees with the exit code
    print(f"\nShipped {new + replaced} file(s), {replaced} replaced; {skipped} junk skipped; "
          f"{reported} named entr{'y' if reported == 1 else 'ies'} missing; {vanished} vanished.")
    print("Restart Claude Code, then check /skills lists 'init-project-docs'.")
    print("Tip: run  python sync.py enable-hook  for in-session update notifications.")
    print("Tip: run  python sync.py enable-statusline  to show model|effort|context|quota in the status line.")
    print("Tip: run  python sync.py enable-workflow  to turn on the six-step workflow (nudge + wf status line).")
    return 1 if (missing or vanished) else 0            # loud on any anomaly; a clean deploy is 0


def capture() -> int:
    """~/.claude -> repo: pull live edits back so they can be committed. Returns an exit code — 0 on a
    clean capture (orphans do NOT flip it — a lingering live file is news, not an error), non-zero
    only if a file vanished mid-copy.

    No backup on this side: the repo is git-tracked, so `git diff`/history is the safety net. Only the
    REPO's ship set is pulled — a file that exists live but the repo doesn't own is reported as an
    orphan and NEVER pulled, so a repo-side deletion can't resurrect itself into the source of truth
    (F2)."""
    print(f"  live {TARGET_DIR}  ->  repo {BUNDLE_DIR}")   # resolved roots FIRST (cwd-audit habit)
    ship, _ = _bundle_files(BUNDLE_DIR)                    # the REPO bundle = the authoritative owned set
    captured = vanished = 0
    for rel in ship:
        if not (TARGET_DIR / rel).exists():
            print(f"  not on this machine, skipped: {rel}")   # info, not an error (no '!')
            continue
        outcome = _copy(TARGET_DIR / rel, BUNDLE_DIR / rel, backup=False)
        if outcome == "missing":                          # vanished between the check above and the copy (TOCTOU) — honor it (M3)
            vanished += 1
            print(f"  ! vanished before capture, not pulled: {rel}", file=sys.stderr)
        else:
            captured += 1
            print(f"  captured {rel}")
    orphans = _live_orphans(ship)
    for rel in orphans:
        print(f"  live orphan (present live, not in the bundle — not captured): {rel}")   # info, exit stays 0
    print(f"\nCaptured {captured} file(s); {vanished} vanished; {len(orphans)} live orphan(s) reported.")
    print("Now:  git add -A;  git commit -m 'update methodology';  git push")
    return 1 if vanished else 0                            # orphans are informational — only a vanished file is an anomaly


def _live_orphans(repo_ship: list[Path]) -> list[Path]:
    """Files that exist under the LIVE named dirs but the repo bundle does not own — lingering or
    foreign leftovers. Reported by capture/status, NEVER pulled (that would let a repo-side deletion
    resurrect itself — F2). Reuses `_bundle_files(TARGET_DIR)` rather than re-walking, so the walk
    mechanic lives in exactly one place (M1).

    Named ROOT files are deliberately excluded (`len(rel.parts) > 1` keeps only files inside a dir):
    the `~/.claude` root is a shared namespace (settings.json, projects/, other tools), so an unowned
    live root file can't be told from a foreign one — an accepted blind spot (a lingering root file;
    a wholly-retired directory is the other). Both are low-harm on an additive target."""
    owned = set(repo_ship)
    live_ship, _ = _bundle_files(TARGET_DIR)              # reuse the one walker on the live side (M1)
    return [rel for rel in live_ship
            if len(rel.parts) > 1                          # skip top-level root files (shared-namespace blind spot)
            and rel not in owned]                          # keep only what the repo bundle doesn't own


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
    """Compare each repo bundle file against its live ~/.claude copy, byte for byte. Returns a list of
    (relative_path, state) for every file NOT in sync — 'missing' (never installed here) or 'differs'
    (the live copy isn't the repo's current bytes). Empty = live is fully up to date. Read-only.

    The file list comes from the same `_bundle_files(BUNDLE_DIR)` walk install/capture use, so status
    can never check a different set than they deploy — and a file dropped into a named dir shows up
    here the moment it exists, with no list to update."""
    out_of_sync = []
    ship, _ = _bundle_files(BUNDLE_DIR)
    for rel in ship:
        live_file = TARGET_DIR / rel
        if not live_file.exists():
            out_of_sync.append((rel, "missing"))
        elif (BUNDLE_DIR / rel).read_bytes() != live_file.read_bytes():
            out_of_sync.append((rel, "differs"))
    return out_of_sync


def status() -> int:
    """Print where this machine stands across GitHub <-> repo <-> live ~/.claude, and return an
    exit code: 0 when everything is confirmed in sync, 1 when there's something to do (or we
    couldn't fully confirm, e.g. offline). Read-only — it changes nothing.
    """
    git = _git_status()
    live = _live_status()
    ship, _ = _bundle_files(BUNDLE_DIR)
    strays, missing_entries = _definition_problems(BUNDLE_DIR)   # the two coverage disagreements, kept apart (M2)
    orphans = _live_orphans(ship)

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

    # --- bundle definition: two DISTINCT advisories (M2) -------------------------------------
    # A stray and a missing named entry get DIFFERENT install responses, so status previews them
    # distinctly — never a blurred "halt / report". Both are actionable, so both flip the exit code.
    if strays:
        synced = False
        n = len(strays)
        lines.append(f"  Bundle   {n} stray top-level entr{'y' if n == 1 else 'ies'} under claude/ "
                     "- install will HALT and deploy nothing.")
        todo.append("classify the stray(s): name it (BUNDLE_DIRS/BUNDLE_ROOT_FILES), move it into a "
                    "named dir, or add it to IGNORE")
    if missing_entries:
        synced = False
        n = len(missing_entries)
        lines.append(f"  Bundle   {n} named entr{'y' if n == 1 else 'ies'} missing from claude/ "
                     "- install will REPORT and exit non-zero (ships the rest).")
        todo.append("restore the missing named entr(y/ies), or drop the name from BUNDLE_DIRS/BUNDLE_ROOT_FILES")

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
    # Live orphans are INFORMATIONAL — printed as a sub-line, but they do NOT flip `synced` (they
    # never flip capture's exit code either, so status stays consistent with it).
    if orphans:
        n = len(orphans)
        lines.append(f"           (plus {n} file(s) present live but not in the bundle - informational.)")

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


def update() -> int:
    """One-command update: `git pull` the repo, then `install` the refreshed files into ~/.claude.
    Returns an exit code — install's on a successful pull+deploy, or 1 if we couldn't pull (so the
    everyday `python sync.py` is loud when it deploys nothing).

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
        return 1

    print("Pulling the latest methodology from the remote...")
    try:
        pull = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:                       # git isn't installed / not on PATH
        print("  ! git was not found on PATH.", file=sys.stderr)
        print("    Install git (or pull manually), then run:  python sync.py install")
        return 1

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
        return 1

    # Pull succeeded (fast-forwarded or already current) -> deploy the now-current files, and carry
    # install's exit code up (a missing named entry or a vanished file makes even `update` loud).
    print()
    return install()


def default_action() -> int:
    """What `python sync.py` with NO subcommand does: bring this machine up to date, returning the
    underlying exit code so the everyday command is loud on an anomaly.

    On a git checkout it runs `update` (pull the latest, then install); on a plain folder copy (no
    `.git`, so nothing to pull) it just `install`s what's here. Everything else — capture, check,
    enable-hook, disable-hook — is a named subcommand.
    """
    print("No command given — bringing ~/.claude up to date (run  python sync.py -h  for the rest).\n")
    if (REPO_ROOT / ".git").exists():
        return update()   # git checkout: pull the latest, then install
    return install()      # plain copy: nothing to pull, just deploy what's here


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
    # install / update / capture / status / no-arg each return an exit code; propagate it so a real
    # anomaly (a stray, a missing named entry, a vanished file, drift) reaches the shell as non-zero.
    if args.command == "install":
        return install()
    elif args.command == "update":
        return update()
    elif args.command == "capture":
        return capture()
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
        return default_action()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
