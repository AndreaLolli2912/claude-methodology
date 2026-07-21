#!/usr/bin/env python3
"""Test sync.py's M6 directory-whitelist transport: the walk (`_bundle_files`), the two-response
coverage gate (`_definition_problems`), the `_copy` status return, `_live_orphans`, and the three
verbs (install / capture / status) under the SETTLED exit-code model (docs/DECISIONS.md 2026-07-17):

  * an OVER-inclusion (a stray top-level entry) HALTS install and deploys nothing;
  * an UNDER-inclusion (a named entry absent) does NOT halt — it ships the covered files, reports the
    missing one, and exits non-zero;
  * a live ORPHAN is INFORMATION at exit 0, never pulled (F2, no resurrection).

It also pins the four Implementation directives (M1 one shared owned-predicate; M3 capture honours
`_copy`'s "missing"; M4 install's footer carries the missing count; and the migration guard: the
walk of the real claude/ equals the old 13-file MANIFEST set).

Standalone script — run it DIRECTLY (`python tests/workflow/test_sync_bundle.py`), never under
pytest. Every scenario runs in throwaway temp dirs; the live ~/.claude is NEVER touched (we redirect
sync.BUNDLE_DIR / sync.TARGET_DIR at temp dirs, the same isolation trick test_sync.py uses for
settings.json).
"""
import io
import shutil
import sys
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
import sync  # noqa: E402

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# --- fixtures ------------------------------------------------------------------------------------
# The old MANIFEST's 13 files, frozen here as the migration baseline (proof 11). Once the walk is
# proven equal to this set, the per-file list is safe to delete — which it now is.
OLD_MANIFEST_13 = {
    "CLAUDE.md", "METHODOLOGY.md", "skills/init-project-docs/SKILL.md", "VERSION",
    "CHANGELOG.md", "hooks/check_version.py", "statusline.py", "workflow/workflow.py",
    "workflow/rulebook.md", "workflow/conductor.md", "agents/challenger.md",
    "workflow/nudge.py", "statusline_wf.py",
}


def _fresh():
    """A fresh (repo, live) pair of temp dirs, with sync redirected to point at them. The verbs read
    the module globals BUNDLE_DIR / TARGET_DIR, so these two assignments isolate the whole test."""
    base = Path(tempfile.mkdtemp(prefix="wf_bundle_")).resolve()
    repo, live = base / "claude", base / "live"
    repo.mkdir()
    live.mkdir()
    sync.BUNDLE_DIR = repo
    sync.TARGET_DIR = live
    return repo, live


def _seed(repo):
    """Write a minimal VALID bundle into `repo`: the six named root files + one file inside each of
    the four named dirs (10 files total). Every scenario starts from this and mutates it."""
    for name in sync.BUNDLE_ROOT_FILES:
        (repo / name).write_text(name + " v1", encoding="utf-8")
    (repo / "skills" / "init-project-docs").mkdir(parents=True)
    (repo / "skills" / "init-project-docs" / "SKILL.md").write_text("skill", encoding="utf-8")
    (repo / "agents").mkdir()
    (repo / "agents" / "challenger.md").write_text("agent", encoding="utf-8")
    (repo / "hooks").mkdir()
    (repo / "hooks" / "check_version.py").write_text("hook", encoding="utf-8")
    (repo / "workflow").mkdir()
    (repo / "workflow" / "workflow.py").write_text("spine", encoding="utf-8")


