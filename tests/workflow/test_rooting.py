#!/usr/bin/env python3
"""Block-1 proof (M5 rooting refactor): the seams the D-2 / D-2a / D-3 / D-10 split INTRODUCED,
none of which the pre-M5 suite exercised. Every check here is a NEW guarantee that only exists
because BUNDLE and PROJECT came apart and PROJECT paths became functions of a resolved `root`:

  * walk-up (D-2a): a verb run from a SUBDIRECTORY finds the open task ABOVE it; a verb with NO
    task at or above resolves to None and fails CLEANLY (a plain message, never a traceback -
    which the platform mangles under a hook, D-9(iii)) and never silently grabs the wrong project.
  * `start` (D-2a): roots at the nearest .git repo, REFUSES outside one, and REFUSES a nested
    duplicate when a marker already sits above.
  * the resolved root prints to STDERR (human ruling, 2026-07-16), so STDOUT stays exactly what
    callers and the other 124 checks parse.
  * D-10: `start` authors a self-ignoring .workflow/.gitignore, proven with REAL git - a
    `git add -A` stages NOTHING from .workflow/: the marker, the drafts, a hand-authored file,
    and .gitignore itself all stay ignored (`*` is total; M7 retired the lone re-include).

Standalone script (like every suite here): it sys.exit()s at the end, so run it DIRECTLY -
`python tests/workflow/test_rooting.py` - never under pytest.
"""
import subprocess
import sys
import os
import shutil
import tempfile
from pathlib import Path

# Deploy the bundle the way it ships (copy workflow.py into a temp dir), so we test the COPIED
# shape, not the repo source - identical to the other suites.
SRC = Path(__file__).resolve().parents[2] / "claude" / "workflow"
TMP = Path(tempfile.mkdtemp(prefix="wf_root_"))
shutil.copy(SRC / "workflow.py", TMP / "workflow.py")
shutil.copy(SRC / "rulebook.md", TMP / "rulebook.md")

sys.path.insert(0, str(TMP))
import workflow  # noqa: E402  (import the copy, to read its marker_path spelling below)

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def run(*args, cwd):
    """Run the CLI as a subprocess with an EXPLICIT cwd. This suite tests the WALK-UP, so cwd is
    the variable under test - it is always passed, never defaulted (and never omitted, which for a
    walk-up-rooted verb would be the D-3 catastrophe the other suites guard with cwd=TMP)."""
    p = subprocess.run([sys.executable, str(TMP / "workflow.py"), *args],
                       capture_output=True, text=True, cwd=str(cwd))
    return p.returncode, p.stdout, p.stderr


# ---------------------------------------------------------------------------
# R1. `start` OUTSIDE any git repo fails cleanly. `bare/` has no .git, and TMP (a mkdtemp
# under the system temp dir) is not itself inside any repo, so the git walk-up finds nothing.
# ---------------------------------------------------------------------------
BARE = TMP / "bare"
BARE.mkdir()
rc, out, err = run("start", "no repo here", cwd=BARE)
check("R1 start refuses outside a git repo (no .git above)",
      rc == 1 and "git repositor" in err.lower())

# ---------------------------------------------------------------------------
# R2. `start` INSIDE a git repo roots at the repo, creates the marker there, authors the
# self-ignoring .gitignore, and prints the resolved root to STDERR (not STDOUT).
# ---------------------------------------------------------------------------
REPO = TMP / "repo"
REPO.mkdir()
(REPO / ".git").mkdir()   # a bare .git dir is enough for _walk_up_for_git (it tests .exists())
rc, out, err = run("start", "rooting task", cwd=REPO)
check("R2 start succeeds inside a git repo", rc == 0)
check("R2 marker created at the repo root", (REPO / ".workflow" / "marker.json").exists())
check("R2 start authored .workflow/.gitignore verbatim (* only, no !.gitignore)",
      (REPO / ".workflow" / ".gitignore").read_text(encoding="utf-8") == "*\n")
check("R2 resolved root printed to STDERR", "workflow: root" in err and str(REPO.resolve()) in err)
check("R2 STDOUT carries no root line (the 124 stdout assertions stay untouched)",
      "workflow: root" not in out)

# ---------------------------------------------------------------------------
# R3. A verb run from a nested SUBDIRECTORY finds the task above it (the walk-up in action).
# ---------------------------------------------------------------------------
DEEP = REPO / "sub" / "deep"
DEEP.mkdir(parents=True)
rc, out, err = run("status", cwd=DEEP)
check("R3 status from a subdirectory finds the task above",
      rc == 0 and "current step: need" in out)

# ---------------------------------------------------------------------------
# R4. `start` from a subdir REFUSES because a marker already sits above it (no nested task).
# ---------------------------------------------------------------------------
rc, out, err = run("start", "nested", cwd=DEEP)
check("R4 start refuses a nested task when one is already open above",
      rc == 1 and "already open" in err.lower())

