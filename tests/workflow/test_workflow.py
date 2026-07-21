#!/usr/bin/env python3
"""Direct-invocation test for the deterministic verb chain (exercised on the Need step).

Proves the deterministic chain by running the REAL CLI as a subprocess - exactly how
Claude Code / the developer would call it - and checking exit codes + resulting state
after each move. It also imports the shared receipt_state() to confirm the status line
and hooks (M5) would see the same truth.

It deploys the bundle the way it actually ships: copy workflow.py + rulebook.md together
into a fresh temp project, so the test exercises the COPIED shape, not the repo source.
"""
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "claude" / "workflow"
TMP = Path(tempfile.mkdtemp(prefix="wf_test_"))

shutil.copy(SRC / "workflow.py", TMP / "workflow.py")
shutil.copy(SRC / "rulebook.md", TMP / "rulebook.md")
(TMP / "docs").mkdir()
(TMP / ".workflow").mkdir()   # D-10: drafts + task state live here now; create before any draft write
(TMP / ".git").mkdir()        # D-2a: `start` roots the task at the nearest .git ancestor - give it one

sys.path.insert(0, str(TMP))
import workflow  # noqa: E402  (import after path insert + copy so `import workflow` finds the copy)

# Aim every in-process reader at THIS test's project root (root=TMP), exactly as the M5 status
# line and nudge pass the platform-handed root. The suite must never rely on the process cwd for
# aiming - that is the D-3 catastrophe the subprocess `cwd=` below guards against. (A qualified
# `workflow.load_marker` resolves on the module, never to these local wrappers, so there is no
# recursion to guard against.)
def load_marker():
    return workflow.load_marker(root=TMP)


def receipt_state(step):
    return workflow.receipt_state(step, root=TMP)


WF = TMP / ".workflow"
NEED = WF / "draft-need.md"                     # the step's draft = draft_path(TMP, "need") (D-10: in .workflow/)
OPERATOR = TMP / "docs" / "OPERATOR.md"
RULEBOOK = TMP / "rulebook.md"
CONTEXT = WF / "context.md"
CHALLENGE = WF / "challenge.md"

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def run(*args):
    # cwd=TMP so the subprocess (which resolves its root by walking UP from cwd) roots at THIS
    # test's project, never the real repo above it - the D-3/D-10 guard (Architecture Section 2).
    p = subprocess.run([sys.executable, str(TMP / "workflow.py"), *args],
                       capture_output=True, text=True, cwd=str(TMP))
    return p.returncode, p.stdout, p.stderr


def canary_in_context():
    text = CONTEXT.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "CANARY (echo this token" in line:
            return line.split(":", 1)[1].strip()
    return None


def write_challenge(canary):
    CHALLENGE.write_text("## COLD verdict\nAttacked it. token: {}\n\n## WARM verdict\nok\n".format(canary),
                         encoding="utf-8")


def write_need(body="the toy need under attack."):
    NEED.write_text("# Need draft\nNEED-DRAFT-MARKER: {}\n".format(body), encoding="utf-8")


# A. status with no task -> inert, exit 0
rc, out, _ = run("status")
check("A no-task status is inert, exit 0", rc == 0 and "no task open" in out)

# B. start -> exit 0, marker at need
rc, out, _ = run("start", "Toy need task")
check("B start succeeds at step need", rc == 0 and load_marker()["current_step"] == "need")

# C. start again -> refuse to clobber
rc, _, err = run("start", "Another")
check("C second start refuses (no clobber)", rc == 1 and "already open" in err)

# UNIT. an unknown recipe source token raises loudly (the guard is real, not just a comment)
raised = False
try:
    workflow._resolve_sources(["bogus_token"], "need", TMP)
except KeyError:
    raised = True
check("U _resolve_sources raises on an unknown token", raised)

# PRE-1. prepare with NO draft present -> fail closed (can't challenge nothing)
OPERATOR.write_text("# Operator\nOPERATOR-MARKER: how the developer actually works.\n", encoding="utf-8")
rc, _, err = run("prepare", "need")
check("P1 prepare refuses when the draft is missing", rc == 1 and "no proposal" in err.lower())

