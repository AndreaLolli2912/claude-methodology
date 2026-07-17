#!/usr/bin/env python3
"""Test sync.py's M5 wiring (Block 3 / D-8): the enable/disable-workflow verbs, the enable_statusline
preserve-script change, the shared register/deregister helpers, and the MANIFEST rows.

Two layers:
  * PURE helpers on in-memory dicts (no I/O): _command_refers_to distinguishes the two status-line
    scripts; _register_hook adds then refreshes-in-place; _deregister_hook removes + prunes.
  * The verbs end to end, with sync.SETTINGS_FILE redirected to a TEMP file so the live
    ~/.claude/settings.json is NEVER touched: enable-workflow writes the nudge (SessionStart +
    UserPromptSubmit) + the wf status line, coexists with an existing check_version hook, is
    idempotent; disable-workflow reverses it; enable_statusline PRESERVES the wf renderer (D-8).

Standalone script; run directly, not under pytest. It never writes the real settings.json.
"""
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
import sync  # noqa: E402

# Redirect EVERY settings write to a temp file - the live ~/.claude/settings.json must never be
# touched by a test. All the verbs use the module global sync.SETTINGS_FILE, so this one line isolates
# them (their backups land in the temp dir too).
TMP = Path(tempfile.mkdtemp(prefix="wf_sync_")).resolve()
sync.SETTINGS_FILE = TMP / "settings.json"

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


def read_settings():
    return json.loads(sync.SETTINGS_FILE.read_text(encoding="utf-8")) if sync.SETTINGS_FILE.exists() else {}


def reset_settings(obj=None):
    """Start each scenario from a known settings.json (or none)."""
    if obj is None:
        if sync.SETTINGS_FILE.exists():
            sync.SETTINGS_FILE.unlink()
    else:
        sync.SETTINGS_FILE.write_text(json.dumps(obj), encoding="utf-8")


def cmds(settings, event):
    return [e.get("command", "") for g in settings.get("hooks", {}).get(event, []) for e in g.get("hooks", [])]


# A realistic pre-existing check_version hook, to prove D-8's "never delete check_version".
CHECK_HOOK = {"hooks": {"SessionStart": [{"matcher": "startup",
              "hooks": [{"type": "command", "command": '"py" "/x/hooks/check_version.py"', "timeout": 10}]}]}}
NUDGE_A = '"pyA" "/x/workflow/nudge.py"'
NUDGE_B = '"pyB" "/x/workflow/nudge.py"'

# ---------------------------------------------------------------------------
# PURE helpers (in-memory dicts, no file I/O).
# ---------------------------------------------------------------------------
# The substring subtlety: statusline.py must NOT match a statusline_wf.py command (else enable-statusline
# would think the plain line is active and could revert the wf one).
check("P1 statusline.py predicate does NOT match a statusline_wf.py command",
      sync._command_refers_to('"py" "/x/statusline_wf.py"', sync.STATUSLINE_WF_REL)
      and not sync._command_refers_to('"py" "/x/statusline_wf.py"', sync.STATUSLINE_REL))
check("P2 statusline.py predicate matches a plain statusline.py command",
      sync._command_refers_to('"py" "/x/statusline.py"', sync.STATUSLINE_REL))
check("P3 nudge and check predicates are distinct",
      sync._hook_refers_to_nudge(NUDGE_A) and not sync._hook_refers_to_check(NUDGE_A))

# _register_hook: first add returns False + no matcher key; re-register (same script, new interpreter)
# refreshes IN PLACE (returns True, no duplicate).
s = {}
r1 = sync._register_hook(s, "UserPromptSubmit", None, NUDGE_A, sync._hook_refers_to_nudge)
check("P4 first register appends (False) with no matcher key",
      r1 is False and cmds(s, "UserPromptSubmit") == [NUDGE_A] and "matcher" not in s["hooks"]["UserPromptSubmit"][0])
r2 = sync._register_hook(s, "UserPromptSubmit", None, NUDGE_B, sync._hook_refers_to_nudge)
check("P5 re-register refreshes in place (True, no duplicate)",
      r2 is True and cmds(s, "UserPromptSubmit") == [NUDGE_B])

# _deregister_hook: removes the only hook -> prunes the event AND the empty hooks dict.
removed = sync._deregister_hook(s, "UserPromptSubmit", sync._hook_refers_to_nudge)
check("P6 deregister removes + prunes emptied structures", removed is True and "hooks" not in s)
check("P7 deregister a missing hook -> False",
      sync._deregister_hook({}, "SessionStart", sync._hook_refers_to_nudge) is False)

# ---------------------------------------------------------------------------
# The verbs, end to end (writes go to the temp settings.json).
# ---------------------------------------------------------------------------
# 1) enable-workflow all -> nudge on both events + the wf status line.
reset_settings()
sync.enable_workflow("all")
st = read_settings()
check("1a SessionStart carries a nudge hook", any("nudge" in c for c in cmds(st, "SessionStart")))
check("1b SessionStart matcher is the four-leg alternation",
      any(g.get("matcher") == "startup|resume|clear|compact" for g in st["hooks"]["SessionStart"]))
