#!/usr/bin/env python3
"""The two publish MODES do the right thing (M4): log-accumulate and sectioned.

test_publish.py proves the verb is fail-closed on the Need/log path. THIS suite proves the
generalized engine behaves correctly across both shapes the review steps write:

  * Part A - the engine (`_place_block`) at the unit level, on strings: log accumulate
    (prepend, per-task, newest-first) and sectioned replace-or-create (append, per-slug,
    stable order), plus every fail-closed path and the key-agnostic entry/anchor guards.
  * Part B - section mode end to end through the CLI (Architecture -> ARCHITECTURE):
    --section / --new / --update intent guards, and the two exception rows (Shipping has
    no publish half; Implementation has no recipe).
  * Part C - log-accumulate across TWO tasks through the CLI (the RISKS #12 key-half fix):
    a second task must accumulate under the shared OVERVIEW anchor, never clobber the first.

Byte-level throughout; the engine is exercised directly and via the real subprocess.
"""
import subprocess
import sys
import shutil
import tempfile
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "claude" / "workflow"
TMP = Path(tempfile.mkdtemp(prefix="wf_modes_"))
shutil.copy(SRC / "workflow.py", TMP / "workflow.py")
shutil.copy(SRC / "rulebook.md", TMP / "rulebook.md")
(TMP / "docs").mkdir()
(TMP / ".workflow").mkdir()   # D-10: drafts + task state live here now
(TMP / ".git").mkdir()        # D-2a: `start` roots the task at the nearest .git ancestor

sys.path.insert(0, str(TMP))
import workflow as wf  # noqa: E402  (import after copy so `import workflow` finds the copy)

# Aim in-process readers at THIS test's project root (root=TMP), as the M5 status line and nudge
# pass the platform-handed root - never leaning on process cwd (the D-3 catastrophe the subprocess
# `cwd=` guards). Qualified `wf.*` resolves on the module, never to these local wrappers, so there
# is no recursion to guard against.
def load_marker():
    return wf.load_marker(root=TMP)


def receipt_state(step):
    return wf.receipt_state(step, root=TMP)

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def refuses(name, fn):
    """Assert `fn` raises the engine's fail-closed _PublishError."""
    try:
        fn()
        check(name, False)
    except wf._PublishError:
        check(name, True)


# ===========================================================================
# Part A - the engine (`_place_block`) at the unit level.
# ===========================================================================
# --- log-accumulate: prepend, per-task scope, newest-first, replace-in-place ---
doc = "# Doc\n\n<!-- WF:anchor:current-status -->\n\nolder stuff\n"
d1 = wf._place_block(doc, "need", "aaaa", "current-status", "prepend", "BODY-A")
check("A1 log first-write inserts the block", "<!-- WF:need:aaaa:start -->" in d1 and "BODY-A" in d1)
d2 = wf._place_block(d1, "need", "bbbb", "current-status", "prepend", "BODY-B")
check("A2 log second task accumulates (no clobber)",
      "WF:need:aaaa:start" in d2 and "WF:need:bbbb:start" in d2)
check("A3 log newest-first (B above A)", d2.index("BODY-B") < d2.index("BODY-A"))
d3 = wf._place_block(d2, "need", "aaaa", "current-status", "prepend", "BODY-A2")
check("A4 log re-settle replaces in place (one A block)",
      d3.count("<!-- WF:need:aaaa:start -->") == 1 and "BODY-A2" in d3)
check("A5 log re-settle leaves the other task intact",
      "BODY-B" in d3 and d3.count("<!-- WF:need:bbbb:start -->") == 1)

# --- cross-KEY under a SHARED anchor: need + judgment interleave (the shared-anchor design -
#     anchors are per-location, not per-key, so a task's Need and its later Judgment coexist). ---
shared = "# Overview\n\n<!-- WF:anchor:current-status -->\n\nolder\n"
k1 = wf._place_block(shared, "need", "t1", "current-status", "prepend", "NEED-BODY")
k2 = wf._place_block(k1, "judgment", "t1", "current-status", "prepend", "JUDG-BODY")
check("A5b cross-key: need and judgment both live under one shared anchor",
      "WF:need:t1:start" in k2 and "WF:judgment:t1:start" in k2)
