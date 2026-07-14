#!/usr/bin/env python3
"""Fail-closed matrix for the `publish` verb (Decision D-1, Design beta-2).

`publish` is the only verb that writes a real, committed document, so its contract is
FAIL-CLOSED: anything ambiguous must refuse and leave the doc byte-for-byte untouched,
never guess into it. This suite drives every documented branch as a subprocess and, on
every refusal, asserts the target is unchanged. It also proves the two success paths
(first write prepends under the anchor; re-settle replaces in place), structural
idempotence (proof #2), and that a publish preserves the doc's exact line endings.
"""
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "claude" / "workflow"
TMP = Path(tempfile.mkdtemp(prefix="wf_pub_"))
shutil.copy(SRC / "workflow.py", TMP / "workflow.py")
shutil.copy(SRC / "rulebook.md", TMP / "rulebook.md")
(TMP / "docs").mkdir()

WF = TMP / ".workflow"
ENTRY = WF / "overview-entry.md"
OVERVIEW = TMP / "docs" / "OVERVIEW.md"

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


def n_starts():
    return OVERVIEW.read_text(encoding="utf-8").count('<!-- WF:need:start')


def n_ends():
    return OVERVIEW.read_text(encoding="utf-8").count('<!-- WF:need:end -->')


def no_tmp_left():
    return not any(p.name.endswith(".tmp") for p in (TMP / "docs").iterdir())


run("start", "Publish matrix task")

# 1. No entry file -> refuse.
rc, _, err = run("publish", "need")
check("1 refuse when no drafted entry exists", rc == 1 and "no drafted entry" in err.lower())

# 2. Empty / whitespace-only entry -> refuse.
set_entry("   \n\t\n")
rc, _, err = run("publish", "need")
check("2 refuse on empty entry", rc == 1 and "no drafted entry" in err.lower())

P1 = "**2026-07-14** - the settled Need, round one.\nA second line of prose.\n"
set_entry(P1)

# 3. Target doc missing -> refuse.
rc, _, err = run("publish", "need")
check("3 refuse when target doc is missing", rc == 1 and ("does not exist" in err.lower() or "unreadable" in err.lower()))

# 4. Target exists but no anchor heading -> refuse, doc untouched.
OVERVIEW.write_text("# Overview\n\nNo status heading here.\n", encoding="utf-8")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("4 refuse when anchor is absent, doc untouched",
      rc == 1 and "anchor" in err.lower() and ov_bytes() == before)

# 5. First write prepends the block newest-first under the anchor; FULL entry lands.
OVERVIEW.write_text("# Overview\n\n## Current status\n\n**2026-07-01** - an older status entry.\n",
                    encoding="utf-8")
rc, out, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
first_ok = (
    rc == 0
    and n_starts() == 1 and n_ends() == 1
    and "round one" in doc and "A second line of prose." in doc          # BOTH lines, not just the first
    and doc.index("<!-- WF:need:start") > doc.index("## Current status")
    and doc.index("<!-- WF:need:start") < doc.index("an older status entry")
    and no_tmp_left()
)
check("5 first write prepends one block, full entry, under the anchor, newest-first", first_ok)

# 6. Re-settle replaces in place, NEVER appends a duplicate (proof #2).
P2 = "**2026-07-14** - the settled Need, ROUND TWO (revised).\n"
set_entry(P2)
rc, out, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
check("6 re-settle replaces in place, no duplicate block (proof #2)",
      rc == 0 and n_starts() == 1 and n_ends() == 1
      and "ROUND TWO" in doc and "round one" not in doc and "an older status entry" in doc)

# 7. Structural idempotence: same entry again changes nothing.
snap = ov_bytes()
run("publish", "need")
check("7 re-running with the same entry is a no-op (idempotent)", ov_bytes() == snap)

# 8. LF preservation: a pure-LF doc stays pure-LF after publish (the CRLF-flip regression).
OVERVIEW.write_bytes(b"# Overview\n\n## Current status\n\n**old** LF entry.\n")   # forced LF on disk
set_entry("**2026-07-14** - LF preservation check.\n")
rc, _, _ = run("publish", "need")
check("8 publish preserves LF line endings (no whole-file CRLF flip)",
      rc == 0 and b"\r\n" not in OVERVIEW.read_bytes())

