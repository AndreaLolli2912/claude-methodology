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
- `claude/CHANGELOG.md` — the per-release history (also what the update check reads)
- `claude/VERSION` — the machine-readable current version (single source of truth)
- `claude/skills/init-project-docs/SKILL.md` — scaffolds a project's standard docs
- `claude/hooks/check_version.py` — SessionStart hook that flags when a newer version exists
- `sync.py` — one script: deploy/update `~/.claude`, capture edits back, or check/enable the update hook

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

## Staying up to date
`sync.py install` is a one-shot copy — it can't tell you when a *newer* methodology version is
published later. If you don't Watch this repo on GitHub, two ways to find out:

**On demand** — ask any time:
```
python sync.py check
```
It compares your installed `~/.claude/VERSION` against the version on GitHub and, if you're
behind, prints the changelog of exactly what you'd gain.

**Automatically, inside Claude Code** (opt-in) — set it once:
```
python sync.py enable-hook      # add it     ·     python sync.py disable-hook   # remove it
```
This adds a `SessionStart` hook to `~/.claude/settings.json` (your existing settings are backed
up first and fully preserved). From then on, when you start a new Claude Code session and a
newer version exists, you'll see a short notice of what changed — then apply it in one step
with `python sync.py update` (a `git pull --ff-only` followed by `install`).

The check is deliberately unobtrusive: it runs at most **once a day** (cached in between), times
out fast, stays **silent when you're up to date or offline**, and never blocks a session. It
makes one HTTPS request to GitHub; to turn it off, run `disable-hook` or set the environment
variable `METHODOLOGY_UPDATE_CHECK=0`.

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
