# Claude working-methodology — portable setup

My personal Claude Code working methodology, packaged so it deploys to any **Windows**
machine with one command. This repo is the **source of truth** for the files that live in
`~/.claude` (= `%USERPROFILE%\.claude`).

## Contents
- `claude/CLAUDE.md` — the always-on core (loaded in every project)
- `claude/METHODOLOGY.md` — the full rule reference (read on demand)
- `claude/skills/init-project-docs/SKILL.md` — scaffolds a project's standard docs
- `install.ps1` — copy these into this machine's `~/.claude` (backs up anything it replaces)
- `capture.ps1` — copy live edits from `~/.claude` back here (before you commit)

## Install on a new machine
1. Get this folder onto the machine — either:
   - `git clone <your-repo-url>`, **or**
   - copy the folder via OneDrive / Google Drive / USB (any channel your IT allows).
2. In the folder, open PowerShell and run:  `.\install.ps1`
3. Restart Claude Code. Check `/skills` lists `init-project-docs`.

## Sync changes between machines
The repo is the source of truth, so the round-trip is two scripts:
- **Edited the live files in `~/.claude`?** Run `.\capture.ps1`, then
  `git add -A; git commit -m "..."; git push`.
- **On another machine:** `git pull`, then `.\install.ps1`.

## Notes
- `install.ps1` **overwrites** the three files in `~/.claude`, backing up any existing copy
  as `*.<timestamp>.bak`. If you keep unrelated personal instructions in
  `~/.claude/CLAUDE.md`, keep them committed here too, or ask Claude to split the core into
  its own imported file.
- The scripts are **location-independent** (they use their own folder), so you can move or
  rename this repo without breaking anything.
- Windows / PowerShell only. `~/.claude` means `%USERPROFILE%\.claude`.