check("A5c cross-key newest-first: the later judgment sits above the earlier need",
      k2.index("JUDG-BODY") < k2.index("NEED-BODY"))
kr = wf._place_block(k2, "need", "t1", "current-status", "prepend", "NEED-BODY-2")
check("A5d re-settling need leaves the judgment block untouched",
      "JUDG-BODY" in kr and kr.count("<!-- WF:judgment:t1:start -->") == 1 and "NEED-BODY-2" in kr)

# --- sectioned: append, per-slug, stable order, replace-in-place ---
sdoc = "# Arch\n\n<!-- WF:anchor:architecture-sections -->\n\ntail-text\n"
s1 = wf._place_block(sdoc, "arch", "comp-one", "architecture-sections", "append_section", "SEC-1")
s2 = wf._place_block(s1, "arch", "comp-two", "architecture-sections", "append_section", "SEC-2")
check("A6 section append both present", "WF:arch:comp-one:start" in s2 and "WF:arch:comp-two:start" in s2)
check("A7 section stable order (one before two)", s2.index("SEC-1") < s2.index("SEC-2"))
sr = wf._place_block(s2, "arch", "comp-one", "architecture-sections", "append_section", "SEC-1B")
check("A8 section re-settle replaces in place",
      sr.count("<!-- WF:arch:comp-one:start -->") == 1 and "SEC-1B" in sr)
check("A9 section re-settle keeps order", sr.index("SEC-1B") < sr.index("SEC-2"))
# A9b 3+ sections: a NEW section appends after the LAST managed block, not merely the 2nd.
s3 = wf._place_block(sr, "arch", "comp-three", "architecture-sections", "append_section", "SEC-3")
check("A9b third section appends after the last (order: one, two, three)",
      s3.index("SEC-1B") < s3.index("SEC-2") < s3.index("SEC-3"))

# --- fail-closed paths ---
refuses("A10 missing anchor refuses",
        lambda: wf._place_block("# no anchor\n", "need", "a", "current-status", "prepend", "X"))
refuses("A11 duplicate anchor refuses",
        lambda: wf._place_block("<!-- WF:anchor:x -->\n<!-- WF:anchor:x -->\n", "need", "a", "x", "prepend", "Y"))
dupdoc = ("<!-- WF:anchor:x -->\n<!-- WF:need:a:start -->\nb\n<!-- WF:need:a:end -->\n"
          "<!-- WF:need:a:start -->\nc\n<!-- WF:need:a:end -->\n")
refuses("A12 duplicate same-scope block refuses",
        lambda: wf._place_block(dupdoc, "need", "a", "x", "prepend", "Z"))
refuses("A13 orphan start refuses",
        lambda: wf._place_block("<!-- WF:anchor:x -->\n<!-- WF:need:a:start -->\nno end\n", "need", "a", "x", "prepend", "Z"))

# --- key-agnostic entry/anchor guard ---
check("A14 entry guard rejects a column-0 marker line",
      wf._entry_has_marker_line("text\n<!-- WF:design:zzzz:start -->\nmore"))
check("A15 entry guard rejects a column-0 anchor line",
      wf._entry_has_marker_line("<!-- WF:anchor:current-status -->"))
check("A16 entry guard allows an inline backtick mention",
      not wf._entry_has_marker_line("see `<!-- WF:need:x:start -->` inline"))
check("A17 entry guard allows plain prose",
      not wf._entry_has_marker_line("a normal settled-need paragraph."))

# --- append_section is bounded to the CURRENT anchor's region (no cross-anchor bleed) ---
twoanchor = ("<!-- WF:anchor:sec-one -->\n\n<!-- WF:arch:aaa:start -->\nA\n<!-- WF:arch:aaa:end -->\n\n"
             "<!-- WF:anchor:sec-two -->\n\n<!-- WF:arch:bbb:start -->\nB\n<!-- WF:arch:bbb:end -->\n")
placed = wf._place_block(twoanchor, "arch", "ccc", "sec-one", "append_section", "C-BODY")
check("A18 append_section stays inside its own anchor region",
      placed.index("C-BODY") < placed.index("<!-- WF:anchor:sec-two -->"))

