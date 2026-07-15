#!/usr/bin/env python3
"""The SEEDED real docs are valid publish targets - proven read-only, WITHOUT mutating them.

Unlike the other suites (which run against synthetic temp fixtures that merely match the real
docs' shape), this one reads the ACTUAL committed `docs/OVERVIEW.md`, `docs/DECISIONS.md`, and
`docs/ARCHITECTURE.md`, and simulates each doc's future publish in memory. `_place_block` is a
pure function (returns a string, writes nothing), so the simulation proves the seeding is correct
AND leaves every real byte untouched - the "proven on real docs, read-only, no mutation" claim,
made reproducible and preserved (methodology T1) instead of an ad-hoc scratchpad check.

If any anchor is missing/duplicated, a fence is present, or the ARCHITECTURE wrap is malformed,
`_place_block` raises `_PublishError` (or a count assertion fails) and this suite goes red - so a
future hand-edit that breaks a real doc as a publish target is caught here.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "claude" / "workflow"))
import workflow as wf  # noqa: E402

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def read(rel):
    return (REPO / rel).read_text(encoding="utf-8")


# Snapshot all three real docs' RAW BYTES up front, so the "unchanged" check at the end is a true
# byte-for-byte comparison (not just "no WF:need substring"). Every simulation below is a pure
# in-memory _place_block call; this catches any accidental real write a future edit might introduce.
_SNAP = {rel: (REPO / rel).read_bytes()
         for rel in ("docs/OVERVIEW.md", "docs/DECISIONS.md", "docs/ARCHITECTURE.md")}

# --- OVERVIEW: log-accumulate target (need + judgment share current-status) ---
ov = read("docs/OVERVIEW.md")
check("OVERVIEW has exactly one current-status anchor", ov.count("<!-- WF:anchor:current-status -->") == 1)
check("OVERVIEW has no WF marker inside a code fence", not wf._wf_marker_in_fence(ov))
sim = wf._place_block(ov, "need", "task0001", "current-status", "prepend", "SIMULATED NEED ENTRY")
check("OVERVIEW simulated need publish inserts under the anchor, newest-first",
      "<!-- WF:need:task0001:start -->" in sim and "SIMULATED NEED ENTRY" in sim
      and sim.index("SIMULATED NEED ENTRY") > sim.index("<!-- WF:anchor:current-status -->")
      and sim.index("SIMULATED NEED ENTRY") < sim.index("Step 4 (Implementation)"))   # above existing content
check("OVERVIEW existing hand-written entries are untouched by the sim",
      "Step 4 (Implementation)" in sim and "Step 3 (Architecture) settled" in sim)

# --- DECISIONS: log-accumulate target (design decisions) ---
de = read("docs/DECISIONS.md")
check("DECISIONS has exactly one decisions-log anchor", de.count("<!-- WF:anchor:decisions-log -->") == 1)
check("DECISIONS has no WF marker inside a code fence", not wf._wf_marker_in_fence(de))
simd = wf._place_block(de, "design", "task0002", "decisions-log", "prepend", "SIMULATED DESIGN DECISION")
check("DECISIONS simulated design publish inserts under the anchor, above the newest dated entry",
      "SIMULATED DESIGN DECISION" in simd
      and simd.index("SIMULATED DESIGN DECISION") > simd.index("<!-- WF:anchor:decisions-log -->")
      and simd.index("SIMULATED DESIGN DECISION") < simd.index("Step 4 (Implementation) settled"))

# --- ARCHITECTURE: sectioned target; the existing body is wrapped once as workflow-machinery ---
ar = read("docs/ARCHITECTURE.md")
check("ARCHITECTURE has exactly one architecture-sections anchor",
      ar.count("<!-- WF:anchor:architecture-sections -->") == 1)
check("ARCHITECTURE wraps the existing body once as workflow-machinery (start+end, one each)",
      ar.count("<!-- WF:arch:workflow-machinery:start -->") == 1
      and ar.count("<!-- WF:arch:workflow-machinery:end -->") == 1)
check("ARCHITECTURE has no WF marker inside a code fence", not wf._wf_marker_in_fence(ar))
i_start = ar.index("<!-- WF:arch:workflow-machinery:start -->")
i_end = ar.index("<!-- WF:arch:workflow-machinery:end -->")
check("ARCHITECTURE wrap is well-formed (start before end; M2 + M4 narrative inside)",
      i_start < ar.index("The one principle that shapes everything below") < i_end
      and i_start < ar.index("Built + hardened at Step 4") < i_end)
# --update the existing section: replace-in-place, still exactly one workflow-machinery block
sim_upd = wf._place_block(ar, "arch", "workflow-machinery", "architecture-sections", "append_section", "REPLACED BODY")
check("ARCHITECTURE --update workflow-machinery replaces in place (still one block)",
      sim_upd.count("<!-- WF:arch:workflow-machinery:start -->") == 1 and "REPLACED BODY" in sim_upd)
# --new a fresh section: appends AFTER workflow-machinery's end (stable order)
sim_new = wf._place_block(ar, "arch", "new-component", "architecture-sections", "append_section", "NEW SECTION BODY")
check("ARCHITECTURE --new section appends after the wrapped section (stable order)",
      "<!-- WF:arch:new-component:start -->" in sim_new
      and sim_new.index("NEW SECTION BODY") > sim_new.index("<!-- WF:arch:workflow-machinery:end -->"))

# --- the M3 superseded banner is present (the doc-reconciliation decision) ---
check("ARCHITECTURE M3 subsection carries the 'Superseded by ... M4' banner", 'Superseded by "M4' in ar)

# --- the real files were NOT mutated: full byte-for-byte comparison against the snapshots ---
for _rel, _snap in _SNAP.items():
    check("real doc byte-for-byte unchanged: " + _rel, (REPO / _rel).read_bytes() == _snap)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