# ---------------------------------------------------------------------------
# R5 / R6. With NO task at or above, the walk-up returns None: a mutating verb fails CLEANLY
# (message, no traceback), and `status` is inert exit 0. `lonely/` sits under TMP, whose only
# marker lives in TMP/repo (a sibling), so nothing is found above lonely.
# ---------------------------------------------------------------------------
LONELY = TMP / "lonely"
LONELY.mkdir()
rc, out, err = run("prepare", "need", cwd=LONELY)
check("R5 prepare with no task fails cleanly (message, not a traceback)",
      rc == 1 and "no task open" in err.lower() and "Traceback" not in err)
rc, out, err = run("status", cwd=LONELY)
check("R6 status with no task is inert (exit 0)", rc == 0 and "no task open" in out)

# ---------------------------------------------------------------------------
# R7. D-10, proven with REAL git (proof #4 - asserted, not inspected): after `start` authors
# .workflow/.gitignore (`*`, no re-includes), a `git add -A` stages NOTHING from .workflow/ -
# the marker, a draft, AND a hand-authored file all stay ignored. This is the whole point of
# the rule - `git add -A` is safe in ANY repo by construction, with no repo-level entry. (M7
# retired the lone re-include along with the warm slot it served, so `*` is now total: a
# strictly simpler, safer invariant than the old "all ignored except one".)
# ---------------------------------------------------------------------------
GITREPO = TMP / "gitproof"
GITREPO.mkdir()
subprocess.run(["git", "init", "-q"], cwd=str(GITREPO), check=True)
rc, out, err = run("start", "git proof", cwd=GITREPO)
check("R7 start succeeds in a real git repo", rc == 0)
# A hand-authored file, a draft, and the marker - the `*` must keep ALL of them ignored.
(GITREPO / ".workflow" / "notes.md").write_text("a hand-authored file\n", encoding="utf-8")
(GITREPO / ".workflow" / "draft-need.md").write_text("a draft\n", encoding="utf-8")
subprocess.run(["git", "add", "-A"], cwd=str(GITREPO), check=True)
staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                        cwd=str(GITREPO), capture_output=True, text=True).stdout
check("R7 a hand-authored .workflow file is NOT staged (`*` is total, no re-include)",
      ".workflow/notes.md" not in staged)
check("R7 marker.json is NOT staged", ".workflow/marker.json" not in staged)
check("R7 a draft is NOT staged", ".workflow/draft-need.md" not in staged)
check("R7 .gitignore itself is NOT staged (no !.gitignore line)",
      ".workflow/.gitignore" not in staged)

# ---------------------------------------------------------------------------
# R8. The workflow.py half of Architecture Section 2, proof 2: marker_path's spelling is exactly
# `.workflow/marker.json`. The statusline_wf.py and nudge.py copies of this literal (which stat it
# WITHOUT importing this module) are asserted equal to it in Block 2, when those files exist.
# ---------------------------------------------------------------------------
check("R8 marker_path spelling is .workflow/marker.json",
      workflow.marker_path(Path("/anywhere")).as_posix().endswith(".workflow/marker.json"))

# ---------------------------------------------------------------------------
# R9 / R10. The `root=None` library affordance (D-3(a)): the walk-up default the readers offer a
# human/model at a REPL, which NO shipped caller uses (every verb passes an explicit root). R9 -
# with CWD inside an open task, a bare load_marker()/receipt_state() resolves via the marker
# walk-up. R10 - with CWD in NO task, a bare _save_marker() degrades to a clean _fail (the guard
# that keeps a TypeError out of a hook) and writes nothing. CWD is process-global, so it is set
# under try/finally and restored.
# ---------------------------------------------------------------------------
_orig_cwd = os.getcwd()
try:
    os.chdir(str(DEEP))    # inside REPO's open task (its marker sits at REPO, an ancestor of DEEP)
    m = workflow.load_marker()             # no root -> walk up from CWD
    check("R9 load_marker() with no root walks up to the task above",
          m is not None and m.get("task_title") == "rooting task")
    check("R9 receipt_state() with no root resolves via walk-up (need has no receipt here)",
          workflow.receipt_state("need") == "missing")
    os.chdir(str(LONELY))  # no task at or above
    rc = workflow._save_marker({"stray": True})   # no root, no task -> clean _fail, not a TypeError
    check("R10 _save_marker() with no root and no task fails cleanly (writes no marker)",
          rc == 1 and not (LONELY / ".workflow" / "marker.json").exists())
finally:
    os.chdir(_orig_cwd)


failed = [name for name, ok in checks if not ok]
print("\n{}/{} checks passed.".format(len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