# --- fence guard: a fenced WF marker makes the whole publish fail-closed (RISKS #12) ---
fenced = ("<!-- WF:anchor:current-status -->\n\n```\n<!-- WF:need:example:start -->\nex\n"
          "<!-- WF:need:example:end -->\n```\n")
refuses("A19 fenced WF marker refuses (fail-closed)",
        lambda: wf._place_block(fenced, "need", "zzz", "current-status", "prepend", "X"))
# CB2 (correctness red-team): the guard also covers ~~~ fences and INDENTED ``` fences, not just
# a column-0 ``` - the old ```-only check failed OPEN on both, splicing a new section inside the fence.
tilde_fenced = ("<!-- WF:anchor:current-status -->\n\n~~~\n<!-- WF:need:example:start -->\nex\n"
                "<!-- WF:need:example:end -->\n~~~\n")
refuses("A19b ~~~-fenced WF marker refuses (fail-closed)",
        lambda: wf._place_block(tilde_fenced, "need", "zzz", "current-status", "prepend", "X"))
indented_fenced = ("<!-- WF:anchor:current-status -->\n\n  ```\n<!-- WF:need:example:start -->\nex\n"
                   "<!-- WF:need:example:end -->\n  ```\n")
refuses("A19c indented-```-fenced WF marker refuses (fail-closed)",
        lambda: wf._place_block(indented_fenced, "need", "zzz", "current-status", "prepend", "X"))
# B1 (convergence red-team): the guard tracks the OPENING fence's char+length, so a MISMATCHED
# delimiter inside a fence is content, not a closer - a marker in a ```-fence that also contains a
# stray ~~~ line is still caught (the naive 'toggle on any run' failed OPEN here).
mismatch_fenced = ("<!-- WF:anchor:current-status -->\n\n```\nsome code\n~~~\n"
                   "<!-- WF:need:example:start -->\nex\n<!-- WF:need:example:end -->\n```\n")
refuses("A19d marker in a ```-fence containing a stray ~~~ still refuses (fail-closed)",
        lambda: wf._place_block(mismatch_fenced, "need", "zzz", "current-status", "prepend", "X"))
# ...and that same mismatch must NOT desync parity for the rest of the doc: a free WF line after a
# properly-closed ```-fence-with-~~~ is NOT wrongly flagged (the old toggle FALSE-refused here).
false_refuse = ("intro\n\n```\ncode\n~~~ not a closer\n```\n\n"
                "<!-- WF:anchor:current-status -->\n\nolder\n")
d19 = wf._place_block(false_refuse, "need", "ok", "current-status", "prepend", "NEW BODY")
check("A19e a WF line after a properly-closed ```-fence-with-~~~ publishes fine (no false refuse)",
      "NEW BODY" in d19 and "<!-- WF:need:ok:start -->" in d19)
# A19f (convergence round-2): a backtick opener whose info string CONTAINS a backtick is NOT a valid
# fence (CommonMark), so a marker after it is free - publish must not false-refuse a legitimate doc.
invalid_opener = "intro\n\n``` `inline`\n<!-- WF:anchor:current-status -->\n\nolder\n```\n"
d19f = wf._place_block(invalid_opener, "need", "ok2", "current-status", "prepend", "NEW BODY 2")
check("A19f marker after an invalid backtick-info-string opener publishes (no false refuse)",
      "NEW BODY 2" in d19f and "<!-- WF:need:ok2:start -->" in d19f)
# A19g/A19h (convergence round-3): a bare CR (\r, no LF) is a CommonMark line ending. The guard
# normalizes it, so a marker hidden by a bare-CR-preceded fence is still caught (fail-open closed),
# and a free marker after a bare-CR-preceded CLOSER is not wrongly flagged (no false refuse).
cr_hidden = "prefix\r```\n<!-- WF:need:x:start -->\nbody\n<!-- WF:need:x:end -->\n```\n"
refuses("A19g marker hidden by a bare-CR-preceded fence still refuses (fail-closed)",
        lambda: wf._place_block(cr_hidden, "need", "yy", "current-status", "prepend", "X"))
