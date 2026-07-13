# Overview

> What we're building, why, the roadmap, and current status. Living document — update
> whenever direction or status changes.

## What it is
`claude-methodology` is the **source of truth** for a personal Claude Code working
methodology and the files that live in `~/.claude` (`%USERPROFILE%\.claude` on Windows,
`$HOME/.claude` elsewhere). It packages the always-on core (`claude/CLAUDE.md`), the full
rule reference (`claude/METHODOLOGY.md`), the `init-project-docs` skill, and a custom status
line (`claude/statusline.py`) — plus a single cross-platform script, `sync.py`, that deploys
them onto a machine (`install`) and captures live edits back into the repo (`capture`). The
goal: reproduce the exact same Claude working style on any machine with one command, and keep
every machine in sync through git.

## Why (constraints)
- **Single-user, personal tooling.** Not a product; optimized for one person's workflow.
- **Cross-platform, Python-only.** Runs on Windows/macOS/Linux; the sole requirement is
  Python 3 (no installs, standard library only). `~/.claude` means `%USERPROFILE%\.claude`
  on Windows, `$HOME/.claude` elsewhere.
- **Repo is authoritative.** The live `~/.claude` files are deployed copies; edits round-trip
  back through `sync.py capture` before committing. Never let the two silently diverge.
- **Location-independent.** `sync.py` resolves paths from its own folder, so the repo can be
  moved or renamed without breaking.
- **Non-destructive install.** `sync.py install` backs up anything it overwrites as `*.<stamp>.bak`.

## Roadmap
| Stage | What | Status |
|------:|------|--------|
| 1 | Windows bundle: core + methodology + `init-project-docs` skill, install/capture scripts | Done (v0.1) |
| 2 | Git-based sync as the primary multi-machine flow (clone → pull → install; capture → commit → push) | In use; may automate |
| 3 | Cross-platform support — one `sync.py` runs install & capture on Windows/macOS/Linux | Done |
| 4 | Grow the bundle (more skills/agents) as the methodology matures | In progress (v0.3.3: status line) |
| 5 | Active adversarial workflow (six steps + a challenger) that makes the rules *run* | Designed — `docs/WORKFLOW.md`; build not started |

## Current status
**2026-07-13** — Piloting the six-step adversarial workflow by hand (`docs/WORKFLOW.md`, M1) on its
first real task: a new **`sync.py status`** command. Working through Step 1 (Need) reshaped what the
command should be:
- The original idea (from RISKS #3) was to warn that `install` might overwrite live edits you forgot
  to `capture`. But the sole developer **always edits in the repo and then installs — never edits the
  live `~/.claude` files directly** — so that overwrite never actually happens. That framing is
  retired (see RISKS #3).
- **What `status` does instead:** a **report-only** command (it never commits, pushes, pulls,
  installs, or edits anything) that tells you, in plain English, where you stand across the whole sync
  chain — **GitHub ↔ your repo ↔ your live `~/.claude`** — and what to do next. It reports every
  condition that applies at once (not just one), and degrades gracefully when you're offline, have no
  GitHub remote, or are on a plain (non-git) copy — it says so instead of pretending you're in sync.
- **Situations it reports:** in sync; uncommitted changes; commits not yet pushed to GitHub; GitHub is
  ahead (pull); you and GitHub have diverged; and — the part no git command can see — your live
  `~/.claude` is behind the repo because you haven't run `install`.
- **How we'll know it's done:** on a throwaway setup, each situation above produces the right
  plain-English report, and the command changes nothing (no commit/push/pull/install, no edits to your
  files or `~/.claude`).

**Built and verified** (2026-07-13): `sync.py status` is implemented and passes an end-to-end test of
every situation on throwaway repos plus a fake `HOME` — 17/17 checks, including a proof that it writes
nothing to `~/.claude` or the working tree. Still to do: a version bump, a `CHANGELOG` line, and the
commit/push (the commit is the user's to approve). Side finding logged in `DECISIONS.md`: a file's
modification time is **not** a safe signal for "which side is newer" (git restamps files on
pull/clone), so the tool never guesses sync direction from timestamps.

**2026-07-13** — Designed a major next direction: an active, six-step *adversarial workflow* — a
*builder* proposes, a separate *challenger* subagent attacks, the human judges, and the docs
self-write. Full design in `docs/WORKFLOW.md`; **not built yet** — next is a by-hand validation (M1)
before any machinery. See DECISIONS 2026-07-13.

**2026-07-13** — v0.3.3: added a custom Claude Code status line (`claude/statusline.py`,
monochrome-green `mdl:… eff:… ctx:… 5h:…`) to the bundle; wired live via `settings.json` and
carried by `sync.py`'s `MANIFEST`. Enabling it on a new machine is still a manual `settings.json`
step (RISKS #7). See DECISIONS 2026-07-13.

**2026-07-05** — v0.1 methodology core committed; standard project docs scaffolded. Transport
is now a single cross-platform `sync.py` (Windows/macOS/Linux), replacing the PowerShell
scripts — roadmap stage 3 done, RISKS #1 closed. Verified end-to-end on both Windows and real
Linux (Ubuntu). Next: sync automation.
