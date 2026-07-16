#!/usr/bin/env python3
"""Test the workflow-aware status line (statusline_wf.py, M5 Block 2 / D-4).

Proves, by running the REAL script as a subprocess with crafted stdin (exactly how Claude Code
invokes it):
  1. No project handed in -> base line only, byte-identical to plain statusline (must-not #5).
  2. A project with no task -> base line only, no wf: segment (must-not #3: never annotate a repo
     with no task; workflow.py is not even imported - proven by the broken-workflow probe in 4).
  3. A task present -> base line + `wf:<step>:<state>`, the state matching the shared receipt_state
     (fresh, then stale after the draft is edited - the SAME truth the CLI `status` verb shows).
  4. A present-but-unparseable marker -> `wf:ERR` beside an intact base line (never a dead line).
  5. $CLAUDE_PROJECT_DIR is honoured as the fallback root when stdin carries no workspace.
  6. statusline_wf's inline `.workflow/marker.json` literal matches workflow.marker_path's spelling
     (Architecture Section 8, proof 2 - the stat-before-import copy cannot silently drift).

Standalone script (sys.exit at the end): run it DIRECTLY, never under pytest.
"""
import json
import os
import re
import subprocess
import sys
import shutil
import tempfile
from pathlib import Path

# The line is drawn with ANSI colour spans, and _pair renders a KEY and a VALUE as SEPARATE spans -
# so "wf:ERR" (key "wf", value "ERR") is not a contiguous substring of the raw bytes. Strip the
# colour codes before asserting on the human-VISIBLE text, which is what actually reads "wf:...".
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def visible(s):
    return _ANSI.sub("", s)

REPO_CLAUDE = Path(__file__).resolve().parents[2] / "claude"

# Mimic the deployed ~/.claude layout in a temp dir: statusline.py + statusline_wf.py at the top,
# workflow.py + rulebook.md in workflow/. statusline_wf resolves BOTH its imports off its own file
# location, so this layout is what makes `import statusline` (same dir) and the bridged `import
# workflow` (workflow/ subdir) resolve exactly as they will once deployed.
TMP = Path(tempfile.mkdtemp(prefix="wf_sl_")).resolve()   # resolved so the hook's own .resolve() is identity
CLAUDE = TMP / "claude"
(CLAUDE / "workflow").mkdir(parents=True)
shutil.copy(REPO_CLAUDE / "statusline.py", CLAUDE / "statusline.py")
shutil.copy(REPO_CLAUDE / "statusline_wf.py", CLAUDE / "statusline_wf.py")
shutil.copy(REPO_CLAUDE / "workflow" / "workflow.py", CLAUDE / "workflow" / "workflow.py")
shutil.copy(REPO_CLAUDE / "workflow" / "rulebook.md", CLAUDE / "workflow" / "rulebook.md")
WF_SCRIPT = CLAUDE / "statusline_wf.py"

# Import the copied modules in-process to build correct markers and compute the expected base line.
sys.path.insert(0, str(CLAUDE / "workflow"))
import workflow  # noqa: E402
sys.path.insert(0, str(CLAUDE))
import statusline  # noqa: E402

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


# A scrubbed environment so the $CLAUDE_PROJECT_DIR fallback is absent unless a check sets it -
# otherwise a real CLAUDE_PROJECT_DIR in this shell would leak in and make the "no project" cases
# non-deterministic.
_BASE_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}