cr_closer = "```\nbody\nend-prefix\r```\n\n<!-- WF:anchor:current-status -->\n\nolder\n"
d19h = wf._place_block(cr_closer, "need", "ok3", "current-status", "prepend", "NEW BODY 3")
check("A19h free marker after a bare-CR-preceded closer publishes fine (no false refuse)",
      "NEW BODY 3" in d19h and "<!-- WF:need:ok3:start -->" in d19h)
# A19i (convergence round-4): CommonMark allows ONLY spaces/tabs after a closing fence. A run
# followed by any other "whitespace" (form feed \x0c, vertical tab, NBSP, C0 separators) is NOT a
# closer - the fence stays open, so a marker after it is still fenced and must refuse (str.strip()
# with no args would have wrongly closed it, exposing the marker: fail-open).
ff_closer = ("<!-- WF:anchor:current-status -->\n\n```\nexample:\n```\x0c\n"
             "<!-- WF:need:x:start -->\nfenced body\n<!-- WF:need:x:end -->\n```\n")
refuses("A19i marker after a form-feed pseudo-closer is still fenced (fail-closed)",
        lambda: wf._place_block(ff_closer, "need", "yy", "current-status", "prepend", "X"))


# ===========================================================================
# CLI harness for Parts B and C.
# ===========================================================================
WFDIR = TMP / ".workflow"
ENTRY = WFDIR / "publish-entry.md"


def run(*args):
    # cwd=TMP so the subprocess roots at THIS test's project (walk-up from cwd), never the real
    # repo above it - the D-3/D-10 guard (Architecture Section 2).
    p = subprocess.run([sys.executable, str(TMP / "workflow.py"), *args],
                       capture_output=True, text=True, cwd=str(TMP))
    return p.returncode, (p.stdout + p.stderr).strip()


def entry(text):
    WFDIR.mkdir(exist_ok=True)
    ENTRY.write_text(text, encoding="utf-8")


def draft(step, text):
    (WFDIR / ("draft-" + step + ".md")).write_text(text, encoding="utf-8")   # D-10: drafts in .workflow/


def settle(step):
    """A real challenge cycle so `step` (the current one) holds a fresh receipt."""
    rc, out = run("prepare", step)
    assert rc == 0, "prepare " + step + ": " + out
    ctx = (WFDIR / "context.md").read_text(encoding="utf-8")
    canary = re.search(r"WF-CANARY-\w+", ctx).group(0)
    (WFDIR / "challenge.md").write_text(
        "## COLD verdict\n" + canary + "\nfindings\n## WARM verdict\nok\n", encoding="utf-8")
    rc, out = run("record", step)
    assert rc == 0, "record " + step + ": " + out


# ===========================================================================
# Part B - section mode end to end through the CLI (Architecture -> ARCHITECTURE).
# ===========================================================================
ARCH = TMP / "docs" / "ARCHITECTURE.md"
ARCH.write_text(
    "# Architecture\n\n## Workflow machinery\n\n<!-- WF:anchor:architecture-sections -->\n\n(older sections)\n",
    encoding="utf-8")

run("start", "modes-section")

# Exception row #1: Shipping has NO publish half -> refuse (recipe check fires first).
entry("would-be shipping prose\n")
rc, out = run("publish", "shipping")
check("B1 shipping publish refuses (no publish half)", rc != 0 and "no publish target" in out.lower())

# Reach the architecture step and settle it.
run("advance", "--force")        # need -> design
run("advance", "--force")        # design -> architecture
draft("architecture", "# architecture draft\n\nthe structure under attack\n")
settle("architecture")

# --section required, exactly-one-of, and --update-on-absent all REFUSE and must leave
# ARCHITECTURE byte-for-byte unchanged (the section refusals never asserted this before).
arch_before = ARCH.read_bytes()
entry("SECTION BODY ONE\n")
rc, out = run("publish", "architecture")
check("B2 section mode requires --section (message says 'required'), doc untouched",
      rc != 0 and "required" in out.lower() and ARCH.read_bytes() == arch_before)

rc, out = run("publish", "architecture", "--section", "comp-one", "--new", "--update")
check("B3 section needs exactly one of --new/--update, doc untouched",
      rc != 0 and "exactly one" in out.lower() and ARCH.read_bytes() == arch_before)

