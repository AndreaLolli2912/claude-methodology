#!/usr/bin/env python3
"""Shipped skill bodies contain NO unintended shell-execution triggers.

Claude Code executes any inline `` !`<cmd>` `` or fenced ```` ```! ```` block it finds in a skill body
at LOAD time - even inside an HTML comment. A stray one makes the whole skill fail with a permission
error before it does anything useful. This bit `/start-task` on first live use: an explanatory comment
literally contained the `!` + backtick example it was describing, and the harness tried to run it. A
static check catches this class where a live slash-command invocation (which the tests can't perform)
otherwise would - so a skill that only means to DESCRIBE the pattern can never accidentally FIRE it.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "claude" / "skills"

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# The two execution-trigger forms Claude Code recognizes in skill content. Intentionally strict:
# ANY exclaim-then-backtick, or a fenced block opened with `!`, would run at load time - so a skill
# must never contain either, not even as documentation (describe it in words instead).
INLINE = re.compile(r"!`")          # !`<command>`  -> runs inline at load time
FENCED = re.compile(r"```\s*!")     # ```! ... ```   -> runs the fenced block at load time

skill_files = sorted(SKILLS.rglob("SKILL.md"))
check("at least one shipped skill exists to check", len(skill_files) > 0)
for sk in skill_files:
    text = sk.read_text(encoding="utf-8")
    rel = sk.relative_to(REPO).as_posix()
    check("{}: no inline !`...` execution trigger".format(rel), INLINE.search(text) is None)
    check("{}: no fenced ```! execution trigger".format(rel), FENCED.search(text) is None)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
