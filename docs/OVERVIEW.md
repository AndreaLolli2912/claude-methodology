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
| 5 | Active adversarial workflow (six steps + a challenger) that makes the rules *run* | Building — M1, M2, M3 passed; **M4 (complete the step set) passed as sliced** — the six-step machinery exists, 124 checks green. **M5 (control layer) open: Steps 1–3 (Need, Design, Architecture) settled** — the **two** ambient pieces (status line + nudge; the skip-warner dropped on measured evidence → M7) + the rooting fix, ending in a live install. Nothing fires automatically and nothing is deployed yet (M5 + M6) (`docs/WORKFLOW.md`) |

## Current status

<!-- WF:anchor:current-status -->

<!-- WF:need:796664b9:start -->
**2026-07-15** — **M5 (control layer) — Step 1 (Need) settled.** Opened M5 and ran its Need on the real
machinery. **What M5 is:** the three ambient pieces that make the six-step workflow fire on its own — a status
line showing the current step *and* its honest `fresh`/`stale`/`missing` receipt state; a `UserPromptSubmit`
nudge telling the **model** (not the human) that a challenge is owed, once rather than every turn; a
`PreToolUse` warner on code written before Implementation — **plus the rooting fix without which none of them
can work**, the `sync.py` wiring, a live smoke-test, and **the install**.
- **The concrete blocker.** `workflow.py` line 40 is `ROOT = Path(__file__).resolve().parent`: every path — the
  marker, every draft — hangs off *the script's own folder* and ignores where you are standing. A global status
  line would hunt for the marker under `~/.claude/` and print "no task open" in every project, forever.
  **Reproduced live** in a hook prototype: it read the project path out of the payload correctly, then the import
  ignored it and found nothing. This is **RISKS #16 in a second place**, and the sandbox is the one shape where
  it does not exist — M3 and M4 ran in a single folder where script, docs and state sat together, so
  `__file__`-rooting worked and the defect never showed. Not a feasibility question: the platform hands the
  project path over on stdin. *Which* mechanism, and how `ROOT` stops being `__file__`-derived without breaking
  the settled CLI contract or the 124 checks, is Design's.
- **Human ruling — latency is NOT a design constraint.** Told a globally-installed hook costs **~140 ms per
  prompt and per file write in every repo**, including repos with no task open: *"why should I fucking care about
  losing 0.1 seconds? I can work in as many repositories as I like."* Now in `OPERATOR.md`. Inertness stays
  non-negotiable **as a behaviour** — no marker, no sound — but its cost is accepted, which points Design at the
  simple answer (one global install) and keeps his existing status line working. The ruling killed an absolute
  **the document had invented and the operator never asked for** ("must feel exactly like plain Claude Code"),
  discovered unmeetable and then defended across rounds by three separate wrong latency budgets.
- **Scope out, recorded.** **RISKS #15** — needs re-homing; it landed on M5 by date, not subject, and M5's honest
  effect is a narrow tilt the *wrong* way (the nudge makes the honest path's owed round arrive sooner while the
  cheap path stays as invisible as today). **RISKS #11** — inert, contingent on "no hook writes what the script
  owns"; reopens if Design proposes one. Plus M4's three deferred items, which M5 owes a *written home*, not an
  implementation.
- **The question Design must answer, and it is empirical:** which channel — if any — tells the human *why*
  **before** he answers. Ordering is the whole requirement; an explanation arriving after the write fails as
  completely as none. Four candidates, `systemMessage` most promising (a universal exit-0 field emitted *beside*
  `additionalContext` — one invocation, both audiences). **An honest fail is allowed:** the piece then ships as a
  pause with its limits recorded, or does not ship, and the human rules again on evidence.
- **Proof bar (11 items).** Rooting proven by measurement; each of the three signals proven **registered /
  executes / output honored** as three separate questions (in M2 a nudge passed two green unit tests while
  silently inert live); inertness proven by a **control**; the skip-warner's reason judged legible **by a naive
  reader on a captured artifact, with the reader's prompt recorded**; breakage observed with **no result written
  in advance**; latency **re-measured and recorded, not gated**; installed, used, reversible.
Converged clean on the **ninth** round (findings 7 → 8 → 5 → 4 → 5 → 3 → 1 → 3 → 0). Sandbox dogfood; live
`~/.claude` untouched; not committed. **Step 2 (Design) next.**