# 9. A drafted entry that itself contains a sentinel line -> refuse, doc untouched.
before = ov_bytes()
set_entry('An entry that quotes a marker line:\n<!-- WF:need:start task="x" -->\n...more.\n')
rc, _, err = run("publish", "need")
check("9 refuse when the entry contains a sentinel line, doc untouched",
      rc == 1 and "sentinel line" in err.lower() and ov_bytes() == before)

# reset the entry to something clean for the remaining malformed-doc tests
set_entry("**2026-07-14** - clean entry for the malformed-doc checks.\n")

# 10. More than one pair -> refuse.
OVERVIEW.write_text(
    '# Overview\n\n## Current status\n\n'
    '<!-- WF:need:start task="aaa" -->\none\n<!-- WF:need:end -->\n\n'
    '<!-- WF:need:start task="bbb" -->\ntwo\n<!-- WF:need:end -->\n',
    encoding="utf-8")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("10 refuse on more than one sentinel pair, doc untouched",
      rc == 1 and "more than one" in err.lower() and ov_bytes() == before)

# 11. A start with no matching end -> refuse.
OVERVIEW.write_text(
    '# Overview\n\n## Current status\n\n<!-- WF:need:start task="aaa" -->\ndangling\n',
    encoding="utf-8")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("11 refuse on a start with no matching end, doc untouched",
      rc == 1 and "malformed" in err.lower() and ov_bytes() == before)

# 12. A reversed pair (end line before start line) -> refuse.
OVERVIEW.write_text(
    '# Overview\n\n## Current status\n\n<!-- WF:need:end -->\nbody\n<!-- WF:need:start task="aaa" -->\n',
    encoding="utf-8")
before = ov_bytes()
rc, _, err = run("publish", "need")
check("12 refuse on a reversed sentinel pair, doc untouched",
      rc == 1 and "precede" in err.lower() and ov_bytes() == before)

# 13. CRLF preservation: a pure-CRLF doc stays pure-CRLF after publish (the OTHER newline
#     direction from check 8 - the one that actually bites on the developer's Windows box).
OVERVIEW.write_bytes(b"# Overview\r\n\r\n## Current status\r\n\r\n**old** CRLF entry.\r\n")
set_entry("**2026-07-14** - CRLF preservation check.\n")
rc, _, _ = run("publish", "need")
raw = OVERVIEW.read_bytes()
check("13 publish preserves CRLF line endings (no bare LF introduced)",
      rc == 0 and b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"))

# 14. The anchor is matched as an EXACT heading line, not a prefix: a "## Current status
#     archive" heading (without the exact anchor) is NOT matched, so first-write fails closed
#     rather than misplacing the block under the wrong heading.
OVERVIEW.write_text("# Overview\n\n## Current status archive (do not touch)\n\n**old** archived.\n",
                    encoding="utf-8")
before = ov_bytes()
set_entry("**2026-07-14** - must not land under the archive heading.\n")
rc, _, err = run("publish", "need")
check("14 anchor prefix ('... archive') is not matched; fail closed, doc untouched",
      rc == 1 and "anchor" in err.lower() and ov_bytes() == before)

# 15. An INDENTED sentinel example (real markers are always column-0) must NOT be matched as
#     the live block: publish treats it as zero pairs -> first-write, leaving the example intact
#     rather than overwriting it (a fail-open gap the column-0 match closes).
OVERVIEW.write_text(
    "# Overview\n\n## Current status\n\nHow the markers look:\n\n"
    '    <!-- WF:need:start task="EXAMPLE" -->\n    EXAMPLE BODY\n    <!-- WF:need:end -->\n\n'
    "**2026-01-01** - real older entry.\n",
    encoding="utf-8")
set_entry("**2026-07-14** - a real settled entry.\n")
rc, _, _ = run("publish", "need")
doc = OVERVIEW.read_text(encoding="utf-8")
check("15 indented sentinel example is not overwritten (first-write, example intact)",
      rc == 0 and "EXAMPLE BODY" in doc and "a real settled entry" in doc
      and doc.count("\n<!-- WF:need:start") == 1)   # exactly one NEW column-0 marker added

shutil.rmtree(TMP, ignore_errors=True)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
