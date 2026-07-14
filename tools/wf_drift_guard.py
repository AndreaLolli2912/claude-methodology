#!/usr/bin/env python3
"""wf_drift_guard.py - flag a stale repo -> test-project copy before a workflow test run.

WHY this exists (harness tooling, NOT part of the shipped bundle): the M3 walking skeleton is
proven in an isolated test project, and the bundle files are copied there per iteration. `sync.py`
only knows the repo <-> ~/.claude directions, so this THIRD direction (repo -> test project) has no
tool watching it - and the operator's habit is to propagate by tool and never hand-diff. This guard
closes that gap: it byte-compares each bundle file against its copy in the test project and reports
any that drift or are missing, so you never run a test against stale code. Modeled on `sync.py
status`: it only LOOKS and PRINTS - it never copies, edits, or fixes anything.

Usage:  python tools/wf_drift_guard.py <test-project-dir>
Exit:   0 = every guarded file is byte-identical; 1 = drift/missing (do the copy, then retry).
"""

import sys
import hashlib
from pathlib import Path

# This file lives at <repo>/tools/wf_drift_guard.py, so the repo root is its parent's parent.
REPO = Path(__file__).resolve().parents[1]

# The bundle files that must reach the test project byte-for-byte, and where each lands there
# (relative to the test-project root). Keep this in step with how Block 5 copies the bundle in.
#   repo path (under the repo)                -> test-project path (under <test-project-dir>)
MAPPING = {
    "claude/workflow/workflow.py":  "workflow.py",
    "claude/workflow/rulebook.md":  "rulebook.md",
    "claude/workflow/conductor.md": "conductor.md",
    "claude/agents/challenger.md":  ".claude/agents/challenger.md",
}


def _digest(path):
    """SHA-256 of a file's raw bytes, or None if it can't be read. Raw bytes so a CRLF/LF
    difference is caught, not hidden by text-mode translation (same reason workflow.py hashes
    bytes)."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        sys.stderr.write("usage: python tools/wf_drift_guard.py <test-project-dir>\n")
        return 2
    proj = Path(argv[0]).resolve()

    print("drift guard: repo {} -> test project {}".format(REPO, proj))
    drift = []
    for rel_repo, rel_proj in sorted(MAPPING.items()):
        src = REPO / rel_repo
        dst = proj / rel_proj
        src_h = _digest(src)
        dst_h = _digest(dst)
        if src_h is None:
            status = "SRC-MISSING (bundle file absent in repo)"
            drift.append(rel_repo)
        elif dst_h is None:
            status = "MISSING (not copied into the test project yet)"
            drift.append(rel_repo)
        elif src_h == dst_h:
            status = "ok (in sync)"
        else:
            status = "DRIFT (test-project copy differs - re-copy before testing)"
            drift.append(rel_repo)
        print("  {:34s} {}".format(rel_proj, status))

    if drift:
        print("\n{} file(s) stale or missing. Re-copy the bundle into the test project, "
              "then re-run.".format(len(drift)))
        return 1
    print("\nall guarded files are byte-identical - safe to run the test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