**Corrected 2026-07-16 (M5 Design D-6; six corrections applied to the Need draft):** M5 ships **two**
ambient pieces, not three — the `PreToolUse` skip-warner was dropped on measured evidence (no channel
puts a reason on screen at the moment of a permission decision) and re-homed to **M7**. The proof items
and the "which channel warns the human" question above resolve with it. Steps 2 (Design) and 3
(Architecture) have since settled — see the Decision Log and `ARCHITECTURE.md`'s `control-layer` section.
<!-- WF:need:796664b9:end -->

**2026-07-15** — **M4 (complete the step set) — COMPLETE. Step 6 (Shipping) settled; the six-step machinery is
built.** The Shipping challenger found **no blocking issues** and verified rather than accepted — it re-ran the
suite itself (124/124), read `sync.py`'s MANIFEST, and checked the diff stats against the claim. Its three
material findings are closed: the **self-hosting gap** recorded (RISKS #16 — `ROOT` is the script's folder, so
every live proof ran on byte-identical sandbox *copies*; "proven on the real docs" honestly means "proven on
their exact bytes"); the **rollback demonstrated** rather than argued (stashing all of M4 leaves a clean tree,
a parsing pre-M4 script, and 0 anchors in all three docs — so a revert is provably clean); and the **ephemeral
evidence trail** harvested into a durable PLAYBOOK recipe. Two minors → RISKS #17 (two writes raise a raw
traceback — accepted: they fail *loud*, never silently green). **The harvested lesson:** the live smoke-test is
what pays — budget for it every milestone, and verify every fix with a control. **M4 ships the publish engine +
four rows + 124 checks + the synced record; it is NOT deployed** (`sync.py`'s MANIFEST doesn't ship
`workflow/*` — RISKS #8, M6), so it has zero live blast radius. **M5 (hooks + status line) next**, inheriting
RISKS #15 and #17.

**2026-07-15** — **M4 (complete the step set) — Step 5 (Judgment) settled: GO. The live smoke-test passed and
paid for itself.** Discharged M4's one owed item — the dogfood had proven the chain with a *scripted*
challenger, so "end-to-end" only covered the deterministic half. Walked all four new rows with **real spawned
Sonnet challengers** in a sandbox seeded with copies of the real docs. Bar met on all five items: 4/4 challengers
echoed a fresh canary verbatim; every publish was byte-surgical (stripping the blocks reproduced all three
originals exactly); **twelve real refusals**; the three publishing rows advanced through the gate without
`--force`. It found **two things 121 deterministic checks could not** — a scripted challenger does only what it
is told, a live one reads its whole environment. **Fixed:** `prepare` never cleared the previous round's
`challenge.md`, so two live challengers read the prior verdict and reported it back as "corroboration" —
contamination dressed as independent confirmation (the mirror of the entry bug, one file over; proven with a
control against the pre-M4 script). **Documented (RISKS #15, deferred to M5):** later steps challenge a record
that lacks every earlier correction, because `prior_settled` feeds the *drafts* while corrections live in the
*entry* — and folding one back into a draft flips its receipt stale. Not a code bug; its fix reopens a settled
design decision. **124/124 on 3.12.7.** Sandbox only; not committed. **Step 6 (Shipping) next — the commit.**

**2026-07-15** — **M4 (complete the step set) — Step 4 (Implementation) built + settled.** The publish subsystem
is built (the data-driven `_place_block` engine + the four review rows + migrated tests + seeded real docs) and
hardened by a full Step-4 red-team: the team of attackers plus four convergence rounds found and fixed **eleven
blocking defects** — an ungated publish, a stale/cross-scope entry publish, and the code-fence fail-closed guard
defeated five ways (cross-validated against the CommonMark reference parser by the round-4 red-team). **121/121
checks on Python 3.12.7**, including a committed read-only test proving the real docs are valid publish targets
(unmutated). Caveat: the four new rows' end-to-end tests exercise the *deterministic chain* only — a live
real-challenger smoke-test against a new row is owed. By hand; sandbox only; not committed. **Step 5 (Judgment) next.**

**2026-07-14** — **M4 (complete the step set) — Step 3 (Architecture) settled.** By hand; a fresh challenger
attacked the internal structure over **two rounds** (grep-verified against the real code/docs), converging
clean. Settled: one `_place_block` core (identity-match + fail-closed guard + replace) with a 2-way insert
(`prepend` for logs; `append_section`, stable order, for reference sections); publish schema `{mode,
doc_target, block_key, anchor_slug}`; `--new`/`--update` intent for section writes (fail-closed on mismatch;
the wrong-valid-slug residual accepted as human-diff-gated); **both** halves of RISKS #12 (fence carve-out +
key-agnostic entry guard); manual one-time anchor seeding with concrete placements; the old publish path
retired; an honest test migration. **Step 4 (Implementation) next** — the code. Not committed.

**2026-07-14** — **M4 (complete the step set) — Step 2 (Design) settled.** M4's Design step ran **by hand**
(the `design` row is one of M4's own deliverables; the machinery dogfood resumes per-row at Implementation).
A fresh challenger attacked over **three rounds** against the real `cmd_publish` and docs — breaking three of
four first-draft recommendations, then converging clean. Settled: **one sentinel engine** — both-ends-identity
markers `WF:<key>:<scope>:start/end` parameterized by `(scope: task_id | section-slug) × (placement: prepend |
replace-or-create)` — covering **log-accumulate** (fixes the cross-task clobber) and **sectioned
replace-or-create**; **seeded per-location anchors** (`WF:anchor:<slug>`, not fragile headings); **Shipping
publishes nothing** (a second exception; its docs stay human-curated); the cold bundle unchanged. Proof #4
amended (Shipping proves through `record` only). **Step 3 (Architecture) next.** Not committed.

**2026-07-14** — **M4 (complete the step set) — Step 1 (Need) settled.** Opened M4 and ran its Need step as a
dogfood **on the real M3 machinery** — the first non-toy run of `workflow.py` (`start → prepare →` a real
challenger over **three rounds** `→ record → publish → advance`), the canary/receipt honest floor live throughout.
- **Scope (human-sliced this session):** build the **four remaining review-style rows**
  (`design`/`architecture`/`judgment`/`shipping`) as data, and generalize `publish` to the document **shapes**
  they truly write — **log-accumulate** (a dated-log prepend that accumulates across tasks) and **sectioned
  replace-or-create** (region-anchoring). **Deferred, recorded:** Step 4's built-in-tool attacker team, the
  research-helper, and forcing the cold read (α-2); the deferral criterion is *mechanism* (a genuinely different
  attack mechanism), not effort.
- **A real bug the challenge surfaced:** M3's `need → OVERVIEW` publish matches its block by sentinel **key
  alone**, so a *second* task would clobber the first task's entry — `need → OVERVIEW` is itself a log-accumulate
  target (RISKS #12). M4's log-accumulate mode fixes it while preserving the proven single-task behaviour.
- **RISKS #12 fence half (human ruling):** the residual "sentinel-shaped line inside a code fence" path is made
  **fail-closed (refuse), never a silent overwrite**; full fence-aware parsing stays a narrowed, still-open risk.
- **Proof-of-success:** every new mode proven surgical at the **byte level** on real docs (LF + CRLF, cross-task
  no-clobber, fail-closed on malformed input); each of the four steps dogfooded end-to-end; the 44 checks stay
  green + new tests, on Python 3.12.
- **Open for Design/Architecture:** the log-accumulate mechanism (task-scoped sentinels?), region-anchoring
  bounds + create-if-absent, Shipping's scope + cross-file partial failure, and whether the growing cold bundle
  needs a selection policy.
Converged clean over three challenger rounds (findings 9 → 2 → 0). **Step 2 (Design) next.** Sandbox dogfood;
live `~/.claude` untouched; not committed.

**2026-07-14** — **M3 (walking skeleton) — Step 4 (Implementation) built + proven.** The production
Need-slice machinery is built and passed its bar end to end. `workflow.py` (the M2 spine hardened + the
two-halved `RECIPE`, the α-1 `prepare`, the fail-closed `publish` verb, a `record` TOCTOU guard), plus the
extracted `rulebook.md`, `challenger.md`, `conductor.md`; a harness drift-guard and three test suites
(**44 checks**) round it out. Built in small blocks, each red-teamed by the Step-4 **team of attackers**
(four context-free lenses + a fidelity attacker), with a **second adversarial round** verifying the fixes —
which caught real defects (a Windows CRLF flip, sentinel corruption, a non-ASCII crash, a `record` TOCTOU, a
case-collision) and even a Python-3.12-vs-3.13 API trap the tests exposed. Proven on a toy Need over **three
real challenger rounds** that genuinely converged: each revision staled the receipt and blocked `advance`
until re-challenged (proof #1), `publish` re-settled idempotently to one block (proof #2), the forced-failure
suite covers the three `record` modes (proof #3), and replication-readiness holds for all five review-style
steps (proof #4). Residual minors → RISKS #10–12. **All in the isolated test project; live `~/.claude`
untouched; not committed. Next: M4.** Detail in DECISIONS (2026-07-14).

**2026-07-14** — **M3 (walking skeleton) — Step 3 (Architecture) settled.** The thin Need-slice structure,
settled over **three challenger rounds** (Sonnet, resumed; converged clean). Two human decisions: **A-1** —
the script bundles the extracted nine-rule rulebook into the challenge package, so the rules are guaranteed
present in the one file the challenger provably reads (over A-2's model-mediated path-read, a silent miss);
**D-1** — a new `publish` verb owns the settled-doc write (model drafts prose, verb places it between
markers and refuses rather than corrupt a malformed doc), leaving the M2-settled verbs untouched — the same
"don't churn settled contracts" principle as last step's α-1 (over folding it into `advance`/`record`). The
challenger's central catch, landed **twice**: the "add one row per step" replication promise over-generalized
— now honestly bounded, with the challenge spine frozen for the **five review-style steps** and both recipe
halves naming **Step 4 (Implementation)** as their exception → M4. Full rationale in DECISIONS (2026-07-14).
Architecture is written into `ARCHITECTURE` ("M3 walking skeleton — the Need slice"). **Step 4
(Implementation) next.** Not committed yet.

**2026-07-14** — **M3 (walking skeleton) — Step 2 (Design) settled.** Chose **α-1** (ordered-visible
cold/warm delivery — the challenger reads one bundle and returns cold-then-warm verdicts; honestly
*surfaces* whether a cold read happened, does **not** force it; forcing deferred to an observable
trigger — warm-set growth or the M4/M5 control layer — anchored on the WORKFLOW M4 build-plan line)
over α-2 (presence-sequenced *forcing*, which would extend the M2-settled `prepare`/`record`/gate
contracts). Chose **β-2** for auto-docs (the model drafts the settled-Need prose; the script places it
between sentinel markers — prepend-newest-first on first write, replace-in-place on re-settle;
structural idempotence meets proof #2). Converged over **three challenger rounds**; the recommendation
**flipped α-2 → α-1 mid-cycle** when the challenger disclosed α-2's settled-verb cost — the adversarial
process working as designed. Full rationale + the conscious *no-clean-trace* acceptance in DECISIONS
(2026-07-14). **Step 3 (Architecture) next.** Not committed yet.

**2026-07-14** — **M3 (walking skeleton) — Step 1 (Need) settled.** Opened M3: build the *real*
machinery for ONE step (Need), thin but complete, to prove the builder -> challenger -> judge ->
auto-docs pattern before replicating it for the other five steps (M4). Run as the six-step dogfood;
**the Need settled after five challenger rounds** (findings converged 11 -> 4 -> 1 -> 0-clean).
- **What the Need-step skeleton must do:** conduct the Need loop from the marker + conductor
  (survey -> draft -> `prepare` context -> spawn challenger -> `record` -> human settles ->
  `advance`); extract the nine challenger rules into **one shared rulebook**; assemble
  **verified-correct challenger context** with an *honest* cold/warm split (the canary proves the
  context was *read*, not that both passes ran); spawn **one adaptable attacker**; write an **honest
  receipt** with a load-bearing failure path (no false green); **auto-write the settled Need into
  `OVERVIEW`**; **gate advancement** on a fresh receipt; ship **production-quality, bundle-destined
  code** proven in an **isolated test project** first.
- **Not in M3** (scoped out): the other five steps and region-anchoring (M4); the ambient surface —
  status line, both hooks including the nudge, and the skip-warner (M5).
- **Proof-of-success:** end-to-end on a toy Need task over >=2 rounds (a revised draft stales the
  prior receipt and *blocks* advance until re-challenged); auto-docs idempotent; all three `record`
  failure modes read honestly missing/stale; replication-ready (a single-writer step needs no
  hash-gate edit; a shared-doc step needs region-anchoring — M4).
- **Key judge calls:** nudge -> M5; auto-docs `OVERVIEW`-only; region-anchoring reopened M3 -> M4
  (trigger is *single-writer vs. shared*, not in-place-vs-log). Full detail + the reopen in DECISIONS
  (2026-07-14). **Paused before Step 2 (Design)** at a clean checkpoint; not committed yet.

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