# PRE-2. prepare with NO rulebook -> fail closed (A-1 guarantee: rules must be present)
write_need()
RULEBOOK.unlink()
rc, _, err = run("prepare", "need")
check("P2 prepare refuses when the rulebook is missing (A-1)", rc == 1 and "rulebook" in err.lower())
shutil.copy(SRC / "rulebook.md", RULEBOOK)   # restore

# D. advance with no receipt -> gate refuses, still at need
rc, _, err = run("advance")
check("D gate refuses advance without receipt", rc == 1 and load_marker()["current_step"] == "need")

# E. prepare builds the alpha-1 bundle (rulebook header + ordered COLD/WARM + canary)
rc, out, _ = run("prepare", "need")
c1 = canary_in_context()
ctx = CONTEXT.read_text(encoding="utf-8")
header_first = "The challenger's rulebook" in ctx and ctx.index("The challenger's rulebook") < ctx.index("# Challenge for step")
i_cold = ctx.find("===== COLD")
i_artifact = ctx.find("NEED-DRAFT-MARKER")
i_canary = ctx.find("CANARY (echo")
i_warm = ctx.find("===== WARM")
i_operator = ctx.find("OPERATOR-MARKER")
ordered = -1 < i_cold < i_artifact < i_canary < i_warm < i_operator
check("E prepare plants canary + sets pending",
      rc == 0 and c1 and load_marker()["pending"]["canary"] == c1)
check("E bundle carries the rulebook as a framing header (A-1)", header_first)
check("E bundle is ordered COLD(artifact+canary) -> WARM(operator) (alpha-1)", ordered)

# F. record with NO challenge file -> fail closed, no receipt
rc, _, err = run("record", "need")
check("F record fail-closed on missing result",
      rc == 1 and "no receipt written" in err.lower() and "need" not in load_marker().get("receipts", {}))

# G. result echoes WRONG canary -> fail closed
write_challenge("WF-CANARY-deadbeefdeadbeef")
rc, _, err = run("record", "need")
check("G record fail-closed on wrong canary",
      rc == 1 and "canary" in err.lower() and "need" not in load_marker().get("receipts", {}))

# H. correct canary BUT artifact missing -> fail closed (unreadable artifact)
write_challenge(c1)
NEED.unlink()
rc, _, err = run("record", "need")
check("H record fail-closed on unreadable artifact",
      rc == 1 and "unreadable" in err.lower() and "need" not in load_marker().get("receipts", {}))

# I. recreate the SAME artifact; correct canary -> success (live hash matches prepare snapshot)
write_need()
rc, out, _ = run("record", "need")
check("I record succeeds with artifact + correct canary",
      rc == 0 and load_marker()["receipts"]["need"]["challenge_ran"] is True)

# J. shared truth function agrees: fresh
check("J receipt_state(need) == fresh", receipt_state("need") == "fresh")

# J2. M7 (R-2): the receipt must NOT carry `context_hash`. That field hashed a bundle
#     containing the RANDOM canary, so it was unreproducible and reader-less; M7 deletes it
#     (Component C). We assert field-ABSENCE on a LIVE receipt because "gates behave" (tests
#     I/J) proves behaviour, not that the field is gone (Design proof bar: "written nowhere").
#     RED until Component C removes the receipt copy in cmd_record.
check("J2 receipt carries no context_hash (R-2 field deleted)",
      "context_hash" not in load_marker()["receipts"]["need"])

# K-N. multi-round: a revision stales the receipt and BLOCKS advance until re-challenged (proof #1),
#      and the TOCTOU guard refuses a record whose artifact changed after prepare.
write_need("REVISED between rounds.")
check("K a revision flips fresh -> stale", receipt_state("need") == "stale")

rc, _, err = run("advance")
check("L gate BLOCKS advance while stale",
      rc == 1 and load_marker()["current_step"] == "need")

