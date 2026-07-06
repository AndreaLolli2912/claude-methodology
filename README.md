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
revised and the reason logged — that's how it keeps improving. The always-on core is
`claude/CLAUDE.md`; the full Requirements / Project / Development / Testing rule set lives in
`claude/METHODOLOGY.md`.

## The docs it creates in your projects — so nothing surprises you
When you work on a project with this methodology, Claude keeps a small, **standard set of docs**
and *maintains* them as you go (that's the "log decisions" and "keep docs in sync" invariants). It
sets them up with the `init-project-docs` skill, which **asks you a few questions first** — it
doesn't just dump files on you. So if a `docs/` folder appears, that's expected, and every file
has exactly one job:

| File | What it's for |
|---|---|
| `README.md` | Orientation + quick start — the front door |
| `CLAUDE.md` | Instructions auto-loaded into every Claude session for the project |
| `docs/OVERVIEW.md` | What you're building, why, the roadmap, and current status |
| `docs/DECISIONS.md` | A dated log of what changed and *why* (newest first) |
| `docs/ARCHITECTURE.md` | The components, their boundaries, and the tech stack |
| `docs/CONTRIBUTING.md` | How to change each part safely |
| `docs/RISKS.md` | Things that work now but will bite under scale or deployment |
| `docs/PLAYBOOK.md` | Reusable, cross-project build recipes |

You're not forced into all of them — tell Claude to skip any you don't want. The payoff is a
project that explains itself later, instead of "why is it built like this?" archaeology.

## Contents
- `claude/CLAUDE.md` — the always-on core (loaded in every project)
- `claude/METHODOLOGY.md` — the full rule reference (read on demand)
- `claude/CHANGELOG.md` — the per-release history (also what the update check reads)
- `claude/VERSION` — the machine-readable current version (single source of truth)
- `claude/skills/init-project-docs/SKILL.md` — scaffolds a project's standard docs
- `claude/hooks/check_version.py` — SessionStart hook that flags when a newer version exists
- `sync.py` — one script: deploy/update `~/.claude`, capture edits back, or check/enable the update hook

## Set it up — and keep it current — with one command
Get this folder onto the machine (`git clone <your-repo-url>`, or copy it via any channel your
IT allows — OneDrive / Google Drive / USB). Then, from inside the folder, run:

    python sync.py

That's the everyday command. With **no subcommand** it brings `~/.claude` up to date: on a git
clone it pulls the latest and installs it; on a plain copy it just installs what's here. It backs
up anything it replaces as `*.<timestamp>.bak`. Restart Claude Code and check `/skills` lists
`init-project-docs`. Run it again any time to update. (Use `python3` on macOS/Linux.)

## Get told when there's an update (optional — set once)

    python sync.py enable-hook

Adds a `SessionStart` hook so that, when you start a new Claude Code session and a newer version
exists, you see a short notice of what changed — then run `python sync.py` to apply it. The check
is unobtrusive: at most **once a day**, fast timeout, **silent when up to date or offline**, and
never blocks a session. Turn it off with `python sync.py disable-hook` or by setting
`METHODOLOGY_UPDATE_CHECK=0`.

## The other commands (you rarely need these)
| Command | What it does |
|---|---|
| `python sync.py` | **The everyday one** — update (git clone) or install (plain copy) |
| `python sync.py update` | The explicit form: `git pull --ff-only`, then install |
| `python sync.py install` | Deploy the files here into `~/.claude` (no pull) |
| `python sync.py check` | Manually ask "is a newer version published?" (the hook already does this) |
| `python sync.py enable-hook` · `disable-hook` | Turn the in-session update notice on / off |
| `python sync.py capture` | Reverse direction — copy live `~/.claude` edits back into the repo, then `git commit` |

**Editing the methodology yourself?** Change the files under `claude/`, run `python sync.py` to
deploy, then commit + push. If you edited the live `~/.claude` files directly, pull them back
first with `python sync.py capture`. Full guide: `docs/CONTRIBUTING.md`.

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
