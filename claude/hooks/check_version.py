#!/usr/bin/env python3
"""check_version.py — notify when a newer working-methodology version exists.

`sync.py install` DEPLOYS this file to ~/.claude/hooks/check_version.py. It runs two ways:

  * As a Claude Code **SessionStart hook** (the `__main__` path): quiet, throttled, fail-safe.
    If a newer version is published on GitHub it writes a short notice to STDERR and exits 2 —
    which Claude Code shows to you and then continues the session. Otherwise it stays silent
    and exits 0. It must NEVER block or break a session: any error → silent exit 0.

  * Via `python sync.py check` (which calls `run_check(verbose=True, ...)`): a full, on-demand
    report — installed vs latest, and the changelog of exactly what you'd gain by updating.

Standard library only, so it runs wherever Python 3 does with nothing to install. It compares
a local version file (~/.claude/VERSION) against the same file in the GitHub repo, and reads
the repo's CHANGELOG.md to show *what changed*, so a person can decide whether to update.
"""

# `from __future__` keeps the annotations valid on the older Python a Linux box might ship —
# they become strings and are never evaluated (same reason sync.py uses it).
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

# --- Configuration (methodology D5: change here, no code surgery) -------------------------
# Where to fetch the canonical version + changelog from. `METHODOLOGY_RAW_BASE` overrides it —
# tests point that at a fake "newer" remote; the default is this repo's raw `main` branch.
RAW_BASE = os.environ.get(
    "METHODOLOGY_RAW_BASE",
    "https://raw.githubusercontent.com/AndreaLolli2912/claude-methodology/main",
).rstrip("/")
# The two files, relative to RAW_BASE — the same paths the bundle deploys from `claude/`.
REMOTE_VERSION_URL = f"{RAW_BASE}/claude/VERSION"
REMOTE_CHANGELOG_URL = f"{RAW_BASE}/claude/CHANGELOG.md"

# Never hit the network more than once per this window; between checks we answer from the cache
# so a session start stays instant. A day is plenty for something that changes rarely.
THROTTLE_SECONDS = 24 * 60 * 60
# Hard cap on any single network read, so a slow or hanging GitHub can't delay a session start.
NET_TIMEOUT = 2.5

# The live bundle on this machine. Path.home() = %USERPROFILE% (Windows) or $HOME (mac/Linux).
CLAUDE_DIR = Path.home() / ".claude"
LOCAL_VERSION_FILE = CLAUDE_DIR / "VERSION"                 # the installed version to compare
CACHE_FILE = CLAUDE_DIR / ".methodology-update-check.json"  # throttle + last-known-remote cache


def _emit(text: str, *, err: bool = False) -> None:
    """Print a line, tolerating a console whose encoding can't represent every character.

    The changelog/notice contain characters like "—" and "≥". On a Windows console using a
    legacy code page (cp1252), a plain print() of those raises UnicodeEncodeError — which,
    inside the fail-safe hook, would silently swallow the whole notice. So we fall back to
    writing bytes in the stream's OWN encoding with errors="replace" (e.g. "≥" → "?"), which
    degrades gracefully instead of crashing, and never forces mojibake by re-encoding as UTF-8.
    """
    stream = sys.stderr if err else sys.stdout
    line = text + "\n"
    try:
        stream.write(line)
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "utf-8"
        try:
            stream.flush()                                   # keep byte + text writes in order
            stream.buffer.write(line.encode(enc, errors="replace"))
            stream.buffer.flush()
        except Exception:
            pass
    try:
        stream.flush()
    except Exception:
        pass


def _parse_version(text: str | None):
    """Turn a version string like 'v0.3.0' or '0.3' into a comparable tuple, e.g. (0, 3, 0).

    Returns None if it can't be parsed, so callers bail out safely instead of crashing on a
    malformed file. A leading 'v' is tolerated and short forms are zero-padded, so '0.3' and
    '0.3.0' compare equal. Comparing tuples of ints means 0.10.0 > 0.9.0 (not string order).
    """
    if not text:
        return None
    cleaned = text.strip().lstrip("vV").strip()
    try:
        nums = [int(p) for p in cleaned.split(".")]
    except ValueError:
        return None
    while len(nums) < 3:          # pad "0.3" -> (0, 3, 0) so lengths always match
        nums.append(0)
    return tuple(nums)