rc, _, _ = run("prepare", "need")                 # round 2: snapshot the revised draft
c2 = canary_in_context()
write_challenge(c2)
write_need("CHANGED AGAIN after prepare.")        # edit AFTER prepare, BEFORE record
rc, _, err = run("record", "need")
check("M TOCTOU: record refuses when the draft changed after prepare",
      rc == 1 and "changed between prepare and record" in err.lower()
      and receipt_state("need") == "stale")

rc, _, _ = run("prepare", "need")                 # honest re-challenge over the current bytes
c3 = canary_in_context()
check("M2 re-prepare mints a fresh canary each round", c3 and c3 not in (c1, c2))
write_challenge(c3)
rc, _, _ = run("record", "need")
check("M3 re-record makes it fresh again", receipt_state("need") == "fresh")

rc, out, _ = run("advance")
check("N gate OPENS on the fresh re-challenge (need -> design)",
      rc == 0 and load_marker()["current_step"] == "design")

# O. force-advancing a never-challenged step records the override AND reads honestly 'missing'
rc, out, _ = run("advance", "--force")            # design (has a recipe in M4, but was never challenged) -> architecture
m = load_marker()
check("O --force records the override + moves on (design -> architecture)",
      rc == 0 and m["current_step"] == "architecture" and m["receipts"]["design"].get("override") is True)
check("O2 overridden-never-challenged step reads 'missing', not 'stale'",
      receipt_state("design") == "missing")

# P. reset clears state -> inert again
rc, _, _ = run("reset")
check("P reset clears state", rc == 0 and load_marker() is None)

# Q. a non-ASCII title does not crash start/status (Windows cp1252 arrow), and start is consistent
rc, out, _ = run("start", "Need → Design workflow")
started_ok = rc == 0 and load_marker() is not None and "→" in load_marker()["task_title"]
rc2, _, _ = run("status")
check("Q non-ASCII title: start exits 0 and status does not crash", started_ok and rc2 == 0)
run("reset")

# R. CB1 (correctness red-team): `record` clears any LEFTOVER drafted entry, so a stale entry
#    from a previous round can never publish under the next fresh receipt - the model must
#    draft a fresh one each settle. Here: plant an entry BEFORE record, then confirm record ate it.
ENTRY = WF / "publish-entry.md"
run("start", "CB1 entry-clear check")
write_need()
run("prepare", "need")
ENTRY.write_text("a leftover entry from a previous round.\n", encoding="utf-8")
write_challenge(canary_in_context())
rc, _, _ = run("record", "need")
check("R record clears a leftover entry (CB1: a fresh entry is required each settle)",
      rc == 0 and not ENTRY.exists())
run("reset")

# R2. CB1/B2 (convergence): if the leftover entry CANNOT be removed, `record` must fail CLOSED -
#     write NO receipt (so publish's gate refuses) rather than silently leave a stale entry.
#     Simulate an undeletable entry portably by making its path a DIRECTORY (unlink -> OSError).
run("start", "CB1 fail-closed check")
write_need()
run("prepare", "need")
ENTRY.mkdir()                                   # ENTRY path is now a dir -> unlink() raises OSError
write_challenge(canary_in_context())
rc, _, err = run("record", "need")
check("R2 record fails closed when a leftover entry cannot be cleared (no receipt written)",
      rc != 0 and receipt_state("need") == "missing")
ENTRY.rmdir()                                   # clean up the simulated lock
run("reset")

# S. L2 (live smoke-test): `prepare` clears the PREVIOUS round's challenger result. The
#    challenger is told to WRITE challenge.md, so it reads whatever sits there first - two live
#    challengers did exactly that and fed the prior round's findings back as "corroboration".
#    A stale result can never earn a receipt (the canary check catches it), so this is about
#    the challenger's INDEPENDENCE, not the receipt's integrity.
run("start", "L2 challenge-clear check")
write_need()
CHALLENGE.parent.mkdir(exist_ok=True)
CHALLENGE.write_text("PRIOR ROUND'S VERDICT - must not survive into the next round.\n",
                     encoding="utf-8")
rc, _, _ = run("prepare", "need")
check("S prepare clears the previous round's challenge result (L2: challenger independence)",
      rc == 0 and not CHALLENGE.exists())
