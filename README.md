# Claude working-methodology — portable setup

My personal Claude Code working methodology, packaged so it deploys to any machine —
**Windows, macOS, or Linux** — with one command. This repo is the **source of truth** for
the files that live in `~/.claude` (`%USERPROFILE%\.claude` on Windows, `$HOME/.claude`
elsewhere).

The only requirement is **Python 3**, already present on most machines — nothing to install.

## Contents
- `claude/CLAUDE.md` — the always-on core (loaded in every project)
- `claude/METHODOLOGY.md` — the full rule reference (read on demand)
- `claude/skills/init-project-docs/SKILL.md` — scaffolds a project's standard docs
- `sync.py` — one script, two directions: deploy into `~/.claude`, or capture live edits back

## Install on a new machine
1. Get this folder onto the machine — `git clone <your-repo-url>`, or copy it via any channel
   your IT allows (OneDrive / Google Drive / USB).
2. In the folder, deploy the bundle into `~/.claude`:
   - Windows: `python sync.py install`
   - macOS / Linux: `python3 sync.py install`  (or `./sync.py install`)

   It backs up anything it replaces as `*.<timestamp>.bak`.
3. Restart Claude Code. Check `/skills` lists `init-project-docs`.

## Sync changes between machines
The repo is the source of truth, so the round-trip is one script, two directions:
- **Edited the live files in `~/.claude`?** Pull them back, then commit:
  `python sync.py capture`  →  `git add -A; git commit -m "..."; git push`
- **On another machine:** `git pull`, then `python sync.py install`.

## Notes
- `install` **overwrites** the bundled files in `~/.claude`, backing up any existing copy as
  `*.<timestamp>.bak`. If you keep unrelated personal instructions in `~/.claude/CLAUDE.md`,
  keep them committed here too, or ask Claude to split the core into its own imported file.
- `sync.py` is **location-independent** (it resolves paths from its own folder) and
  **standard-library only** (no `pip install`), so you can move or rename this repo, and it
  runs on any Python 3.
- Use `python` or `python3` — whichever your machine has. `~/.claude` means
  `%USERPROFILE%\.claude` on Windows and `$HOME/.claude` on macOS/Linux.
