#!/usr/bin/env python3
"""Fail-closed matrix for the `publish` verb (M4 log path).

`publish` is the only verb that writes a real, committed document, so its contract is
FAIL-CLOSED: anything ambiguous must refuse and leave the doc byte-for-byte untouched,
never guess into it. This suite drives the LOG-mode path (Need -> OVERVIEW) as a
subprocess and, on every refusal, asserts the target is unchanged.

Two M4 facts shape this suite (vs the retired M3 version):
  * THE GATE is upstream of everything. `publish` now refuses unless the step is CURRENT
    and holds a FRESH receipt (the challenge ran against the bytes on disk). So the suite
    must first settle a real challenge before it can even reach the entry/doc/marker
    branches - and it proves the gate itself in both directions (no-receipt, non-current).
  * The markers carry identity on BOTH ends - <!-- WF:need:<task_id>:start --> ... :end -->
    - and the anchor is a SEEDED comment (<!-- WF:anchor:current-status -->), not heading
    text. (The old heading-prefix check #14 is retired: that mechanism no longer exists.)
The two success modes and byte-level newline preservation are proven here too; the
cross-task/section MODES live in test_publish_modes.py.
"""
import subprocess
import sys
import shutil
import tempfile
import re
import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "claude" / "workflow"
TMP = Path(tempfile.mkdtemp(prefix="wf_pub_"))
shutil.copy(SRC / "workflow.py", TMP / "workflow.py")
shutil.copy(SRC / "rulebook.md", TMP / "rulebook.md")
(TMP / "docs").mkdir()