def _fetch(url: str) -> str:
    """GET a small text file over HTTPS and return its decoded body.

    Raises on any failure (offline, timeout, HTTP error, TLS). Callers wrap this so a failure
    just means "couldn't check", never a crash. A User-Agent is set because some endpoints
    reject blank ones.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "methodology-update-check"})
    with urllib.request.urlopen(req, timeout=NET_TIMEOUT) as resp:  # timeout bounds the wait
        return resp.read().decode("utf-8")


def _read_local_version() -> str | None:
    """The version installed in ~/.claude, or None if the file isn't there (older/partial install)."""
    try:
        return LOCAL_VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _load_cache() -> dict:
    """The cached check result, or {} if missing/unreadable."""
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(data: dict) -> None:
    """Persist the check result. Best-effort — a write failure must not break anything."""
    try:
        CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def _changelog_delta(changelog_text: str, installed: str, remote: str) -> list[str]:
    """Return the changelog lines you'd GAIN by updating: entries with installed < version <= remote.

    The changelog's contract (see claude/CHANGELOG.md) is one entry per release, each opening
    with a heading `## <semver> — <date>` followed by `- ` bullet lines. We scan for those
    headings, keep the ones newer than what's installed (up to and including the remote), and
    return their heading + body lines. Anything malformed is skipped, not fatal — worst case the
    caller still reports the bare version bump.
    """
    installed_t = _parse_version(installed) or (0, 0, 0)
    remote_t = _parse_version(remote)
    heading_re = re.compile(r"^##\s+(\d+\.\d+\.\d+)\b")   # binds to the heading grammar (P5)
    out: list[str] = []
    including = False
    for line in changelog_text.splitlines():
        match = heading_re.match(line)
        if match:
            ver_t = _parse_version(match.group(1))
            # Keep this entry only if it's newer than installed and no newer than the remote.
            including = bool(
                ver_t and ver_t > installed_t and (remote_t is None or ver_t <= remote_t)
            )
            if including:
                out.append(line.strip())
        elif including:
            out.append(line.rstrip())          # body line of an entry we're keeping
    while out and not out[-1].strip():          # trim trailing blanks for a tidy notice
        out.pop()
    return out


def run_check(*, verbose: bool, use_throttle: bool) -> int:
    """Compare installed vs latest and report. Returns 2 if an update is available, else 0.

    verbose=True  → talkative stdout report for `python sync.py check` (run on demand).
    verbose=False → hook mode: silent unless an update exists, in which case a short notice goes
                    to STDERR and we return 2 (Claude Code shows a SessionStart hook's stderr to
                    the user and continues). Any error is swallowed → return 0, so a hook can
                    never break a session.
    use_throttle=True → answer from the daily cache when it's fresh, avoiding a network call on
                        every session start.
    """
    # Kill switch: METHODOLOGY_UPDATE_CHECK=0 disables the check entirely (privacy / offline).
    if os.environ.get("METHODOLOGY_UPDATE_CHECK") == "0":
        if verbose:
            _emit("Update check is disabled (METHODOLOGY_UPDATE_CHECK=0).")
        return 0
    try:
        return _run_check_inner(verbose=verbose, use_throttle=use_throttle)
    except Exception as exc:      # fail-safe: a hook must never surface an error or block
        if verbose:
            _emit(f"Could not check for updates: {exc}")
        return 0


def _run_check_inner(*, verbose: bool, use_throttle: bool) -> int:
    """The actual check. Kept separate so run_check() can wrap it in one try/except."""
    installed = _read_local_version()
    if installed is None:
        if verbose:
            _emit(f"No {LOCAL_VERSION_FILE} found — can't determine the installed version.")
        return 0

    now = time.time()
    cache = _load_cache()
    # Fast path: inside the throttle window, decide from cache without touching the network.
    fresh = use_throttle and (now - cache.get("last_check_epoch", 0) < THROTTLE_SECONDS)
    if fresh and cache.get("remote_version"):
        remote = cache["remote_version"]
        delta = cache.get("delta_lines", [])
    else:
        # Slow path: fetch the canonical version; only pull the (larger) changelog if we're behind.
        remote = _fetch(REMOTE_VERSION_URL).strip()
        if (_parse_version(remote) or (0, 0, 0)) > (_parse_version(installed) or (0, 0, 0)):
            try:
                delta = _changelog_delta(_fetch(REMOTE_CHANGELOG_URL), installed, remote)
            except Exception:
                delta = []      # a version bump is still worth reporting without the changelog
        else:
            delta = []
        _save_cache({"last_check_epoch": now, "remote_version": remote, "delta_lines": delta})

    update_available = (_parse_version(remote) or (0, 0, 0)) > (_parse_version(installed) or (0, 0, 0))

    if verbose:
        _emit(f"Installed methodology version: {installed}")
        _emit(f"Latest published version:      {remote}")
        if update_available:
            _emit("\nAn update is available. What you'd gain:\n")
            _emit("\n".join(delta) if delta else "  (see CHANGELOG.md on GitHub)")
            _emit("\nTo update: pull the claude-methodology repo, then  python sync.py install")
        else:
            _emit("\nYou're up to date.")
        return 2 if update_available else 0

    # Hook mode: silent unless there's genuinely something to say.
    if update_available:
        _emit(_format_hook_notice(installed, remote, delta), err=True)  # stderr+exit2 → user sees it
        return 2
    return 0


def _format_hook_notice(installed: str, remote: str, delta: list[str]) -> str:
    """A short, human-readable notice for the SessionStart hook (kept deliberately brief)."""
    lines = [f"[methodology] Update available: {installed} -> {remote}."]
    # Show only the bullet first-lines (skip '## x.y.z' headings and wrapped continuations) and
    # cap the count so a long changelog can't flood the session-start notice.
    bullets = [ln for ln in delta if ln.lstrip().startswith("- ")]
    lines.extend(bullets[:6])
    if len(bullets) > 6:
        lines.append("  … see CHANGELOG.md for the rest")
    lines.append("Update:  pull the claude-methodology repo, then  python sync.py install  (restart Claude Code)")
    return "\n".join(lines)


if __name__ == "__main__":
    # Hook mode: quiet, throttled, fail-safe. Exit 2 (with a stderr notice) only when an update
    # is available; exit 0 otherwise so a normal session start is completely untouched.
    raise SystemExit(run_check(verbose=False, use_throttle=True))