def _run(fn, *args, **kwargs):
    """Call a sync verb, capturing (returncode, stdout, stderr) so we can assert on both text and code."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = fn(*args, **kwargs)
    return rc, out.getvalue(), err.getvalue()


# --- Proof 1: a file inside a named dir auto-ships, with no code change (closes RISKS #8) ---------
repo, live = _fresh()
_seed(repo)
(repo / "skills" / "new.md").write_text("brand new", encoding="utf-8")   # never named anywhere
rc, out, err = _run(sync.install)
check("1 a file dropped into a named dir auto-ships (no code change)",
      rc == 0 and (live / "skills" / "new.md").read_text(encoding="utf-8") == "brand new")

# --- Proof 2: over-inclusion (a stray) HALTS install and deploys NOTHING --------------------------
repo, live = _fresh()
_seed(repo)
(repo / "notes.md").write_text("stray file", encoding="utf-8")
(repo / "prompts").mkdir()
(repo / "prompts" / "x.md").write_text("stray dir", encoding="utf-8")
rc, out, err = _run(sync.install)
check("2a a stray top-level entry halts install (exit non-zero)", rc != 0)
check("2b the halt deploys NOTHING (target is still empty)", not any(live.iterdir()))
check("2c both strays are named in the report", "notes.md" in err and "prompts" in err)

# --- Proof 3: under-inclusion (a missing named entry) does NOT halt — ships rest, exits non-zero --
# This is the CORRECTED model (DECISIONS.md supersedes the draft's "missing halts"): the covered
# files still deploy, the absence is reported, and the run exits non-zero.
repo, live = _fresh()
_seed(repo)
(repo / "VERSION").unlink()                                             # a named root file goes missing
rc, out, err = _run(sync.install)
check("3a a missing named entry does NOT halt — the covered files still ship", (live / "CLAUDE.md").exists())
check("3b a missing named entry exits non-zero", rc != 0)
check("3c the missing entry is reported", "VERSION" in err)
repo, live = _fresh()
_seed(repo)
shutil.rmtree(repo / "agents")                                          # a named dir goes missing
rc, out, err = _run(sync.install)
check("3d a missing named dir reports + exits non-zero, still ships the rest",
      rc != 0 and "agents" in err and (live / "CLAUDE.md").exists())

# --- Proof 4: ignore beats ship — junk never ships and is counted as skipped ----------------------
repo, live = _fresh()
_seed(repo)
(repo / "workflow" / "__pycache__").mkdir()
(repo / "workflow" / "__pycache__" / "x.pyc").write_text("junk", encoding="utf-8")
(repo / "workflow" / "old.bak").write_text("backup junk", encoding="utf-8")
ship, skipped = sync._bundle_files(repo)
shipset = {p.as_posix() for p in ship}
check("4a __pycache__/*.pyc never ships", "workflow/__pycache__/x.pyc" not in shipset)
check("4b *.bak never ships", "workflow/old.bak" not in shipset)
check("4c junk inside a named dir is counted as skipped, not shipped", skipped == 2)
rc, out, err = _run(sync.install)
check("4d junk is not written to the target", not (live / "workflow" / "old.bak").exists())

# --- Proof 5: no resurrection (F2) — a live orphan is reported, never pulled, exit 0 --------------
repo, live = _fresh()
_seed(repo)
_run(sync.install)                                                      # live now mirrors the repo
(live / "workflow" / "old.py").write_text("live only", encoding="utf-8")   # exists live, repo doesn't own it
rc, out, err = _run(sync.capture)
check("5a capture does NOT pull the orphan into the repo", not (repo / "workflow" / "old.py").exists())
check("5b capture reports the orphan (info on stdout)", "old.py" in out)
check("5c capture exits 0 despite the orphan (information, not an error)", rc == 0)

# --- Proof 6: plain-copy install works with no git in play ----------------------------------------
repo, live = _fresh()
_seed(repo)
check("6a the temp bundle has no .git (plain copy)", not (repo / ".git").exists())
rc, out, err = _run(sync.install)
check("6b plain-copy install deploys normally", rc == 0 and (live / "CLAUDE.md").exists())

# --- Proof 7: install ships working-tree bytes (A5) — edited-but-unstaged content lands ------------
repo, live = _fresh()
_seed(repo)
_run(sync.install)
(repo / "CLAUDE.md").write_text("EDITED BYTES", encoding="utf-8")       # edit on disk, no staging/commit
rc, out, err = _run(sync.install)
check("7 install ships working-tree bytes (edited, unstaged)",
      (live / "CLAUDE.md").read_text(encoding="utf-8") == "EDITED BYTES")

# --- Proof 8: the report is shipped / skipped / reported (F3), with real numbers -------------------
repo, live = _fresh()
_seed(repo)                                                            # 10 shippable files
(repo / "workflow" / "__pycache__").mkdir()
(repo / "workflow" / "__pycache__" / "a.pyc").write_text("j", encoding="utf-8")   # 1 junk file
rc, out, err = _run(sync.install)
check("8a footer counts shipped files (10)", "Shipped 10 file(s)" in out)
check("8b footer has the 'junk skipped' column (1)", "1 junk skipped" in out)
check("8c footer's reported column shows 0 missing on a clean bundle", "0 named entries missing" in out)
rc2, out2, err2 = _run(sync.install)                                   # second run: all replaced
check("8d a second install reports replacements (10 replaced)", "10 replaced" in out2)

# --- Proof 9: exit codes reach the shell THROUGH main() -------------------------------------------
repo, live = _fresh()
_seed(repo)
(repo / "stray.md").write_text("x", encoding="utf-8")
rc, out, err = _run(sync.main, ["install"])
check("9a main propagates install's non-zero on a stray", rc != 0)
repo, live = _fresh()
_seed(repo)
rc, out, err = _run(sync.main, ["install"])
check("9b main returns 0 on a clean install", rc == 0)
_run(sync.install)
(live / "hooks" / "foreign.py").write_text("orphan", encoding="utf-8")
rc, out, err = _run(sync.main, ["capture"])
check("9c main: capture exits 0 despite a live orphan (informational)", rc == 0)

# --- Proof 10: resolved roots print FIRST (the cwd-audit habit), even on the halt path -------------
repo, live = _fresh()
_seed(repo)
(repo / "stray.md").write_text("x", encoding="utf-8")
rc, out, err = _run(sync.install)                                     # halts on the stray
first = out.splitlines()[0]
check("10a install prints resolved roots as line 1 even on the halt path",
      str(repo) in first and str(live) in first)
repo, live = _fresh()
_seed(repo)
rc, out, err = _run(sync.capture)
first = out.splitlines()[0]
check("10b capture prints resolved roots as line 1", str(live) in first and str(repo) in first)

# --- Proof 11: migration equivalence — the walk of the REAL claude/ == the old 13-file MANIFEST ----
real_ship, _ = sync._bundle_files(REPO_ROOT / "claude")
# A SUBSET check, not ==: it guards that the migration never LOST one of the original 13 files, while
# allowing the feature under test (a file dropped into a named dir ships) — so a later bundle-file
# addition (e.g. M7 editing claude/workflow/) never false-fails this. The one-shot == baseline was
# verified at the switch; freezing == permanently would re-import the per-file burden M6 deleted.
check("11a the walk of the real claude/ still ships every one of the original 13 MANIFEST files",
      OLD_MANIFEST_13 <= {p.as_posix() for p in real_ship})
real_strays, real_missing = sync._definition_problems(REPO_ROOT / "claude")
check("11b the real claude/ has no coverage problems (no self-halt on first install)",
      real_strays == [] and real_missing == [])

# --- Proof 12: the shipped core carries the workflow start-trigger + how-to-run (Need proof 7) -----
core = (REPO_ROOT / "claude" / "CLAUDE.md").read_text(encoding="utf-8")
check("12a shipped core names the workflow start command", "workflow.py start" in core)
check("12b shipped core mentions the six-step workflow", "six-step" in core.lower())

# --- Proof 13: status fires the two DISTINCT advisories (M2) + the informational orphan line -------
# Stub _git_status so the readout is hermetic (no real git/network).
_saved_git = sync._git_status
sync._git_status = lambda: {"kind": "ok", "uncommitted": 0, "reached": True, "ahead": 0, "behind": 0}
repo, live = _fresh()
_seed(repo)
_run(sync.install)                                                    # live matches repo
(repo / "stray.md").write_text("x", encoding="utf-8")                 # a coverage gap (over-inclusion)
(live / "agents" / "foreign.md").write_text("orphan", encoding="utf-8")   # a live orphan
rc, out, err = _run(sync.status)
check("13a status previews a stray as a HALT", "HALT" in out)
check("13b status prints the live orphan (informational)", "not in the bundle" in out)
check("13c status returns non-zero when there's a coverage problem", rc != 0)
repo, live = _fresh()
_seed(repo)
(repo / "CHANGELOG.md").unlink()                                      # a MISSING named entry (not a stray)
rc, out, err = _run(sync.status)
check("13d status previews a MISSING entry as REPORT, distinct from HALT (M2)",
      "REPORT" in out and "HALT" not in out)
sync._git_status = _saved_git

# --- Proof 14: VERSION is 0.5.0 AND consistent across every shipped site that states a version ---------
# 14c/14d are M7's addition: the R-1 cross-file-equality discipline applied to the version string. Before
# them, a partial bump (VERSION updated, a header forgotten) went GREEN and shipped an inconsistent version
# - M7's own defect class ("the same claim, out of sync across shipped texts"). Now the suite FAILS on it.
# 14a is the single hand-maintained anchor (a real bump edits this literal); 14b-d derive from it, so they
# auto-follow the anchor and only fail when another site drifts away from VERSION.
VER14 = (REPO_ROOT / "claude" / "VERSION").read_text(encoding="utf-8").strip()
check("14a claude/VERSION is 0.5.0", VER14 == "0.5.0")
_changelog14 = (REPO_ROOT / "claude" / "CHANGELOG.md").read_text(encoding="utf-8")
check("14b claude/CHANGELOG.md carries the CURRENT VERSION's entry (not a stale forever-true match)",
      "## {} ".format(VER14) in _changelog14)
_claudemd14 = (REPO_ROOT / "claude" / "CLAUDE.md").read_text(encoding="utf-8")
_method14 = (REPO_ROOT / "claude" / "METHODOLOGY.md").read_text(encoding="utf-8")
check("14c claude/CLAUDE.md carries v<VERSION> in both the core header and the living-hypothesis line",
      _claudemd14.count("v" + VER14) >= 2)
check("14d claude/METHODOLOGY.md's Version line equals VERSION",
      "Version {}".format(VER14) in _method14)

# --- _copy's own "missing" detector (the TOCTOU primitive), exercised directly, not mocked --------
_copy_tmp = Path(tempfile.mkdtemp(prefix="wf_copy_")).resolve()
check("C1 _copy returns 'missing' for an absent source, and writes nothing",
      sync._copy(_copy_tmp / "nope.txt", _copy_tmp / "out.txt", backup=False) == "missing"
      and not (_copy_tmp / "out.txt").exists())

# --- Fresh-machine regression: the READ verbs must not crash when ~/.claude does not exist yet -----
# _live_orphans walks TARGET_DIR; on a brand-new box that directory is absent. status + capture must
# degrade gracefully (the M5 graceful-refuse value), not raise FileNotFoundError from iterdir().
repo, live = _fresh()
_seed(repo)
shutil.rmtree(live)                                                  # simulate: ~/.claude was never created
_saved_git = sync._git_status
sync._git_status = lambda: {"kind": "ok", "uncommitted": 0, "reached": True, "ahead": 0, "behind": 0}
try:
    rc_status, _, _ = _run(sync.status)
    rc_capture, out_capture, _ = _run(sync.capture)
    crashed = False
except Exception:
    crashed = True
sync._git_status = _saved_git
check("F1a status + capture don't crash when ~/.claude is absent (fresh machine)", not crashed)
check("F1b capture on an absent live root exits 0 (nothing to pull, no orphans)",
      not crashed and rc_capture == 0 and "0 live orphan(s)" in out_capture)

# --- Directive M1: one shared owned-predicate — walker and gate never disagree --------------------
# A non-junk top-level entry is EITHER shipped-from OR a stray, never both and never neither, because
# both `_bundle_files` and `_definition_problems` classify the top level through `_owns_root_entry`.
repo, live = _fresh()
_seed(repo)
(repo / "stray.md").write_text("x", encoding="utf-8")
ship, _ = sync._bundle_files(repo)
strays, _ = sync._definition_problems(repo)
shipped_top = {p.parts[0] for p in ship}                              # top-level names the walker touches
stray_names = {s.split("'")[1] for s in strays}                       # the 'name' inside each stray message
check("M1a no top-level entry is both shipped and a stray", shipped_top.isdisjoint(stray_names))
check("M1b the stray is flagged, not shipped", "stray.md" in stray_names and "stray.md" not in shipped_top)

# --- Directive M3: capture honours _copy's "missing" — never a false green (TOCTOU) ----------------
# Force every copy to report "missing" (a file vanishing after the exists() check): capture must count
# ZERO captured and exit non-zero, not print "captured" for a file it did not write.
repo, live = _fresh()
_seed(repo)
_run(sync.install)
_saved_copy = sync._copy
sync._copy = lambda *a, **k: "missing"
rc, out, err = _run(sync.capture)
sync._copy = _saved_copy
check("M3 capture reports 0 captured + exits non-zero when every copy vanishes (no false green)",
      "Captured 0 file(s)" in out and rc != 0)

# --- Directive M4: install's footer carries the missing-named count, agreeing with the exit code ---
repo, live = _fresh()
_seed(repo)
(repo / "VERSION").unlink()                                           # exactly one missing named entry
rc, out, err = _run(sync.install)
check("M4a install footer shows the missing-named count (1), agreeing with a non-zero exit",
      "1 named entry missing" in out and rc != 0)
repo, live = _fresh()
_seed(repo)
_saved_copy = sync._copy
sync._copy = lambda *a, **k: "missing"                                # force every copy to vanish
rc, out, err = _run(sync.install)
sync._copy = _saved_copy
check("M4b install footer shows 'vanished' + exits non-zero when copies vanish",
      "vanished" in out and rc != 0)


failed = [name for name, ok in checks if not ok]
print("\n{}/{} checks passed.".format(len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