WF = TMP / ".workflow"
ENTRY = WF / "publish-entry.md"
NEED = TMP / "docs" / "draft-need.md"
OVERVIEW = TMP / "docs" / "OVERVIEW.md"
ANCHOR = "<!-- WF:anchor:current-status -->"      # the seeded per-location anchor publish targets

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def run(*args):
    p = subprocess.run([sys.executable, str(TMP / "workflow.py"), *args],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def set_entry(text):
    WF.mkdir(exist_ok=True)
    ENTRY.write_text(text, encoding="utf-8")


def ov_bytes():
    return OVERVIEW.read_bytes() if OVERVIEW.exists() else None


# Count MY need blocks by the M4 both-ends format (any hex/kebab scope); only need blocks
# ever appear in this suite's OVERVIEW, so this is exact.
_START = re.compile(r"(?m)^<!-- WF:need:[a-z0-9-]+:start -->$")
_END = re.compile(r"(?m)^<!-- WF:need:[a-z0-9-]+:end -->$")


def n_starts():
    return len(_START.findall(OVERVIEW.read_text(encoding="utf-8")))


def n_ends():
    return len(_END.findall(OVERVIEW.read_text(encoding="utf-8")))


def task_id():
    return json.loads((WF / "marker.json").read_text(encoding="utf-8"))["task_id"]


def no_tmp_left():
    return not any(p.name.endswith(".tmp") for p in (TMP / "docs").iterdir())


def scaffold(seed="**2026-01-01** - an older status entry.\n"):
    """A valid OVERVIEW: heading, the SEEDED comment anchor, then prior content."""
    OVERVIEW.write_text("# Overview\n\n## Current status\n\n" + ANCHOR + "\n\n" + seed, encoding="utf-8")


def settle_need():
    """Run a real challenge cycle so `need` (the current step) holds a FRESH receipt -
    the precondition the gate now enforces before any publish can proceed."""
    NEED.write_text("# Need\nthe toy need under attack.\n", encoding="utf-8")
    run("prepare", "need")
    ctx = (WF / "context.md").read_text(encoding="utf-8")
    canary = re.search(r"WF-CANARY-\w+", ctx).group(0)
    (WF / "challenge.md").write_text(
        "## COLD verdict\n" + canary + "\nfindings\n## WARM verdict\nok\n", encoding="utf-8")
    run("record", "need")


run("start", "Publish matrix task")
scaffold()

# 1. THE GATE (no receipt): publish before any challenge -> refuse, doc untouched. This is
#    the honest floor - unvouched prose must never reach a committed doc.
before = ov_bytes()
set_entry("**2026** - would-be prose with no challenge behind it.\n")
rc, _, err = run("publish", "need")
check("1 gate: refuse publish with no fresh receipt, doc untouched",
      rc == 1 and "receipt" in err.lower() and ov_bytes() == before)

# Establish the fresh receipt the rest of the matrix needs. From here on, draft-need.md is
# never touched, so the receipt stays fresh and every refusal below is attributable to the
# entry or the doc, not to the gate.
settle_need()

# 1b. THE GATE (stale receipt): editing the draft AFTER `record` flips the receipt to 'stale',
#     and publish must refuse - the honest-floor core (the challenge no longer matches the bytes
#     on disk). Distinct from 'missing' (check 1) and 'non-current' (check 18): a regression that
#     checked only "a receipt exists" instead of "it is fresh" would slip unvouched prose through.
#     Restore the draft afterward so checks 2-18 keep their fresh receipt.
need_saved = NEED.read_bytes()
NEED.write_bytes(need_saved + b"\nedited AFTER the challenge - the receipt is now stale.\n")
before = ov_bytes()
set_entry("**2026** - would-be prose published over a STALE receipt.\n")
rc, _, err = run("publish", "need")
check("1b gate: refuse publish on a STALE receipt (draft edited after record), doc untouched",
      rc == 1 and "stale" in err.lower() and ov_bytes() == before)
NEED.write_bytes(need_saved)     # restore -> receipt fresh again for the rest of the matrix

# 2. No entry file -> refuse, doc untouched.
ENTRY.unlink(missing_ok=True)
before = ov_bytes()
rc, _, err = run("publish", "need")
check("2 refuse when no drafted entry exists, doc untouched",
      rc == 1 and "no drafted entry" in err.lower() and ov_bytes() == before)

# 3. Empty / whitespace-only entry -> refuse, doc untouched.
set_entry("   \n\t\n")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("3 refuse on empty entry, doc untouched",
      rc == 1 and "no drafted entry" in err.lower() and ov_bytes() == before)

# 4. An entry that itself carries a column-0 WF marker line -> refuse (it would inject bogus
#    structure), doc untouched. Key-agnostic guard (RISKS #12 second half).
set_entry('An entry that quotes a marker line at column 0:\n<!-- WF:need:xxxx:start -->\n...more.\n')
before = ov_bytes()
rc, _, err = run("publish", "need")
check("4 refuse when the entry contains a column-0 marker line, doc untouched",
      rc == 1 and "marker line" in err.lower() and ov_bytes() == before)

# A clean, valid entry for the doc-shape checks below.
set_entry("**2026-07-14** - the settled Need, round one.\nA second line of prose.\n")

# 5. Target doc missing -> refuse (place INTO a real doc, never create one).
OVERVIEW.unlink()
rc, _, err = run("publish", "need")
check("5 refuse when the target doc is missing (never created)",
      rc == 1 and "does not exist" in err.lower() and not OVERVIEW.exists())

# 6. Doc present but the seeded anchor is absent -> refuse, doc untouched.
OVERVIEW.write_text("# Overview\n\n## Current status\n\nno seeded anchor here.\n", encoding="utf-8")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("6 refuse when the seeded anchor is absent, doc untouched",
      rc == 1 and "anchor" in err.lower() and ov_bytes() == before)

# 7. Duplicate seeded anchor -> refuse (ambiguous location), doc untouched.
OVERVIEW.write_text("# Overview\n\n" + ANCHOR + "\n\nx\n\n" + ANCHOR + "\n\ny\n", encoding="utf-8")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("7 refuse on a duplicate seeded anchor, doc untouched",
      rc == 1 and "anchor" in err.lower() and ov_bytes() == before)

# 7b. The clean entry set before check 5 is STILL present after three refusals (5, 6, 7):
#     the drafted entry is consumed ONLY on success, never on a refusal.
check("7b a refusal leaves the drafted entry intact (consumed only on success)", ENTRY.exists())

# 8. First write: prepends ONE block under the anchor, newest-first, with the FULL entry.
scaffold()
rc, out, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
tid = task_id()
need_start = "<!-- WF:need:{}:start -->".format(tid)
first_ok = (
    rc == 0
    and n_starts() == 1 and n_ends() == 1
    and "round one" in doc and "A second line of prose." in doc      # BOTH lines, not just the first
    and doc.index(need_start) > doc.index(ANCHOR)                    # under the anchor...
    and doc.index(need_start) < doc.index("an older status entry")   # ...and ABOVE the older content
    and no_tmp_left()
)
check("8 first write prepends one block, full entry, under the anchor, newest-first", first_ok)

# 8b. A successful publish CONSUMES the drafted entry, so stale prose cannot be silently re-published.
check("8b successful publish consumes the drafted entry", not ENTRY.exists())

# 9. Re-settle replaces THIS task's block in place, never appends a duplicate (proof #2).
set_entry("**2026-07-14** - the settled Need, ROUND TWO (revised).\n")
rc, out, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
check("9 re-settle replaces in place, no duplicate block (proof #2)",
      rc == 0 and n_starts() == 1 and n_ends() == 1
      and "ROUND TWO" in doc and "round one" not in doc and "an older status entry" in doc)

# 10. Structural idempotence: re-publishing the same settled prose is a byte no-op.
set_entry("**2026-07-14** - the settled Need, ROUND TWO (revised).\n")
snap = ov_bytes()
run("publish", "need")
check("10 re-running with the same entry is a byte-for-byte no-op (idempotent)", ov_bytes() == snap)

# --- Malformed-doc matrix: the markers carry THIS task's id, so they count as "mine" and
#     trip the fail-closed guard (a different-scope block would just be ignored, not an error).
set_entry("**2026-07-14** - clean entry for the malformed-doc checks.\n")
tid = task_id()


def with_body(body):
    OVERVIEW.write_text("# Overview\n\n## Current status\n\n" + ANCHOR + "\n\n" + body, encoding="utf-8")


# 11. A start with no matching end -> refuse.
with_body("<!-- WF:need:{}:start -->\ndangling, no end\n".format(tid))
before = ov_bytes()
rc, _, err = run("publish", "need")
check("11 refuse on a start with no matching end, doc untouched",
      rc == 1 and "malformed" in err.lower() and ov_bytes() == before)

# 12. A reversed pair (end line before start line) -> refuse.
with_body("<!-- WF:need:{0}:end -->\nbody\n<!-- WF:need:{0}:start -->\n".format(tid))
before = ov_bytes()
rc, _, err = run("publish", "need")
check("12 refuse on a reversed sentinel pair, doc untouched",
      rc == 1 and "precede" in err.lower() and ov_bytes() == before)

# 13. Two full same-scope pairs -> refuse (more than one of my block).
with_body("<!-- WF:need:{0}:start -->\none\n<!-- WF:need:{0}:end -->\n\n"
          "<!-- WF:need:{0}:start -->\ntwo\n<!-- WF:need:{0}:end -->\n".format(tid))
before = ov_bytes()
rc, _, err = run("publish", "need")
check("13 refuse on more than one same-scope pair, doc untouched",
      rc == 1 and "more than one" in err.lower() and ov_bytes() == before)

# 14. A WF marker inside a ``` code fence -> refuse (RISKS #12 fail-closed ruling): we cannot
#     safely place around fenced marker examples, so the whole publish refuses.
with_body("```\n<!-- WF:need:example:start -->\nfenced example\n<!-- WF:need:example:end -->\n```\n")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("14 refuse when a WF marker sits inside a code fence, doc untouched",
      rc == 1 and "fence" in err.lower() and ov_bytes() == before)

# 15. LF preservation: a pure-LF doc stays pure-LF after a successful publish.
OVERVIEW.write_bytes(("# Overview\n\n## Current status\n\n" + ANCHOR + "\n\n**old** LF entry.\n").encode("utf-8"))
set_entry("**2026-07-14** - LF preservation check.\n")
rc, _, _ = run("publish", "need")
check("15 publish preserves LF line endings (no whole-file CRLF flip)",
      rc == 0 and b"\r\n" not in OVERVIEW.read_bytes())

# 16. CRLF preservation: a pure-CRLF doc stays pure-CRLF (the direction that bites on Windows).
OVERVIEW.write_bytes(
    ("# Overview\r\n\r\n## Current status\r\n\r\n" + ANCHOR + "\r\n\r\n**old** CRLF entry.\r\n").encode("utf-8"))
set_entry("**2026-07-14** - CRLF preservation check.\n")
rc, _, _ = run("publish", "need")
raw = OVERVIEW.read_bytes()
check("16 publish preserves CRLF line endings (no bare LF introduced)",
      rc == 0 and b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"))

# 17. Column-0 discipline: an INDENTED marker example (real markers are always column-0) is
#     NOT treated as the live block - publish first-writes a real block and leaves the example
#     intact. (#14 covers fenced examples; this covers the plain-indented case.)
OVERVIEW.write_text(
    "# Overview\n\n## Current status\n\n" + ANCHOR + "\n\nHow the markers look:\n\n"
    '    <!-- WF:need:example:start -->\n    EXAMPLE BODY\n    <!-- WF:need:example:end -->\n\n'
    "**2026-01-01** - real older entry.\n", encoding="utf-8")
set_entry("**2026-07-14** - a real settled entry (must not disturb the indented example).\n")
rc, _, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
check("17 indented marker example is not matched; first-write, example left intact",
      rc == 0 and "EXAMPLE BODY" in doc and "a real settled entry" in doc and n_starts() == 1)

# 18. THE GATE (non-current): after advancing off Need, republishing it must refuse. need's
#     receipt is still fresh (draft-need.md was never touched), so the gate opens the advance;
#     the refusal is purely because need is no longer the current step.
before = ov_bytes()
rc, _, _ = run("advance")                                  # need -> design (fresh receipt opens it)
set_entry("**2026** - stale re-publish of a step we already left.\n")
rc, _, err = run("publish", "need")
check("18 gate: refuse republish of a non-current step, doc untouched",
      rc == 1 and "current" in err.lower() and ov_bytes() == before)

shutil.rmtree(TMP, ignore_errors=True)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
