#!/usr/bin/env python3
"""init-project-docs scaffolds VALID publish targets - proven by simulating a publish into the
skill's own OVERVIEW / DECISIONS / ARCHITECTURE skeletons.

The six-step workflow's `publish` engine (_place_block) REFUSES any doc that lacks the seeded
`<!-- WF:anchor:<slug> -->` comment. So a repo scaffolded by init-project-docs can only let "the
docs write themselves" if that skill seeds the anchors. This suite lifts the three skeletons
straight out of the skill file and simulates each doc's first publish in memory (a pure function -
it writes nothing), catching any future edit that drops, duplicates, or code-fences an anchor.

Sibling of test_seed_docs.py, which proves the same for THIS repo's already-seeded real docs. The
`/start-task` bootstrap relies on this contract: it scaffolds a fresh repo with init-project-docs,
then the workflow publishes into what was scaffolded.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "claude" / "workflow"))
import workflow as wf  # noqa: E402  (the deployed publish engine; imported, __main__ not run)

SKILL = (REPO / "claude" / "skills" / "init-project-docs" / "SKILL.md").read_text(encoding="utf-8")

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def skeleton(doc_name):
    """Pull the first ```-fenced template that follows the '### docs/<doc_name>' heading - i.e. the
    exact bytes init-project-docs writes for that doc (the fences are SKILL.md formatting, stripped
    here so what remains is the scaffolded file's real content)."""
    i = SKILL.index("### docs/{}".format(doc_name))
    open_fence = SKILL.index("```", i)
    body_start = SKILL.index("\n", open_fence) + 1     # content begins after the opening ``` line
    close_fence = SKILL.index("```", body_start)       # ...and ends at the closing fence
    return SKILL[body_start:close_fence]


# (doc, block_key, scope, anchor_slug, placement) - one row per review-style publish target.
CASES = [
    ("OVERVIEW.md", "need", "task0001", "current-status", "prepend"),
    ("DECISIONS.md", "design", "task0002", "decisions-log", "prepend"),
    ("ARCHITECTURE.md", "arch", "renderer", "architecture-sections", "append_section"),
]

for doc_name, key, scope, anchor, placement in CASES:
    sk = skeleton(doc_name)
    anchor_tag = "<!-- WF:anchor:{} -->".format(anchor)
    check("{} skeleton seeds exactly one {} anchor".format(doc_name, anchor),
          sk.count(anchor_tag) == 1)
    check("{} skeleton has no WF marker inside a code fence".format(doc_name),
          not wf._wf_marker_in_fence(sk))
    sim = wf._place_block(sk, key, scope, anchor, placement, "SIMULATED " + key.upper())
    start = "<!-- WF:{}:{}:start -->".format(key, scope)
    check("{} scaffolded doc accepts a {} publish, placed under the anchor".format(doc_name, key),
          start in sim and ("SIMULATED " + key.upper()) in sim
          and sim.index(anchor_tag) < sim.index(start))

# Negative control: strip the anchor and confirm publish REFUSES - so the check above is really
# testing the anchor's presence, not passing for some unrelated reason (the fix is load-bearing).
ov_no_anchor = skeleton("OVERVIEW.md").replace("<!-- WF:anchor:current-status -->", "")
try:
    wf._place_block(ov_no_anchor, "need", "task0001", "current-status", "prepend", "x")
    check("OVERVIEW without its anchor is refused (fix is load-bearing)", False)
except Exception as exc:
    check("OVERVIEW without its anchor is refused (fix is load-bearing)", "anchor" in str(exc).lower())

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
