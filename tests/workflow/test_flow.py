#!/usr/bin/env python3
"""End-to-end DETERMINISTIC chain for the Need slice (proof #1, minus the model).

Drives the whole loop the conductor describes - start -> prepare -> (challenger writes
a result) -> record -> publish -> advance - as one continuous flow, standing in for the
challenger by writing a result file that echoes the planted canary. This proves the parts
that must "work every time": a step that really settles through the gate gets its receipt
AND its OVERVIEW auto-doc, in one run. (The model-mediated parts - actually spawning the
challenger, the warm pass - are exercised in the live e2e run, not here.)
"""
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "claude" / "workflow"
TMP = Path(tempfile.mkdtemp(prefix="wf_flow_"))
shutil.copy(SRC / "workflow.py", TMP / "workflow.py")
shutil.copy(SRC / "rulebook.md", TMP / "rulebook.md")
(TMP / "docs").mkdir()
(TMP / ".workflow").mkdir()   # D-10: drafts + task state live here now; create before any draft write
(TMP / ".git").mkdir()        # D-2a: `start` roots the task at the nearest .git ancestor - give it one

sys.path.insert(0, str(TMP))
import workflow  # noqa: E402

# Aim every in-process reader at THIS test's project root (root=TMP), as the M5 status line and
# nudge pass the platform-handed root - never leaning on process cwd (the D-3 catastrophe the
# subprocess `cwd=` guards). Qualified `workflow.*` resolves on the module, never to these local
# wrappers, so there is no recursion to guard against.
def load_marker():
    return workflow.load_marker(root=TMP)


def receipt_state(step):
    return workflow.receipt_state(step, root=TMP)


WF = TMP / ".workflow"
NEED = WF / "draft-need.md"                    # D-10: draft lives in .workflow/ now
OVERVIEW = TMP / "docs" / "OVERVIEW.md"
CONTEXT = WF / "context.md"
CHALLENGE = WF / "challenge.md"
ENTRY = WF / "publish-entry.md"

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def run(*args):
    # cwd=TMP so the subprocess roots at THIS test's project (walk-up from cwd), never the real
    # repo above it - the D-3/D-10 guard (Architecture Section 2).
    p = subprocess.run([sys.executable, str(TMP / "workflow.py"), *args],
                       capture_output=True, text=True, cwd=str(TMP))
    return p.returncode, p.stdout, p.stderr


def canary():
    for line in CONTEXT.read_text(encoding="utf-8").splitlines():
        if "CANARY (echo this token" in line:
            return line.split(":", 1)[1].strip()
    return None


# Scaffold a minimal OVERVIEW with the SEEDED anchor the publish half targets. In M4 the
# anchor is a comment sentinel (<!-- WF:anchor:<slug> -->), NOT the heading text - headings
# drift and collide, so the engine keys off a seeded marker (see the publish engine).
OVERVIEW.write_text(
    "# Overview\n\n## Current status\n\n<!-- WF:anchor:current-status -->\n\n"
    "**2026-01-01** - seed entry.\n", encoding="utf-8")
ANCHOR = "<!-- WF:anchor:current-status -->"

# 1) start -> 2) draft -> 3) prepare -> 4) challenger writes result -> 5) record
run("start", "End-to-end need")
task_id = load_marker()["task_id"]                  # the log-block scope is this task's id
need_start = "<!-- WF:need:{}:start -->".format(task_id)     # M4 both-ends-identity marker
NEED.write_text("# Need\nThe toy need, drafted for the flow test.\n", encoding="utf-8")
run("prepare", "need")
CHALLENGE.write_text("## COLD verdict\nlooks ok. canary: {}\n\n## WARM verdict\nok\n".format(canary()),
                     encoding="utf-8")
rc, _, _ = run("record", "need")
check("1 record writes a fresh receipt after a real prepare->challenge", rc == 0 and receipt_state("need") == "fresh")

# 6) publish the settled prose into OVERVIEW
ENTRY.write_text("**2026-07-14** - Need settled: the machinery must prove the pattern end to end.\n",
                 encoding="utf-8")
rc, _, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
check("2 publish auto-docs the settled Need into OVERVIEW under the seeded anchor, newest-first",
      rc == 0 and "Need settled: the machinery" in doc
      and doc.index(need_start) > doc.index(ANCHOR)
      and doc.index(need_start) < doc.index("seed entry"))

# 7) advance - the gate opens because the receipt is fresh
rc, _, _ = run("advance")
check("3 advance opens on the fresh receipt (need -> design)", rc == 0 and load_marker()["current_step"] == "design")

# The whole chain settled one step end to end with both outputs (receipt + auto-doc).
check("4 both outputs present: fresh receipt recorded AND the OVERVIEW block written",
      "need" in load_marker().get("receipts", {})
      and OVERVIEW.read_text(encoding="utf-8").count(need_start) == 1)

shutil.rmtree(TMP, ignore_errors=True)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
