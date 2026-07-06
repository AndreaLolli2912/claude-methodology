# Claude working-methodology — portable setup

My personal Claude Code working methodology, packaged so it deploys to any machine —
**Windows, macOS, or Linux** — with one command. This repo is the **source of truth** for
the files that live in `~/.claude` (`%USERPROFILE%\.claude` on Windows, `$HOME/.claude`
elsewhere).

The only requirement is **Python 3**, already present on most machines — nothing to install.

## Why this exists — the value

Coding agents (and people in a hurry) tend to fail the same few ways: they start building
before the task is understood, make silent assumptions, leave the *why* behind a change
undocumented, let the docs drift out of sync with the code, and never say up front what
"done" looks like. Each one quietly costs a rebuild later.

This methodology is a small, fixed set of rules that heads those off — and, because it's
deployed into `~/.claude`, it holds on **every** project and **every** machine, not just the
one where you happened to feel disciplined. It's built as an **OODA loop** (Observe →
Orient → Decide → Act, in small fast cycles) plus **six invariants**, each firing on a
specific trigger:

1. **Disambiguate first** — question a new task across several rounds *before* building, so
   you solve the real problem, not the first guess.
2. **Decide nothing by assumption** — surface grounded options and agree, instead of the
   agent silently picking for you.
3. **Comment to teach** — code explains *how* it works and *why* it exists, for a
   non-expert reader.
4. **Log every decision** — a dated log of what changed and why, so the project stays
   explainable months later.
5. **Keep docs in sync** — docs update in the same change as the code, so they never lie.
6. **Prove it** — state how you'll know a change worked, and check against that before
   calling it done.

Concretely, that buys four things:

- **Better agent output** — less rework, because the agent asks first, assumes nothing, and
  verifies its own work instead of confidently shipping the wrong thing.
- **A project that explains itself** — decisions and docs are captured as you go, so the
  history and the *why* are still there when you (or someone else) come back.
- **One consistent standard everywhere** — the same operating discipline on every repo and
  OS, installed with one command; no reinventing conventions per project.
- **A repeatable loop, not vibes** — Observe → Orient → Decide → Act is a cadence you apply
  to any work, so quality doesn't depend on how you felt that day.

The rules are a *living hypothesis*, not dogma: when one misfires in real use it gets
revised and the reason logged — that's how this reached **v0.2**. The always-on core is
`claude/CLAUDE.md`; the full Requirements / Project / Development / Testing rule set lives in
`claude/METHODOLOGY.md`.

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
- **Windows: if `python` prints a Microsoft Store message** (or seems to do nothing), Python
  isn't actually installed — that's the Store *alias stub*, not an interpreter, so
  `python sync.py install` will fail. Install Python 3 from
  [python.org](https://www.python.org/downloads/) (tick *"Add python.exe to PATH"*) or the
  Microsoft Store, then verify with `python --version` (you want `Python 3.x`, not the Store
  message) and re-run.
