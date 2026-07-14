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
| 5 | Active adversarial workflow (six steps + a challenger) that makes the rules *run* | Building — M1 (by-hand) passed; **M2 (design + de-risk) passed** — machinery designed, de-risked, and live-smoke-tested; **M3 (walking skeleton) next** (`docs/WORKFLOW.md`) |

## Current status
**2026-07-14** — **M2 complete: the live smoke-test passed, M3 unblocked.** The condition on M2's "go"
verdict — hooks and status line actually firing in a real session — is now met. Launched Claude Code in
the isolated spike and confirmed all three live: the status line (`wf: [need!]`), the nudge (injects the
challenge reminder), and the skip-warner (gates an early code write). The test **earned its keep** — it
first caught a real bug: the nudge was silently inert because it printed a bare `additionalContext`
object instead of the `hookSpecificOutput` wrapper Claude Code requires (and even the same-day earlier
fix was wrong); the unit tests passed through both because they asserted an *assumed* output shape.
Fixed and re-proven live. Honest caveat: the skip-warner gates but its reason text doesn't surface (a
generic prompt) — an M3 detail. The residual firing-rate risk (~70–80%, model-mediated, unforceable) is
unchanged and handled by design (RISKS #9). Full detail in DECISIONS (2026-07-14).

**2026-07-14** — **M2 (technical design + de-risk) is done — judged go-to-M3 *with conditions*.** The
machinery was designed (see `ARCHITECTURE` "Workflow machinery") and de-risked with a throwaway spike:
the deterministic chain (marker lifecycle, fail-closed receipts, the advance-gate, honest
fresh/stale/missing) works every time with no false-green path; a with/without-context control showed
the challenger's context delivery is load-bearing; and verifying the hook payload schemas against the
docs caught and fixed a real bug (a nudge that would have been silently inert live). **Condition for
starting M3:** a short live smoke-test — the hooks and status line actually fire in a real session, and
the marker's start→advance→reset transitions read from a fresh chat. Firing is model-mediated
(~70–80%, unforceable) by design; the machinery's job is to make a miss **visible**, not prevent it.
Dogfooding M2 also sharpened the challenger rules themselves (see `WORKFLOW.md` rules 3/5/6). Full
detail in DECISIONS (2026-07-14).

**2026-07-13** — Building the six-step workflow's own machinery (`docs/WORKFLOW.md`, milestone
**M2** — technical design + de-risk), run as a full six-step dogfood (builder + a fresh challenger
subagent per step + human judge). **Step 1 (Need) is settled** after three challenger rounds:
- **What it is:** machinery that makes the six-step workflow *run on its own* at the right moments
  instead of relying on memory, stays light on trivial work, and — because the parts that fire it are
  model-driven and will sometimes fail — treats its real job as making **every failure visible and
  hand-recoverable**, not firing perfectly.
- **Must do:** know the current step from an explicit **per-task marker** (not inferred from which repo
  docs are filled — those are already full across tasks), with a full lifecycle (created at task start
  by a deliberate human bootstrap, advanced when a step settles, reset between tasks; absent = inert
  here); show the step *and* whether the challenge actually ran (a receipt emitted by the challenger,
  never self-reported by the main model); auto-hand the challenger the correct context from a fixed
  recipe, verifiably; give step guidance at the right moment; soft-warn on skip-ahead (never block);
  write each doc *per type* (prepend the logs — DECISIONS/RISKS/CHANGELOG; update the living docs —
  OVERVIEW/ARCHITECTURE — in place), gated on human acceptance and self-contained for the next
  context-free subagent; be inert in non-workflow repos.
- **Must NOT:** drive the flow with typed `/` commands; hard-block; touch/corrupt the live `~/.claude`;
  feed the challenger empty/wrong context; nag in unrelated repos; commit or push without approval.
- **Entry is a human-owned bootstrap:** starting a workflow task is your deliberate act; not starting
  is a choice, not a silent failure — the visibility guarantees apply once a task is engaged.
- **Honest reliability model:** *deterministic* = detect/show the marker, deliver guidance text, write
  docs. *Model-mediated* (each can fail independently, so each needs its own visible signal or an
  honest "not done") = advance-on-settle, fire the challenger, assemble correct context, and
  act-on-guidance — this last has no signal of its own; it surfaces only via the challenge on the
  builder's output (the weakest link).
- **Proof-of-success (how we'll know M2 worked):** every model-mediated failure is visible and
  hand-recoverable — shown on a real task with a **planted flaw only an `OPERATOR.md`-fed challenger
  could catch** (plus a without-context control confirming the catch disappears), the challenger's
  *written output* getting the credit; the marker's **transitions** (start → advance → reset), not
  just a snapshot, working from a fresh chat; each event forced to fail to confirm the status honestly
  reads "not done" (never a false "it ran"); raw firing rate **made visible, not measured to a
  threshold,** on **natural** tasks as a secondary "how often you'd step in" signal. **M2 de-risks:** (a) the per-task marker lifecycle,
  (b) auto-firing with verified-correct context, and (c) whether the platform allows a **deterministic,
  un-forgeable capture** of what a subagent ran on (else receipts collapse to self-report). **M2 is now complete (2026-07-14 — see the top status entry).** Step 3
  (Architecture) settled 2026-07-14 (see DECISIONS + the "Workflow machinery" section in
  ARCHITECTURE): one `workflow.py` script is the by-convention sole author of every signal, with a
  per-task marker, two read-only hooks, and a status line, all isolated in a test project — and the
  challenge-ran light is now honest-**self-reported permanently** (cruxes (b)/(c) resolved by
  reasoning: a true "verified" is unreachable while the model spawns the challenger, so the spike
  tests only that the canary catches a wrong-context run).

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
