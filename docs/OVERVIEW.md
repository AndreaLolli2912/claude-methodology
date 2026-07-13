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

## Current status
**2026-07-13** — v0.3.3: added a custom Claude Code status line (`claude/statusline.py`,
monochrome-green `mdl:… eff:… ctx:… 5h:…`) to the bundle; wired live via `settings.json` and
carried by `sync.py`'s `MANIFEST`. Enabling it on a new machine is still a manual `settings.json`
step (RISKS #7). See DECISIONS 2026-07-13.

**2026-07-05** — v0.1 methodology core committed; standard project docs scaffolded. Transport
is now a single cross-platform `sync.py` (Windows/macOS/Linux), replacing the PowerShell
scripts — roadmap stage 3 done, RISKS #1 closed. Verified end-to-end on both Windows and real
Linux (Ubuntu). Next: sync automation.