run("reset")

# S2. L2 fail-closed: if the stale result CANNOT be removed, prepare must write NO bundle and
#     plant NO pending - handing over a clean bundle is prepare's whole job, so a directory it
#     cannot clean means nothing is prepared. Same portable trick as R2: make the path a dir.
run("start", "L2 fail-closed check")
write_need()
CONTEXT.unlink(missing_ok=True)                 # so "no bundle written" is a real assertion
CHALLENGE.parent.mkdir(exist_ok=True)
CHALLENGE.mkdir()                               # CHALLENGE path is now a dir -> unlink() raises OSError
rc, _, err = run("prepare", "need")
check("S2 prepare fails closed when the stale result cannot be cleared (nothing prepared)",
      rc != 0 and load_marker()["pending"] is None and not CONTEXT.exists())
CHALLENGE.rmdir()                               # clean up the simulated lock
run("reset")

# S3. L2 ordering: the clear sits AFTER every validation check, so a REFUSED prepare must not
#     have the side effect of destroying the previous round's result. Refuse via the missing
#     draft (P1's path) and confirm the earlier result is still on disk, byte-intact.
run("start", "L2 refusal-has-no-side-effect check")
write_need()
CHALLENGE.parent.mkdir(exist_ok=True)
prior = "PRIOR ROUND'S VERDICT - a refused prepare must leave this alone.\n"
CHALLENGE.write_text(prior, encoding="utf-8")
NEED.unlink()                                   # now prepare refuses at the "no proposal" gate
rc, _, err = run("prepare", "need")
check("S3 a REFUSED prepare does not destroy the previous challenge result",
      rc != 0 and CHALLENGE.exists() and CHALLENGE.read_text(encoding="utf-8") == prior)
run("reset")

# ============================================================================
# M7 (R-1): the challenger-facing honesty block - present, consistent, over-claims gone.
# ----------------------------------------------------------------------------
# STATIC-TEXT assertions: they read the shipped payload files DIRECTLY (repo SRC /
# CHALLENGER_SRC), not the copied temp project. M7 asks "does the text we SHIP carry the
# honest block and not the old lie" - and the operator installs from repo, so repo source
# IS the deployed copy. A deliberate departure from this suite's copied-shape idiom (module
# docstring), correct for a text-content guard. No temp project / subprocess / marker needed.
# ============================================================================
RULEBOOK_SRC = SRC / "rulebook.md"                        # claude/workflow/rulebook.md (bundle header)
CHALLENGER_SRC = SRC.parent / "agents" / "challenger.md"  # claude/agents/challenger.md (ships to every project)


def _norm(text):
    """Normalize markdown prose so a blockquote copy and a plain-prose copy of the SAME words
    compare equal. The block ships `> `-quoted in the rulebook header but as bare prose in
    challenger.md, wrapped differently in each - so three reductions strip everything BUT the
    words: (1) drop `**bold**` markers (emphasis is review-checked, not test-backed); (2) strip
    a leading blockquote marker per line - `> ` OR a bare `>` on a blank quote line (no trailing
    space, else an all-`>` line leaks in); (3) collapse every whitespace run (incl. the newlines
    from wrapping) to one space. What remains is only the WORDS - which is exactly what "the two
    shipped copies can never drift" means. `split()`+`join()` does the collapse+trim, no regex."""
    text = text.replace("**", "")
    out = []
    for ln in text.splitlines():
        s = ln.lstrip()
        if s.startswith(">"):          # a blockquote line: drop the `>` and one OPTIONAL space
            s = s[1:]
            if s.startswith(" "):
                s = s[1:]
        out.append(s)
    return " ".join(" ".join(out).split())