entry("SECTION BODY ONE\n")
rc, out = run("publish", "architecture", "--section", "comp-one", "--update")
check("B4 --update on an absent section refuses, doc untouched",
      rc != 0 and "need exactly 1" in out.lower() and ARCH.read_bytes() == arch_before)

# --new creates it.
entry("SECTION BODY ONE\n")
rc, out = run("publish", "architecture", "--section", "comp-one", "--new")
arch = ARCH.read_text(encoding="utf-8")
check("B5 --new creates the section",
      rc == 0 and "<!-- WF:arch:comp-one:start -->" in arch and "SECTION BODY ONE" in arch)
check("B6 entry consumed after a successful section publish", not ENTRY.exists())

# B6b (convergence round-2 BLOCKING #1): the entry is consumed on a successful publish, so a SECOND
#      publish to a DIFFERENT scope WITHOUT redrafting refuses - a surviving entry can never be
#      silently re-used for another section (which would emit the wrong content).
rc, out = run("publish", "architecture", "--section", "comp-two", "--new")
check("B6b a second publish without a fresh entry refuses (no cross-scope re-use)",
      rc != 0 and "no drafted entry" in out.lower())

# --new again on the same slug refuses (already exists), doc byte-unchanged.
arch_before = ARCH.read_bytes()
entry("DUPLICATE\n")
rc, out = run("publish", "architecture", "--section", "comp-one", "--new")
check("B7 --new on an existing section refuses, doc untouched",
      rc != 0 and "already exists" in out.lower() and ARCH.read_bytes() == arch_before)

# --update replaces the section body in place. Use a NON-overlapping body and assert the OLD
# text is GONE (not merely that the new text appears), so an append-instead-of-replace bug
# can't slip through. Still exactly one block.
entry("COMPONENT ONE REWRITTEN FROM SCRATCH\n")
rc, out = run("publish", "architecture", "--section", "comp-one", "--update")
arch = ARCH.read_text(encoding="utf-8")
check("B8 --update replaces the section in place (old body gone, still one block)",
      rc == 0 and "COMPONENT ONE REWRITTEN FROM SCRATCH" in arch
      and "SECTION BODY ONE" not in arch and arch.count("<!-- WF:arch:comp-one:start -->") == 1)

# B8b. Section mode preserves the doc's newline style at the BYTE level (the log path proves
#      this in test_publish 15/16; section mode shares the restore code, so prove it here too).
ARCH.write_bytes(("# Architecture\r\n\r\n## Workflow machinery\r\n\r\n"
                  "<!-- WF:anchor:architecture-sections -->\r\n\r\n(older sections)\r\n").encode("utf-8"))