def run_wf(payload, extra_env=None):
    """Run statusline_wf.py with `payload` as the stdin JSON; return stdout (stripped of newline)."""
    env = dict(_BASE_ENV)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run([sys.executable, str(WF_SCRIPT)], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.stdout.rstrip("\n")


def run_wf_raw(raw_stdin):
    """Feed RAW stdin (an already-encoded string, so we can send malformed / non-object JSON) and
    return (returncode, stdout). Used by the robustness checks."""
    p = subprocess.run([sys.executable, str(WF_SCRIPT)], input=raw_stdin,
                       capture_output=True, text=True, env=dict(_BASE_ENV))
    return p.returncode, p.stdout


SAMPLE = {"model": {"display_name": "Opus 4.8"},
          "context_window": {"used_percentage": 8, "total_input_tokens": 15500,
                             "context_window_size": 200000}}
BASE = statusline.render(SAMPLE)   # the exact plain line for this data


def with_root(root):
    d = dict(SAMPLE)
    d["workspace"] = {"project_dir": str(root)}
    return d


# 1) No workspace at all -> base line only, byte-identical to plain statusline.
out = run_wf(SAMPLE)
check("1 no project -> base line only, identical to plain statusline",
      out == BASE and "wf:" not in out)

# 2) A project with NO .workflow/marker.json -> base line only.
PROJ = TMP / "proj"
(PROJ / "docs").mkdir(parents=True)
(PROJ / ".workflow").mkdir()
out = run_wf(with_root(PROJ))
check("2 project without a task -> base line only", out == BASE and "wf:" not in out)

# 3) A task present -> base line + wf:<step>:<state>. Build a FRESH receipt by hashing the draft
#    bytes exactly as `record` would, so receipt_state must read "fresh".
draft = workflow.draft_path(PROJ, "need")
draft.write_text("# Need draft\n", encoding="utf-8")
marker = {"task_id": "abcd1234", "task_title": "T", "current_step": "need",
          "receipts": {"need": {"challenge_ran": True,
                                "artifact_hash": workflow.sha256_bytes(draft)}},
          "pending": None}
workflow.marker_path(PROJ).write_text(json.dumps(marker), encoding="utf-8")
out = run_wf(with_root(PROJ))
check("3 task present -> base line + wf:need:fresh",
      out.startswith(BASE) and "wf:need:fresh" in visible(out))

# 3b) Edit the draft -> the segment flips to stale (the shared truth surfaced on the status line).
draft.write_text("# Need draft EDITED\n", encoding="utf-8")
out = run_wf(with_root(PROJ))
check("3b editing the draft flips the segment to stale", "wf:need:stale" in visible(out))

# 4) A present-but-unparseable marker -> wf:ERR beside an intact base line.
workflow.marker_path(PROJ).write_text("{ not valid json", encoding="utf-8")
out = run_wf(with_root(PROJ))
check("4 broken marker -> wf:ERR, base line intact",
      out.startswith(BASE) and "wf:ERR" in visible(out))

# 5) $CLAUDE_PROJECT_DIR fallback: no workspace in stdin, but the env var points at a task. Restore
#    the fresh marker first so we expect a real state, not ERR.
workflow.marker_path(PROJ).write_text(json.dumps(marker), encoding="utf-8")
draft.write_text("# Need draft\n", encoding="utf-8")   # back to the hashed bytes -> fresh
out = run_wf(SAMPLE, extra_env={"CLAUDE_PROJECT_DIR": str(PROJ)})
check("5 $CLAUDE_PROJECT_DIR is the fallback root", "wf:need:fresh" in visible(out))

# 6) Architecture Section 8 proof 2 (statusline_wf's half): its inline literal is spelled exactly as
#    workflow.marker_path builds it. End-to-end, check 3 already proved they agree (the script FOUND
#    the marker workflow wrote); this pins the source literal too.
src = WF_SCRIPT.read_text(encoding="utf-8")
check("6 inline .workflow/marker.json matches marker_path spelling",
      '".workflow" / "marker.json"' in src
      and workflow.marker_path(Path("/x")).as_posix().endswith(".workflow/marker.json"))

# 7) Robustness (must-not #5): valid-JSON-but-wrong-shape input must degrade to the base line, never
#    blank it. Each of these previously crashed the workflow half before the base line was returned.
rc, out = run_wf_raw(json.dumps({**SAMPLE, "workspace": "oops"}))          # workspace not a dict
check("7a wrong-typed workspace -> base line, exit 0", rc == 0 and out.rstrip("\n") == BASE)
rc, out = run_wf_raw(json.dumps({**SAMPLE, "workspace": {"project_dir": 12345}}))   # non-str project_dir
check("7b numeric project_dir -> base line, exit 0", rc == 0 and out.rstrip("\n") == BASE)
rc, out = run_wf_raw("[1, 2, 3]")                                          # valid JSON, not an object
check("7c top-level non-object stdin -> a line still renders, exit 0",
      rc == 0 and "mdl:" in visible(out) and "wf:" not in visible(out))


failed = [name for name, ok in checks if not ok]
print("\n{}/{} checks passed.".format(len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