# The canonical block - authored ONCE here and asserted equal at both shipped sites, so the two
# copies cannot drift (Component E). Bold kept so a human reading the test sees the real doctrine;
# _norm() strips the ** on BOTH sides of every comparison, so it is the words that are guarded.
CANON = (
    "You start isolated — no main chat, none of the builder's private reasoning — and that "
    "isolation is your fresh eyes. Judge the cold section on its own written record; bring in "
    "no outside facts to fill it. You are **not** a blank slate, though: hold any operator "
    "**memory** you carry — habits, preferences, **or facts** from the memory index — for the "
    "warm pass, and apply the operator's methodology **core** or project instructions, to the "
    "extent you carry them, as the **standard you measure that record against** — never as more "
    "evidence, and never as the thing under judgement. Your **attack rules are this bundle**, "
    "not anything injected."
)

_rulebook_n = _norm(RULEBOOK_SRC.read_text(encoding="utf-8"))
_challenger_n = _norm(CHALLENGER_SRC.read_text(encoding="utf-8"))
_union_n = _rulebook_n + " " + _challenger_n     # union: a re-introduction in EITHER file is caught
_canon_n = _norm(CANON)

# Presence: three load-bearing anchors - the isolation opening, the hold-memory clause, and the
# directive - each present in BOTH shipped copies. Anchors the block's two ends + its directive
# (not the connective middle - named honestly, Design R11-min). Guards removal/gutting.
_anchors = [
    "no main chat, none of the builder's private reasoning",   # isolation opening
    "hold any operator memory you carry",                      # hold-memory clause (** stripped)
    "attack rules are this bundle",                            # directive (** stripped)
]
check("M7-Presence: block anchors present in rulebook.md",
      all(a in _rulebook_n for a in _anchors))
check("M7-Presence: block anchors present in challenger.md",
      all(a in _challenger_n for a in _anchors))

# Equality: the WHOLE canonical block is a substring of EACH normalized copy - so a hand-edit to
# one file that keeps the anchors but drifts the middle reddens the suite. Robust to the `> `
# prefixes and to benign reflow (the point of _norm), unlike the infeasible byte-identity rule.
check("M7-Equality: canonical block matches rulebook.md (normalized)", _canon_n in _rulebook_n)
check("M7-Equality: canonical block matches challenger.md (normalized)", _canon_n in _challenger_n)

# Absence: the EXACT over-claims M7 deletes, each absent from the UNION of the two challenger-
# facing files. A closed, finite regression guard on the strings the milestone actually re-added
# 3+ times - NOT the forbidden open blacklist (every conceivable over-claim). RED until A lands.
_deleted = [
    "the bundle is all you get",          # A1, rulebook.md:8
    "the ONLY thing you know",            # A2, challenger.md:8
    "uncontaminated by operator habits",  # A4, challenger.md:27
    "a COLD read of just",                # A3, rulebook.md rule 6 (COLD ** stripped)
    "see only the thing being judged",    # A3, rulebook.md rule 6
]
check("M7-Absence: deleted over-claims gone from the challenger-facing files",
      not any(s in _union_n for s in _deleted))

# Absence (workflow.py): the developer-facing "a force is deferred/coming" staleness (Axis 2).
# The phrase is line-WRAPPED in the cmd_prepare docstring ("deferred\nto M4"), so a raw single-
# line grep MISSES it - _norm collapses the wrap. RED until Component B rewrites the docstring;
# that rewrite must NOT quote the phrase back, or it re-reddens this very check (change-map trap).
_workflow_n = _norm((SRC / "workflow.py").read_text(encoding="utf-8"))
check("M7-Absence: 'forcing is deferred to M4' gone from workflow.py",
      "forcing is deferred to M4" not in _workflow_n)

# A2-seam guard: Equality/Presence are SUBSTRING matches, so none of them catches a botched A2
# removal that strands the `:7` "You" and ships "...the fix. You You start isolated...". This
# mechanical check fails that ships-everywhere seam instead of leaving it to a human eyeball (M7's
# own theme - stop relying on the glance). Green now (no doubling); stays green iff A2 is clean.
check("M7-Seam: no doubled 'You You' at the A2 splice in challenger.md",
      "You You" not in _challenger_n)

shutil.rmtree(TMP, ignore_errors=True)

passed = sum(1 for _, ok in checks if ok)
total = len(checks)
print("\n{}/{} checks passed.".format(passed, total))
sys.exit(0 if passed == total else 1)