entry("A CRLF SECTION BODY\n")
rc, out = run("publish", "architecture", "--section", "comp-crlf", "--new")
raw = ARCH.read_bytes()
check("B8b section publish preserves CRLF line endings (no bare LF introduced)",
      rc == 0 and b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n"))

# Exception row #2: Implementation has no recipe. architecture still holds a fresh receipt
# (publishes never touch draft-architecture.md), so a PLAIN advance works - assert it actually
# REACHED implementation (not a silent no-op), then that prepare fails with 'no recipe'
# specifically (the wrong-current-step message also contains the word 'implementation').
rc, out = run("advance")
check("B9 plain advance off architecture reaches implementation (receipt survived the publishes)",
      rc == 0 and load_marker()["current_step"] == "implementation")
rc, out = run("prepare", "implementation")
check("B10 prepare implementation refuses with 'no recipe' (not a wrong-step message)",
      rc != 0 and "no recipe" in out.lower())


# ===========================================================================
# Part C - log-accumulate across two tasks through the CLI (RISKS #12 key-half).
# ===========================================================================
run("reset")                     # end Part B's task; docs remain, marker cleared
OVERVIEW = TMP / "docs" / "OVERVIEW.md"
OVERVIEW.write_text(
    "# Overview\n\n## Current status\n\n<!-- WF:anchor:current-status -->\n\n(seed)\n", encoding="utf-8")


def publish_a_need(title, prose):
    run("start", title)
    draft("need", "# need for " + title + "\nunder attack.\n")
    settle("need")
    entry(prose)
    rc, out = run("publish", "need")
    assert rc == 0, "publish need (" + title + "): " + out
    run("reset")                 # close this task so the next `start` succeeds


publish_a_need("task-one", "**2026-07-01** - FIRST task's settled Need.\n")
publish_a_need("task-two", "**2026-07-02** - SECOND task's settled Need.\n")
doc = OVERVIEW.read_text(encoding="utf-8")
n_blocks = len(re.findall(r"(?m)^<!-- WF:need:[a-z0-9-]+:start -->$", doc))
check("C1 two separate tasks BOTH accumulate under the shared anchor (no clobber)",
      "FIRST task's settled Need" in doc and "SECOND task's settled Need" in doc and n_blocks == 2)
check("C2 newest task is prepended above the older one (newest-first)",
      doc.index("SECOND task's settled Need") < doc.index("FIRST task's settled Need"))

# ===========================================================================
# Part D - full walk to Judgment (publishes to OVERVIEW, interleaving with this task's OWN
# Need block) and Shipping (record-only terminal). This is proof #4 for the last two rows.
# ===========================================================================
OVERVIEW.write_text(
    "# Overview\n\n## Current status\n\n<!-- WF:anchor:current-status -->\n\n(seed)\n", encoding="utf-8")
run("start", "modes-walk")

# Need: settle + publish its block, then advance on the fresh receipt.
draft("need", "# need\nthe need under attack.\n")
settle("need")
entry("**2026** - NEED settled for the walk.\n")
run("publish", "need")
run("advance")                                     # need -> design

# Design: settle + publish to DECISIONS (log mode, a DIFFERENT target/anchor than Need's).
DECISIONS = TMP / "docs" / "DECISIONS.md"
DECISIONS.write_text("# Decisions\n\n<!-- WF:anchor:decisions-log -->\n\n(older decisions)\n", encoding="utf-8")
draft("design", "# design\nthe approach under attack.\n")
settle("design")
entry("**2026** - DESIGN settled for the walk.\n")
rc, out = run("publish", "design")
dec = DECISIONS.read_text(encoding="utf-8")
check("D0 design publishes to DECISIONS under its own anchor (log, distinct target)",
      rc == 0 and "DESIGN settled for the walk" in dec
      and dec.index("DESIGN settled for the walk") > dec.index("<!-- WF:anchor:decisions-log -->"))
rc, out = run("advance")                            # design -> architecture
check("D0b advance opens off design on its fresh receipt (design -> architecture)",
      rc == 0 and load_marker()["current_step"] == "architecture")

# March through architecture/implementation - section mode is proven in Part B, so force past.
run("advance", "--force")                          # architecture -> implementation
run("advance", "--force")                          # implementation -> judgment

# Judgment: settle + publish the verdict to OVERVIEW. It must land under the SAME anchor as
# Need, ABOVE the Need block (newest-first), with BOTH present - the shared-anchor interleave.
draft("judgment", "# judgment\nthe verdict under attack.\n")
settle("judgment")
entry("**2026** - JUDGMENT verdict for the walk: it meets the Need.\n")
rc, out = run("publish", "judgment")
doc = OVERVIEW.read_text(encoding="utf-8")
check("D1 judgment publishes its verdict to OVERVIEW (log mode)",
      rc == 0 and "JUDGMENT verdict for the walk" in doc)
check("D2 need and judgment BOTH live under one OVERVIEW anchor, judgment newest",
      "NEED settled for the walk" in doc and "JUDGMENT verdict for the walk" in doc
      and doc.index("JUDGMENT verdict for the walk") < doc.index("NEED settled for the walk"))
rc, out = run("advance")                            # judgment -> shipping
check("D2b advance opens off judgment on its fresh receipt (judgment -> shipping)",
      rc == 0 and load_marker()["current_step"] == "shipping")

# Shipping: terminal. It settles via record (earns a receipt) but publishes NOTHING and has
# nowhere to advance to (proof #4 amendment: Shipping proves through `record` only).
draft("shipping", "# shipping\nreal-world readiness under attack.\n")
settle("shipping")
check("D3 shipping earns a fresh receipt via record (the terminal step's proof)",
      receipt_state("shipping") == "fresh")
rc, out = run("advance")
check("D4 shipping is terminal - nothing to advance to", rc != 0 and "last step" in out.lower())

shutil.rmtree(TMP, ignore_errors=True)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
