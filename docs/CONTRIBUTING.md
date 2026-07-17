# How to change this project

> A practical guide to changing each part safely. Update when the code structure changes.

## Mental model
- **Content** lives in `claude/` (the methodology + skills).
- **Transport** lives at the root (`sync.py`, one cross-platform script).
- **The repo is the source of truth**; `~/.claude` holds deployed copies.

## The edit → run → see-it loop
There are two directions. Pick the one that matches where you made the edit.
(Use `python` on Windows, `python3` on macOS/Linux.)

**Edited the repo (`claude/…`)?** Deploy it and check it loaded:
1. `python sync.py install`  — copies the bundle into `~/.claude` (backs up replaced files).
2. Restart Claude Code.
3. Verify: `/skills` lists `init-project-docs`; the core rules are in effect.

**Edited the live files in `~/.claude` (e.g. mid-session tuning)?** Pull them back before
committing:
1. `python sync.py capture`  — copies live files into the repo.
2. `git add -A; git commit -m "…"; git push`.

**On another machine:** `git pull`, then `python sync.py install`.

## Common changes
- **Tweak a methodology rule** → edit `claude/CLAUDE.md` (core) or
  `claude/METHODOLOGY.md` (full reference) → `python sync.py install` → restart → confirm.
- **Change how docs are scaffolded** → edit
  `claude/skills/init-project-docs/SKILL.md` → reinstall → re-run the skill in a scratch
  repo to test.
- **Add a new file to the bundle** → put it under one of the named directories in `claude/`
  (`skills/ agents/ hooks/ workflow/`) and it ships automatically — no code edit. A *new top-level*
  file or directory under `claude/` must be named in `sync.py`'s `BUNDLE_ROOT_FILES`/`BUNDLE_DIRS`
  (or added to `IGNORE`), or `install` halts until you classify it (see `ARCHITECTURE.md` § Contracts).
- **Tweak the status line** → edit `claude/statusline.py` → `python sync.py install` → restart
  Claude Code. It's pointed at by a `statusLine` block in `~/.claude/settings.json`, which is
  personal (not bundled), so on a new machine run `python sync.py enable-statusline` to wire it (see `RISKS.md` #7).
- **Change install/sync behavior** → edit `sync.py`; keep it location-independent
  (`Path(__file__).parent`) and non-destructive (back up before overwrite). Standard library
  only — no `pip` dependencies. Test against a throwaway `HOME`/`USERPROFILE` before trusting it.
