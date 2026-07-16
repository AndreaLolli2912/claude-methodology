#!/usr/bin/env python3
"""statusline_wf.py - the workflow-aware status line (M5, Decision D-4).

Claude Code runs ONE statusline command per refresh. This is that command when the workflow is
enabled: it prints the exact same base line as statusline.py, then - only when the current project
has an open workflow task - appends one compact segment naming the step and its freshness:

    mdl:opus-4.8 eff:max ctx:8% 15.5k/200k 5h:34% @17:02 wf:implementation:missing
                                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                          the added segment: wf:<step>:<state>

WHY a separate file (not a flag on statusline.py): a hook/status-line script is launched as a bare
`<python> <script>`, so `sys.path[0]` is the SCRIPT'S OWN directory and nothing else. This file
ships to ~/.claude/ beside statusline.py, so `import statusline` is a same-directory import that can
NEVER fail - which is what keeps must-not #5 true: the base line always renders, even if the
workflow half is broken. workflow.py lives one level down (~/.claude/workflow/), so importing IT is
the only cross-directory step, and it happens ONLY after we have confirmed a task marker exists, and
inside a guard, so any failure degrades to `wf:ERR` beside an intact base line - never a dead script.

The safety spine (Design D-9(ii), the honest floor): we STAT the marker file INLINE with a raw
Path.exists - importing NOTHING - before deciding to touch workflow.py at all. No task, no import,
no segment (must-not #3: never annotate an unrelated repo). And the project root comes from what the
platform HANDS us (stdin `workspace.project_dir`, or $CLAUDE_PROJECT_DIR), which we then pass to
workflow's readers EXPLICITLY - never letting them fall back to a cwd walk-up, which for a status
line launched who-knows-where would re-enter the D-2 defect (bind the wrong project, or none).

Standard library only. ASCII only (stdout is a pipe; a locale codepage vs UTF-8 mismatch would
mojibake). The wf vocabulary (need/design/.../shipping x fresh/stale/missing) is exactly what the
`status` verb and receipt_state use (must-not #4), and the segment is drawn with statusline._pair so
the whole line stays one palette.
"""

# json parses the stdin blob; os reads the $CLAUDE_PROJECT_DIR fallback; sys gives stdin/stdout and
# the path bridge; Path does the inline marker stat. All standard library, nothing to install.
import json
import os
import sys
from pathlib import Path

# statusline.py is same-directory (both ship to ~/.claude/), so this import is unconditional and
# safe - it is the base line, and must-not #5 says the base line can never sit behind a fragile
# import. (In the repo it resolves to claude/statusline.py; deployed, to ~/.claude/statusline.py.)
import statusline

# This file's own directory. workflow.py lives in the `workflow/` subdirectory of it - the ONE
# cross-directory import, bridged onto sys.path only inside the guarded marker-present branch below.
HERE = Path(__file__).resolve().parent


def _resolve_root(data):
    """Where is the project? The status line is HANDED its root by the platform, never guesses it:
    stdin `workspace.project_dir` first (documented), then $CLAUDE_PROJECT_DIR (undocumented but
    observed to reach a status line - so a fallback only). Returns a Path, or None when neither is
    present - in which case there is no project to annotate and the base line stands alone.

    `.resolve()` normalizes what the platform hands us (D-2a): stdin and the env var disagree on
    slash direction (forward vs back), and resolving canonicalizes them to one path. The isinstance
    guards refuse a wrong-typed workspace/project_dir (valid JSON, wrong shape) rather than crash on
    it - a status line must degrade to the base line, never blank (must-not #5)."""
    ws = data.get("workspace")
    project_dir = ws.get("project_dir") if isinstance(ws, dict) else None
    if isinstance(project_dir, str) and project_dir:
        return Path(project_dir).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return None


def render_wf(data):
    """Return the full status line for `data`: the base line, plus a wf: segment IFF this project
    has an open task. Never raises - a status line that raised would blank the whole line."""
    # The base line ALWAYS renders, from the data we were handed - no second stdin read (D-4(b):
    # statusline.render takes parsed data, so the read-once pipe is never touched again here).
    line = statusline.render(data)

    # From here down is the WORKFLOW half, fully guarded so that once `line` exists NOTHING below can
    # blank it (must-not #5). Two guards, because the two failures mean different things: resolving/
    # stat-ing the task can fail (we then can't even SEE a task -> base line only), and READING a task
    # we DID find can fail (a known task with broken machinery -> a visible wf:ERR).
    try:
        root = _resolve_root(data)
        if root is None:
            return line   # no project handed to us -> nothing to annotate
        # INLINE stat of the marker (D-9(ii)): a raw Path.exists, importing NOTHING. This exact
        # literal `.workflow/marker.json` must equal workflow.marker_path's spelling - a test asserts
        # it (the two copies are the deliberate price of stat-before-import, not an accident).
        if not (root / ".workflow" / "marker.json").exists():
            return line   # no task open in this project -> base line only (must-not #3)
    except Exception:
        return line       # anything wrong locating the task -> the base line still stands alone

    # A task exists here. NOW - and only now - bridge to workflow.py (one level down) and read the
    # shared freshness truth. Any import/read failure degrades to `wf:ERR` beside the intact line.
    try:
        sys.path.insert(0, str(HERE / "workflow"))
        import workflow  # noqa: E402  (deliberately late + guarded - see the module docstring)
        # EXPLICIT root to every reader (the D-2 invariant): the platform told us where the project
        # is; workflow must not re-guess it from a cwd walk-up.
        marker = workflow.load_marker(root=root)
        step = marker["current_step"]
        state = workflow.receipt_state(step, root=root, marker=marker)
        segment = statusline._pair("wf", "{}:{}".format(step, state))
    except Exception:
        # The marker is present but something below it failed (import, parse, a corrupt marker).
        # Flag it visibly rather than hide it - but keep the base line whole.
        segment = statusline._pair("wf", "ERR")
    return line + " " + segment


def main():
    # Read the session blob ONCE, degrading to {} on nothing/garbage exactly as statusline.py does
    # (a status line that raised on bad input would show nothing). render_wf takes it from here.
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}                              # valid-but-non-object JSON -> {} (render must not blank)
    sys.stdout.write(render_wf(data) + "\n")


if __name__ == "__main__":
    main()
