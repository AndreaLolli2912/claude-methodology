# Changelog

> Machine-readable release history for the working methodology. This file is the single,
> parseable source of the "what changed" delta shown by the update-notification hook, and
> the human-readable changelog. Each release is one `## <semver> — <date>` heading followed
> by `- ` bullet lines. Newest first. Keep the heading grammar stable — a parser binds to it.

## 0.5.2 — 2026-07-21
- **Writing-style rules added to the always-on core.** A 21-rule block (Strunk & White-derived:
  active voice, positive form, concrete language, omit needless words, no filler openers, no
  fashionable words; multilingual — English + Italian) now ships in `CLAUDE.md`, so every session and
  every spawned subagent writes under it — builder and challenger alike. A one-line precedence guard
  keeps style subordinate to functional and workflow requirements (exact syntax, canary tokens,
  verbatim quotes, required option-blocks, methodology invariants). Installed verbatim; revisable like
  any rule. The full Strunk & White extraction was considered as a `METHODOLOGY.md` reference and
  dropped (no reader path; copyright exposure). Settled through the workflow over three challenge
  rounds; the benefit is an accepted, unmeasured steer, watched over time, not auto-detected.

## 0.5.1 — 2026-07-21
- **`/start-task` — a chat command to start a workflow task.** A new user skill (`skills/start-task/`)
  is the human-owned bootstrap: type `/start-task "<goal>"` in Claude's chat and it scaffolds any missing
  project docs, runs `workflow.py start` in Claude's own shell, and opens the Need step — no more typing
  the deployed `~/.claude/workflow/workflow.py` path (`~` never expanded in PowerShell/cmd). Manual-only
  by design: the flow stays agent-driven; only the bootstrap is typed.
- **`init-project-docs` now scaffolds workflow-ready docs.** Its OVERVIEW / DECISIONS / ARCHITECTURE
  skeletons carry the seeded `<!-- WF:anchor:<slug> -->` comments the workflow's `publish` requires, so a
  freshly-scaffolded repo can let the docs write themselves (previously the first publish refused — the
  anchors were only ever hand-placed). Guarded by a new `test_scaffold_docs.py`.

## 0.5.0 — 2026-07-21
- **The challenge harness stops overclaiming (M7).** The text a *challenger* reads no longer tells it
  things that are not true: gone are the claims that the challenger "knows only the bundle" and that a cold
  read is *forced* or *deferred to a later milestone*. The `rulebook.md`, `challenger.md`, and `cmd_prepare`
  prose now say what the harness actually does — it *surfaces* a cold read for an agent that arrives
  pre-injected (global + project `CLAUDE.md` + the project memory index), it does not force one. A single
  canonical block, held consistent across the two shipped copies (and guarded by a cross-file test), tells
  the challenger the true shape: it starts isolated (no main chat, none of the builder's private reasoning),
  judges the cold section on its written record, and holds any injected operator memory — habits,
  preferences, or facts — for the warm pass.
- **`OPERATOR.md`'s two false platform claims corrected**, and the redundant **`global_habits` warm slot
  retired** (`warm_sources = ["operator"]`; the `.workflow/.gitignore` `start` writes is now a total ignore).
- **The orphan `context_hash` receipt field removed** — it hashed a bundle that contained the random canary,
  so it was unreproducible and read by nothing. A receipt is now `{challenge_ran, artifact_hash, canary}`;
  the tolerant reader still reads pre-0.5.0 receipts, so no migration is needed.

## 0.4.0 — 2026-07-17
- **The six-step adversarial workflow now ships and runs.** The machinery built across M1–M5 (never
  versioned until now) is deployed by `sync.py` and activated per-machine with `python sync.py
  enable-workflow`: a task walks Need → Design → Architecture → Implementation → Judgment → Shipping,
  a separate *challenger* AI attacks each step, and a deterministic script gates advancement and
  writes the docs. It stays **off** until you run `python workflow.py start "<task>"` in a project — no
  marker, no workflow. The control layer adds a workflow-aware status line (`wf:<step>:<state>`) and a
  soft `SessionStart`/`UserPromptSubmit` nudge when a step owes a challenge.
- **`sync.py` deploys whole directories instead of a per-file list.** The hand-maintained `MANIFEST`
  is retired for a **named directory whitelist walked from disk**: four bundle directories
  (`skills/ agents/ hooks/ workflow/`) ship wholesale plus six named root files, so a file dropped
  into a named directory now ships automatically — no code edit (this closes the old "the list can't
  express a directory" gap). A coverage gate fails loud: a stray, un-named top-level entry under
  `claude/` **halts** install (deploy nothing) until you classify it; a named entry missing from disk
  is **reported** and exits non-zero (the rest still ships). `install`/`capture`/`status` now return a
  real exit code, so `python sync.py` is loud on any anomaly; `capture` reports live-only *orphans* as
  information (exit 0) and never pulls them.

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
