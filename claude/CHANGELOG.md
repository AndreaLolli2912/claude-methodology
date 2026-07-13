# Changelog

> Machine-readable release history for the working methodology. This file is the single,
> parseable source of the "what changed" delta shown by the update-notification hook, and
> the human-readable changelog. Each release is one `## <semver> — <date>` heading followed
> by `- ` bullet lines. Newest first. Keep the heading grammar stable — a parser binds to it.

## 0.3.4 — 2026-07-13
- Added `python sync.py status`: a **read-only** readout of where you stand across
  GitHub ↔ repo ↔ live `~/.claude`. It reports git state (uncommitted / not-pushed /
  GitHub-ahead / diverged, via a timeout-capped `git fetch` that degrades gracefully when
  offline) and byte-compares the bundle against `~/.claude` to catch the one thing no git
  command can see — "you pulled but haven't run `install`, so your live setup is behind the
  repo". Reports every condition at once; exits 0 only when fully in sync; changes nothing.

## 0.3.3 — 2026-07-13
- Added a custom **status line** (`claude/statusline.py`): a compact monochrome-green
  `mdl:… eff:… ctx:… 5h:…` line — model, reasoning effort, context (% + tokens used / window size), and the 5-hour Max
  quota (% + wall-clock reset time) — rendered from the JSON Claude Code pipes to a `statusLine` command. Stdlib-only
  Python (no `jq`/Git Bash needed), wired through `~/.claude/settings.json`.
- `sync.py`'s `MANIFEST` now carries `statusline.py`, so `install`/`capture` move it like any
  bundled file. `sync.py` also gains `enable-statusline` / `disable-statusline` to wire it into
  `~/.claude/settings.json` (mirroring `enable-hook`).

## 0.3.2 — 2026-07-06
- `python sync.py` with **no subcommand** now does the everyday thing — update on a git checkout,
  install on a plain copy — so there's one command to remember. The named subcommands are
  unchanged and still available.
- Reframed the README and docs around that single command.

## 0.3.1 — 2026-07-06
- Added `python sync.py update`: one command that runs `git pull --ff-only` then `install`, so a
  notified update can be applied in a single step (the update-check hook only *notifies*).
- The update notice (hook + `check`) now points at `sync.py update` instead of two manual steps.

## 0.3.0 — 2026-07-06
- Added update notifications: an opt-in Claude Code SessionStart hook (`python sync.py
  enable-hook`) that checks GitHub for a newer methodology version and shows this changelog's
  delta — so installs that don't Watch the repo still learn when to update.
- Added `claude/VERSION` (single machine-readable source of truth) and this `CHANGELOG.md`.
- `sync.py` gained `check`, `enable-hook`, and `disable-hook`; `install` is unchanged (still a
  pure file copy) and now prints a hint to run `enable-hook`.
- Normalized version labels to 3-part semver (`0.x.y`) across the core and reference.

## 0.2.0 — 2026-07-06
- Strengthened **R1**: questioning is now multi-round with a floor (≥2 rounds for new work,
  ≥3 when also large), each round drilling into the last, made broad and deep, stopping only
  at demonstrated saturation, and defaulting to *ask more* when unsure.
- Rewrote **R3**: questions are posed as precise, structured, self-contained options (the
  "avoid menus" guidance was dropped — ambiguity, not menus, was the problem); prose is
  reserved for explaining tradeoffs.
- Updated the `init-project-docs` skill to match the multi-round rule.

## 0.1.0 — 2026-07-02
- Initial extraction of the working methodology from the voice-assistant-concierge project,
  generalized to be technology-agnostic.
- Added **R1** (disambiguate first) and the **OODA** operating loop; strengthened **D2** to
  "comment everything (how + why)".
- Deployed as a lean always-on core + full reference + the `init-project-docs` skill, with a
  cross-platform, standard-library `sync.py`.