check("1c UserPromptSubmit carries a nudge hook with NO matcher",
      any("nudge" in c for c in cmds(st, "UserPromptSubmit"))
      and all("matcher" not in g for g in st["hooks"]["UserPromptSubmit"]))
check("1d statusLine points at the wf renderer",
      sync._command_refers_to(st.get("statusLine", {}).get("command", ""), sync.STATUSLINE_WF_REL))

# 2) idempotent: run again -> exactly one nudge per event, not two.
sync.enable_workflow("all")
st = read_settings()
check("2 enable-workflow is idempotent (one nudge per event)",
      sum("nudge" in c for c in cmds(st, "SessionStart")) == 1
      and sum("nudge" in c for c in cmds(st, "UserPromptSubmit")) == 1)

# 3) coexists with an existing check_version hook (D-8: never delete check_version).
reset_settings(CHECK_HOOK)
sync.enable_workflow("nudge")
st = read_settings()
check("3 check_version hook survives enable-workflow (both present on SessionStart)",
      any(sync._hook_refers_to_check(c) for c in cmds(st, "SessionStart"))
      and any(sync._hook_refers_to_nudge(c) for c in cmds(st, "SessionStart")))

# 4) enable_statusline PRESERVES the wf renderer - the D-8 change (the flat assign would revert it).
reset_settings()
sync.enable_workflow("statusline")     # statusLine := wf
sync.enable_statusline()               # must NOT revert to plain
st = read_settings()
check("4 enable_statusline preserves the wf renderer (no silent revert)",
      sync._command_refers_to(st["statusLine"]["command"], sync.STATUSLINE_WF_REL))

# 4b) enable_statusline on a clean file -> the plain statusline.py.
reset_settings()
sync.enable_statusline()
st = read_settings()
check("4b enable_statusline on a clean file -> plain statusline.py",
      sync._command_refers_to(st["statusLine"]["command"], sync.STATUSLINE_REL)
      and not sync._command_refers_to(st["statusLine"]["command"], sync.STATUSLINE_WF_REL))

# 5) disable-workflow reverses it: nudge gone, statusLine reverted to plain.
reset_settings()
sync.enable_workflow("all")
sync.disable_workflow("all")
st = read_settings()
check("5a disable-workflow removes the nudge from both events",
      not any("nudge" in c for c in cmds(st, "SessionStart"))
      and not any("nudge" in c for c in cmds(st, "UserPromptSubmit")))
check("5b disable-workflow reverts statusLine to plain statusline.py",
      sync._command_refers_to(st.get("statusLine", {}).get("command", ""), sync.STATUSLINE_REL))

# 5c) disabling the nudge leaves an unrelated check hook AND other settings intact.
reset_settings({**CHECK_HOOK, "otherKey": "keep-me"})
sync.enable_workflow("nudge")
sync.disable_workflow("nudge")
st = read_settings()
check("5c disabling the nudge keeps check_version + unrelated keys",
      any(sync._hook_refers_to_check(c) for c in cmds(st, "SessionStart")) and st.get("otherKey") == "keep-me")

# 6) The bundle still ships the six D-8 files (workflow machinery + M5 scripts). M6 retired the
#    per-file MANIFEST for a directory-whitelist walk, so we assert against the WALK's ship set now
#    (they're covered by BUNDLE_DIRS `workflow/`+`agents/` and BUNDLE_ROOT_FILES `statusline_wf.py`).
_ship6 = {p.as_posix() for p in sync._bundle_files(sync.BUNDLE_DIR)[0]}
for rel in ("workflow/workflow.py", "workflow/rulebook.md", "workflow/conductor.md",
            "agents/challenger.md", "workflow/nudge.py", "statusline_wf.py"):
    check("6 bundle walk ships " + rel, rel in _ship6)

# 7) A valid-JSON-but-non-object settings.json (e.g. a list) must be a graceful REFUSE, never a
#    traceback and never an overwrite - _read_settings now rejects a non-dict parse (the type-
#    confusion class). Verb catches ValueError, prints, returns; the file is left byte-for-byte.
reset_settings()
sync.SETTINGS_FILE.write_text("[1, 2, 3]", encoding="utf-8")
try:
    sync.enable_workflow("all")
    crashed = False
except Exception:
    crashed = True
check("7a non-dict settings.json -> graceful refuse, no crash", not crashed)
check("7b non-dict settings.json is left intact (not overwritten)",
      sync.SETTINGS_FILE.read_text(encoding="utf-8") == "[1, 2, 3]")


failed = [name for name, ok in checks if not ok]
print("\n{}/{} checks passed.".format(len(checks) - len(failed), len(checks)))
sys.exit(1 if failed else 0)
