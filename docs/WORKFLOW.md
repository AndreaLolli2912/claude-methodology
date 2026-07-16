# Workflow — the phased, adversarial way of working

> **What this is:** the design for turning the personal methodology from *rules you read* into a
> *process that runs*. Every task walks six steps; at each, a **builder** proposes and a
> **challenger** attacks; the **human judges**; and the **docs write themselves**.
> **Maintenance:** this is a design spec, **not yet built** — the source of truth for that build.
> Update it whenever a decision here changes, and log the change in `DECISIONS.md` (P1).
>
> **Status (2026-07-15):** theory complete and agreed. **M1 (validate by hand) passed**; **M2
> (technical design + de-risk) passed** — the machinery is designed (see `ARCHITECTURE` "Workflow
> machinery"), de-risked by a throwaway spike, and **live-smoke-tested** (all three hooks/status-line
> fire in a real session; the test caught and fixed a nudge that was silently inert). **M3 (walking
> skeleton): passed** — the Need-slice machinery built and proven end to end on a 3-round toy-Need
> dogfood, red-teamed over two clean rounds. **M4 (complete the step set): PASSED as sliced
> (2026-07-15)** — all four remaining review rows + the generalized publish engine, 124 checks, eleven
> blocking defects fixed, and a live real-challenger smoke-test that caught two more (see the **Build
> plan** M4 line for what was deliberately deferred out of it). **The six-step machinery now exists and
> works — but nothing runs it automatically and nothing is deployed: that is M5 + M6.** **M5 (control
> layer) is open: Step 1 (Need) settled 2026-07-15** — the three ambient pieces *plus* the rooting fix
> that turns out to be the real blocker, and ending in a live install rather than a sandbox proof.
> **Step 2 (Design) next.** Lessons folded
> into the challenger rules below:
> operator context (rule 6) and effort triage (rule 7) from M1; and from **dogfooding M2** —
> attack-anything / defend-from-the-record plus the reopening cap (rule 3), full ranked findings with
> severity tags (rule 5), and the cold-then-warm two-pass read (rule 6).

## Context — why this exists
Today the methodology only *describes* good practice: rules sitting in `~/.claude/CLAUDE.md` and
`METHODOLOGY.md`, plus a few active pieces (the `init-project-docs` skill, an update-check hook, a
status line, and `sync.py`). The rules are good, but they don't *run* — following them depends on
remembering to.

This design makes them run. **Every task becomes a fresh conversation that moves through six steps.**
At each step a **builder** (an AI that proposes) is challenged by a **challenger** (a separate AI
whose only job is to prove the builder wrong). The **human is the judge**: nothing passes to the next
step until it has survived the challenge and the human accepts it ("settled"). As the work proceeds,
the **decisions and documents write themselves**. Most of this is already latent in the written
methodology; the genuinely new ingredient is the **challenger**, which exists nowhere today.

## What the methodology codes mean (so this doc stands on its own)
Steps and rules below reference the personal methodology by short code. Full meanings:

- **OODA** — the operating loop: **O**bserve (gather) → **O**rient (make sense of it) → **D**ecide
  (choose) → **A**ct (build/test) → repeat.
- **R1 — Disambiguate first.** When something new comes up, question it across several rounds
  *before* proposing or building.
- **R2 — Decide nothing by assumption.** Put up grounded options (pros/cons + a recommendation) and
  get agreement; never choose silently.
- **R4 — Feasibility experiment.** Gate risky work behind a small throwaway trial that tests the
  risky assumption first.
- **P1 — Dated decision log.** Record what changed and why, newest first (`DECISIONS.md`).
- **P2 — Docs in sync.** Update the affected docs in the *same* change; docs never lag the code.
- **P3 — Reusable know-how.** Capture transferable recipes, separate from history (`PLAYBOOK.md`).
- **P4 — Separate the data-moving layer from the logic.** Keep wiring/input/output apart from the
  parts that do the real work.
- **P5 — Stable contracts.** Fix the interface between parts; make one side own all conversion.
- **P6 — Risk register.** Keep a living list of things that work now but bite at deploy/scale
  (`RISKS.md`).
- **P7 — Exploration vs delivery.** Keep the experiment environment separate from the production one.
- **D1 — Write for the reader.** The simplest thing that works, at the reader's level.
- **D2 — Comment to teach.** Every block explains *how* it works and *why* it exists, for a
  non-expert.
- **D3 — Self-explanatory names.** No cryptic abbreviations or jargon as identifiers.
- **T1 — Preserve experiments.** Keep each throwaway trial and a short write-up of what happened.
- **T2 — Proof-of-success up front.** State how you'll know it worked *before* you start; confirm
  against it at the end.
- **T3 — Validate on realistic input, then live.** Test on representative data; confirm under real
  conditions.

## The six steps
| # | Step | Rooted in | Builder proposes | Challenger attacks | Writes itself into |
|---|------|-----------|------------------|--------------------|--------------------|
| 1 | **Need** | R1 (disambiguate the requirement) | what's truly needed — for you or the end user | hunts for needs you left out or never said aloud, the things it must **NOT** do, who the real user is, and false assumptions about the problem | `OVERVIEW` |
| 2 | **Design** | R2 (grounded options), R4 (test risky bets) | a few real options, each with its reasoning | argues against each option: why it may be the wrong choice, the trade-offs you're quietly ignoring, and a stronger bet you haven't put forward | `DECISIONS` |
| 3 | **Architecture** | P4 (separate wiring from logic), P5 (stable contracts) | a structure drawn from known patterns | asks whether the textbook pattern truly fits *your* constraints, and flags cargo-cult pattern-matching — reusing a shape because it's familiar, not because it's right here | `ARCHITECTURE` |
| 4 | **Implementation** | D1–D5 (readable, commented code), T1–T3 (real tests) | small blocks; each one coded, tested, and commented | red-teams each block for bugs and unhandled edge cases, code that's hard to follow, and missing or shallow tests — plus whether it truly matches the agreed Need and Design | code, tests, `DECISIONS`/`PLAYBOOK` |
| 5 | **Judgment** | T2 (prove success), T3 (confirm live) | the evidence that it meets the Need | attacks the *proof of done* — "you only tested the happy path", "you never actually confirmed need X" — so the go/no-go call rests on real evidence, not optimism | `OVERVIEW` status + verdict |
| 6 | **Shipping** | P6 (risks), P7 (delivery env), P3 (reusable recipe) | deploy / hand off, and harvest the lesson | probes what "works in the chat" but breaks in the real world: behaviour under real load and scale, rollback, baked-in environment assumptions, failure modes | `RISKS`, `PLAYBOOK`, release |

**Judgment is the *macro* verdict** — does the finished thing solve the Need we wrote at the very
start? — as distinct from the small *micro*-judgement the human makes at every step.

## Ground rules
- **The challenger is a separate AI (a subagent).** Independence is *the mechanism* that lets it
  catch what the builder can't see: less shared context means fewer shared blind spots.
- **The human makes the calls.** The AIs propose and attack; the human decides and settles.
- **The *flow* is automatic — it is never driven by typed `/` commands.** Things fire on their own, by context
  or by event, because relying on someone to remember is the failure this whole design exists to remove.
  *(Narrowed 2026-07-15, M5. This read "Automatic, never typed `/` commands" — an absolute the system already
  contradicted: `start` **is** a typed command, the deliberate human-owned bootstrap M2 settled on purpose, and
  the M2 record itself carried the narrow wording "drive the flow with typed `/` commands". The rationale
  defends banning `/` for driving the flow; it says nothing about the **bootstrap**.)* **Open, with a test —
  not a maybe:** whether the bootstrap should become a `/start-task` command. It would be strictly friendlier
  than typing `python claude/workflow/workflow.py start "…"`, and it violates nothing the rationale protects.
  **The operator's criterion is usefulness** — *"we might accept `/` commands if we find them useful"*, *"if it
  solves ambiguity or makes the tool better"* (2026-07-15). That criterion is **empirical, so this is not
  decidable now**: nobody has typed the long form on real work yet, because nothing is deployed. **Decision
  point: M5's Judgment step** — the first moment real-use evidence exists, since M5 ends installed and used
  (M5 proof item 10). **Not decided.**
- **Docs writing themselves is a hard requirement**, not a nice-to-have.
- **The observer is the human.** (A neutral observer *AI* was considered and set aside — the human
  already fills that seat.)

## The challenger — how it behaves
A second, *separate* AI whose only job is to prove the builder wrong. It works only if it stays
independent: a different AI, and one **not** told the builder's private reasons (or it gets talked
into agreeing). Its nine rules:

1. **Points, doesn't build.** Names the problem and gestures at a better direction — but does not
   write the fix itself (that would turn it back into a builder and cost its fresh eyes).
2. **Fair and focused.** Attacks the *strongest* version of the idea, no cheap shots; reports only
   the problems that actually matter, not nitpicks.
3. **May attack anything relevant; a settled decision is defended from the record.** It works the
   current step, but nothing earlier is off-limits if it bears on the work in hand — being *settled*
   protects nothing; being *defensible from what we wrote down* is what protects a decision. Attack a
   settled call and one of two good things happens: we defend it by pointing at its recorded rationale
   (it comes out re-proven), or we can't — and then it *should* reopen, usually because the real reason
   lived in someone's head and never reached the docs (the M1 lesson, generalized). Two guardrails stop
   this from thrashing. **The human judge — not the challenger — rules** whether the record held and
   whether to go back (the challenger is rewarded for reopening, so it doesn't referee its own attack).
   And **reopening is capped:** a reopened decision gets *one* round by default, not the full treatment,
   unless the human escalates; and the cascade **stops at one hop** — the reopened decision's dependents
   are flagged for the human to look at, not auto-re-attacked.
4. **Warns, never blocks.** It raises flags; a serious unresolved flag must be *consciously cleared*
   by the human before moving on. The human can debate the challenger directly.
5. **Attacks in multiple rounds until a clean one — and reports everything, ranked.** Builder and
   challenger go back and forth over several rounds, each drilling into the last, until a whole round
   turns up nothing new that matters — then the human accepts and it's settled (same stop-rule as
   **R1**). Each round the challenger returns its **full list of findings, every one tagged blocking /
   material / minor** (blocking = breaks a stated need or invariant; material = adds real cost or risk
   without breaking one; minor = style / nice-to-have). Only **blocking and material** findings keep
   the rounds going; **minor** ones drop into an appendix and never spawn a new round — so "report
   everything" can't turn into an incentive to pad the list with trivia to avoid an empty-looking round.
6. **Fresh each step; reads only the written record.** Starts clean and sees only the *thing being
   judged plus the settled docs* — never the builder's private thinking. So the self-writing docs do
   double duty: the memory of decisions *and* the challenger's unbiased reading material. The record
   it is handed also includes **`OPERATOR.md`** — how the developer actually works — because a
   subagent inherits **none** of the main chat's memory: anything tacit (a working habit, an
   environment quirk) is invisible to it unless written down and passed in. M1 proved this the hard
   way — the fact that reshaped the whole task lived only in the human's head, so the *human*, not the
   challenger, caught it. The rule underneath: **the challenger is only as sharp as the written
   context it is handed.** **Two passes, cold then warm.** Context both sharpens *and* anchors — hand
   over the operator facts and the challenger catches habit-specific flaws but can glide past plain
   logic bugs (dogfooding M2, a context-fed run called a self-contradictory proposal "coherent"). So
   it reads in two passes: first a **cold read** of just the thing being judged plus the settled docs
   — fresh eyes, and a test of whether the decision stands on the written record alone — then a **warm
   pass** with `OPERATOR.md` and the assembled context added, for the habit- and domain-specific flaws.
   One challenger does both, in that order; a genuinely separate second challenger is spun up only when
   the two passes sharply disagree, never by default (that would just double the slow part for little
   gain).
7. **Matches effort to novelty — weight set deliberately, not by default.** A well-worn,
   obviously-right choice gets a *quick* "does it fit our situation?" check; a genuinely new choice
   gets the full multi-round attack. Familiar never means unchecked — just a lighter check. (Same idea
   as **R1**.) M1 showed this rule doesn't fire on its own — it ran near-full rounds on a familiar
   feature and felt heavy for the size. So a task (and each step) **opens with a quick
   size-and-novelty read that sets the expected number of rounds**: a one-file, familiar change starts
   light and escalates only if the challenger actually finds something; a genuinely new subsystem
   starts heavy. The weight is *chosen* up front, never assumed to be "full".
8. **Calls for an experiment when arguing can't settle it.** When a crux depends on a real-world
   fact about *our own thing* ("is it fast enough?", "does it hold at scale?"), it stops debating
   and calls for a small throwaway experiment (**R4**). The *builder* runs the probe; the result is
   the deciding vote.
9. **Calls for research when nobody actually knows.** If builder, challenger, and human are *all*
   unsure — nobody knows the fact, the best practice, or how a tool really behaves — more debate
   won't help, because the two AIs share training blind spots and can be confidently wrong about the
   same thing. A **research helper** (a subagent using web search/fetch) pulls in real context,
   which then re-enters the loop and is vetted like anything else — no blind trust. (Rule 8 tests
   *our thing*; rule 9 looks up *the world's* knowledge.)

## Each step in detail

### Step 1 — Need
- **Purpose:** pin down what is *truly* needed — for you, or the person you're building for — before
  any design or code.
- **Two modes:**
  - *Brand-new project:* the builder drafts the need from scratch.
  - *Existing project:* an extra first move — **survey what's already there and rank what matters** —
    then draft the need on top of it. (You can't state the real need for a system that already exists
    without first understanding what's true about it.)
- **How it goes:** builder drafts the need → challenger attacks in rounds (what's missing? what must
  it NOT do? who is it really for? what's assumed that might be false? — and, for an existing project,
  "what did you overlook or wrongly treat as important?") → the human decides each round → repeat
  until a round finds nothing new → settled.
- **Writes into:** the settled need → `OVERVIEW`, **plus how we'll know it's delivered**
  (proof-of-success, **T2**) so Judgment later has a concrete bar. The existing-project survey seeds
  `ARCHITECTURE` (Step 3 refines it), so no document repeats another.

### Step 2 — Design
- **Purpose:** decide *what* to build and *why* (the approach) — before worrying about internal
  structure.
- **How it goes:** builder puts up **a few real options**, each with its reasoning and trade-offs →
  challenger argues against them (why each could be wrong, the trade-offs being glossed over, a
  better bet not yet considered) → the human debates and makes the call → rounds until settled.
- **Effort scales to novelty** (challenger rule 7): familiar choices get a quick fit-check; new ones
  get the full attack. (Applies here *and* in Architecture.)
- **Writes into:** the choice, *why* it was made, and *why the other options lost* → `DECISIONS`.

### Step 3 — Architecture
- **Purpose:** decide *how it's structured inside* — the parts, how they're split, the boundaries
  between them (**P4**: keep the data-moving layer separate from the real work; **P5**: fix stable
  contracts between parts).
- **How it goes:** builder proposes a structure from known patterns → challenger attacks *fit to
  your circumstances* (effort scaled to novelty) → the human decides → rounds until settled →
  `ARCHITECTURE`.
- **On "is it the best?":** we can't prove *best* — only that it survived a real attack and genuinely
  fits. For cruxes reasoning can't settle (speed, scale), the challenger calls for a cheap experiment
  (rule 8) and the evidence decides.

### Step 4 — Implementation
- **Purpose:** build the thing in **small blocks**, never one big lump.
- **The block loop (repetitive on purpose):** build a block → test it → the attackers red-team it →
  if it passes, it's settled; if not, find out *why* and fix it **before moving on**. A broken block
  is never left behind for the human to trip over. Rounds per block until settled.
- **Mandatory for every block:** a test (**T2/T3**), comments explaining *why* (**D2**), and simple,
  readable code (**D1/D3**).
- **A team of attackers:**
  - *Built-in, context-free* — Claude Code's own `code-review` (bugs), `verify` (does it actually
    run and behave), `simplify` (readability), `security-review` (safety). Reused as-is for now.
  - *Custom, context-aware — a "fidelity" attacker (a subagent, outside the built-ins).* It reads the
    settled docs (rule 6) and checks what the built-ins can't: does the block deliver the settled
    Need and Design? does it respect the agreed boundaries (**P4**) and contracts (**P5**)? do its
    tests cover the failure modes we flagged, on realistic input? are the why-comments and names
    clear to a non-expert? In short — the built-ins own *"is this good code?"*; the custom attacker
    owns *"is this the code we agreed to, written to our standard?"*
- **Even here, rule 1 holds:** the attacker *points precisely* (like a review comment); the builder
  writes the fix.
- **Writes into:** the code and its tests; lessons → `DECISIONS`/`PLAYBOOK`.

### Step 5 — Judgment
- **Purpose:** the **macro** verdict — hold the finished build up against the **Need from Step 1**.
  This closes the loop (the "re-Observe" of **OODA**: did the act achieve what we set out to do?).
- **How it goes:** builder presents the *evidence* it meets the Need → challenger attacks the *proof*
  ("happy-path only", "need X never confirmed") → the human decides **go / no-go**; a no-go sends the
  work back to whichever earlier step actually failed (rule 3 regression).
- **Success bar set early, checked here:** the proof-of-success (**T2**) is agreed back in
  Need/Design and written down then; Judgment *verifies* against it, never invents it at the end.
- **Writes into:** the verdict + a `OVERVIEW` status update (done / not done, against the Need).

### Step 6 — Shipping
- **Purpose:** deliver the finished, judged thing to the real world; harvest the reusable lesson
  (**P3** → `PLAYBOOK`); and **persist the work** — the actual *saving somewhere*.
- **How it goes:** builder prepares delivery → challenger attacks *real-world readiness* ("works in
  the chat ≠ works in the world": load, scale, rollback, environment assumptions, failure modes).
- **Two kinds of output:** (1) fix-before-you-ship blockers, resolved now; (2) risks that can't be
  resolved now but will bite later → written into `RISKS` as documented, *accepted* risks (what it
  is, why it bites, what to do). Nothing is left un-fixed *and* un-known.
- **Terminal action:** generate the **commit message** and **commit/save the project** — the code
  plus the docs that wrote themselves. This is the last thing the task-conversation does.
- **Writes into:** `RISKS`, `PLAYBOOK`, the release/`CHANGELOG`, and the commit itself.

## The conversation lifecycle (why "a fresh chat per task" works)
Each task is **one fresh conversation**; the six steps run inside it; Step 6 **commits everything**.
The next task is a **new conversation** with no memory of the last — so the only context it inherits
is **what was committed** (the self-written docs + code). The commit is the **hand-off between
conversations**: the docs *are* the memory, and a new task's Need step (existing-project mode) begins
by surveying exactly those committed docs. This is why "docs write themselves" is load-bearing, not
cosmetic — they are the *only* thing that survives into the next task.

## The challenger: one rulebook, a specialist per step
Not one generic critic, and not a pile of unrelated ones, but **one shared rulebook (the nine rules)
worn by a different specialist at each step.** The attack *target* changes down the line — missing
needs → wrong design → poor fit → broken code → thin proof → not deploy-ready — while the *rules*
stay the same. It is built as **per-step attacker subagents** that all point at one shared rulebook
(kept in a single place, so it isn't duplicated six times — **P5**); in Step 4 the built-in tools
join them. Whether each specialist is a separate file or one adaptable agent is a build detail; the
*principle* — a specialist per step — is settled.

## The control layer — knowing the step, and keeping the flow honest
Per-step specialists only work if something knows *which step we're in* and keeps the flow honest.
Three jobs:
1. **Awareness (know the current step).** The real source of truth is the **docs** — which ones are
   filled and settled tells you where you are — plus a live marker in the **status line**
   (`statusline.py`, already ours) so the current step is always visible.
2. **Dispatch (run the right specialist).** The always-on **core** (`CLAUDE.md`) is the conductor: it
   drives the stepped flow and brings in the right per-step attacker when that step is active.
3. **Enforcement (keep the flow honest).** A **hook** raises a *soft flag* when you skip ahead (for
   example, about to write code before Architecture is settled) — a reminder you consciously clear,
   **not** a hard block. This matches challenger rule 4 ("warns, never blocks"); the human keeps the
   wheel.

This is where all the primitives converge: the **core** conducts, **skills/subagents** are the
per-step builder and attackers, **hooks** do soft enforcement, and the **status line** shows the step.

## Build plan
Build order — each task small, tested (**T2**), logged (**P1**), and doc-synced (**P2**), so the
system is built by its own rules. **Each item is a fresh conversation that reads this doc.**
**Nothing heavy gets built before the flow is validated (M1) and the tech is de-risked (M2).**

- **M0 — Freeze & persist the design.** *(This document — done when it's committed to the repo.)* It
  makes "a fresh conversation reads the doc" actually work, and answers "will we lose the context?":
  no — it's a file, not chat memory.
- **M1 — Validate the flow by hand. ✓ PASSED (2026-07-13).** Ran a real task (`sync.py status`)
  through the steps manually (Claude as builder, a subagent as attacker, docs updated live), and it
  beat a normal chat on both counts: the challenger forced a throwaway experiment that killed an
  unsafe timestamp-based feature *before* it became code, and the questioning reshaped the feature
  from an overwrite-guard into a read-only readout — with docs that could resume a fresh chat. Two
  lessons fed back into the theory above: **(a)** the challenger was blind to a tacit working habit
  written nowhere → added `OPERATOR.md` + rule 6's "handed the written context"; **(b)** it was too
  heavy for a small task because rule 7 never fired → rule 7 now sets effort up front. Next → M2.
- **M2 — Technical design + de-risk. ✓ PASSED (2026-07-14).** Designed the machinery
  (one `workflow.py` script as the single independent author of every signal; a per-task marker; two
  read-only hooks; a status line — full map in `ARCHITECTURE` "Workflow machinery") and de-risked it
  with a throwaway spike. Proven off-session: the deterministic chain (marker lifecycle, fail-closed
  receipts, the gate, honest fresh/stale/missing) works every time with no false-green path; the
  challenger's context delivery is load-bearing (a with/without-context control). **Condition
  discharged (live smoke-test passed):** all three signals fire in a real session — status line, the
  nudge, the skip-warner — confirmed via a fire-probe (execution) plus isolation tests (output
  honoured). The smoke-test **caught a real bug the off-session suite missed**: the nudge was silently
  inert live, printing a bare `additionalContext` object instead of the required `hookSpecificOutput`
  wrapper (and the earlier same-day fix was also wrong); fixed and the test now asserts the real shape.
  Residual: firing is model-mediated (~70-80%, unforceable) *by design* — a miss is **visible**, not
  prevented (RISKS #9). Minor: the skip-warner's reason text doesn't surface in the dialog (an M3
  refinement).
- **M3 — Walking skeleton (one step, end to end).** The shared rulebook + one attacker subagent
  (start with Need) + the core conductor for that step + auto-docs for that step. Prove the pattern
  on one step before replicating. **Steps 1-3 settled 2026-07-14.** Step 1 (Need): Need chosen first;
  auto-docs writes OVERVIEW only; nudge -> M5; region-anchoring -> M4. Step 2 (Design): **α-1**
  ordered-visible cold/warm delivery (honest *surfaces*, not *forces*; forcing deferred — see M4) +
  **β-2** auto-docs (model drafts, script places between sentinels). Step 3 (Architecture): **A-1** the
  script bundles the extracted rulebook into the challenge context (over a model-mediated path-read) +
  **D-1** a new `publish` verb owns the doc-write, leaving the M2 verbs intact; the "add one row per step"
  replication promise is honestly **bounded** — the challenge spine is frozen for the **five review-style
  steps**, and both recipe halves name **Step 4 (Implementation)** as their exception (its team-of-attackers
  + code-output) -> M4. Written into ARCHITECTURE ("M3 walking skeleton — the Need slice"). **Step 4 (Implementation)** then built
  the Need-slice code (`workflow.py` + `rulebook.md`, `challenger.md`, `conductor.md`), red-teamed it with
  the team of attackers over two clean rounds, and **proved all four proof items** on a 3-round toy-Need
  dogfood in the isolated test project (44-check suite; live `~/.claude` untouched). Next: **M4**.
- **M4 — Complete the step set. ✓ PASSED AS SLICED (2026-07-15).** *Delivered:* the four remaining
  review-style rows (`design`/`architecture`/`judgment`/`shipping`) as data, sharing one rulebook and a
  structurally-frozen challenge contract; **region-anchoring designed and built** (seeded per-location
  `WF:anchor:<slug>` comments); auto-docs for every publishing step via one `_place_block` engine
  covering both real shapes (log-accumulate + sectioned replace-or-create). Proven by **124 checks** and
  a **live real-challenger smoke-test** (4 real subagents, one per new row). Eleven blocking defects
  found and fixed by the red-team; the live run found two more the green suite structurally could not.
  *(DECISIONS 2026-07-15 ×2; ARCHITECTURE "M4 — the publish engine"; RISKS #15/#16/#17.)*
  **Deliberately deferred OUT of M4 (still open, not yet re-homed to a milestone):** (a) wiring the
  built-in tools into Step 4's attacker team, (b) the research-helper, (c) **forcing the cold read**
  (α-2). Deferral criterion was **mechanism, not effort** — the Implementation team is a genuinely
  different attack mechanism with an open feasibility question, whereas the four review rows shared the
  prose-challenger mechanism and were cheap. **Decide where (a)-(c) live before M5 closes.**
- **M5 — Control layer. Step 1 (Need) settled 2026-07-15** (clean on the ninth round; DECISIONS + OVERVIEW
  2026-07-15). What makes the machinery *fire on its own* — today every verb is typed by hand or by the model
  reading `conductor.md`. **Three ambient pieces:** a status line showing the current step *and* its honest
  `fresh`/`stale`/`missing` receipt state; a `UserPromptSubmit` nudge telling the **model** a challenge is owed
  (once, not every turn); a `PreToolUse` warner on code written before Implementation. **Plus the rooting fix,
  which is the milestone rather than a detail in it:** line 40's `ROOT = Path(__file__).resolve().parent` hangs
  every path off the script's own folder, so a global status line would print "no task open" in every project
  forever. That defect is **invisible in the sandbox** — M3 and M4 ran where script, docs and state shared a
  folder, the one shape in which `__file__`-rooting works — which is why it surfaces only now (RISKS #16, second
  place). Also in scope: `sync.py` wiring, a live smoke-test, and **the install** (the operator has ruled that
  "built but never deployed" is not an acceptable end state). **Human ruling:** per-event latency at the ~100 ms
  scale is **not** a design constraint — inertness stays non-negotiable as a *behaviour*, its ~140 ms cost is
  accepted (`OPERATOR.md`). **Inherits #17** (raw tracebacks get ugly under hooks) and **#11** (a
  compare-and-swap tripwire once a hook can auto-fire `publish`). **#15 is scoped OUT** — it is about the
  challenge record, not the control layer, and landed here by date rather than subject; it needs its own
  milestone, and M5's nudge tilts its cost asymmetry slightly the wrong way (RISKS #15 detail). **New: #18** —
  the canary proves a bundle was *read*, not *fresh*.
  **Step 2 (Design) settled 2026-07-15** — clean on the **eleventh** round (DECISIONS 2026-07-15). **M5 now
  ships TWO ambient pieces, not three:** the skip-warner is **dropped** on four measured grounds and re-homed
  to M7. Design's open empirical question got a measured answer, and it was not the expected one — *no*
  channel puts the reason on screen at the moment of decision (`systemMessage`, the Need's favourite, fires on
  `PreToolUse` and renders nothing; `permissionDecisionReason` reaches Claude, never the human; even
  `PermissionRequest`, which fires exactly *"when a permission dialog appears"*, carries no human-facing field).
  §5.3's honest-fail clause was invoked by human ruling. Settled: `BUNDLE` vs `PROJECT` (one name was doing two
  jobs); the CLI walks up (`.git` for `start`) and every verb prints its root; a separate `statusline_wf.py`
  the setting points at; the nudge quiet only on `UserPromptSubmit` with `SessionStart(…|compact)` always
  re-injecting; all task state in a self-ignoring `.workflow/`. **The hook's output contract is a whitelist,
  not a blacklist** — three rounds running, an enumeration of block routes missed a live one (`"ask"`, then
  `decision: "block"`, then universal `continue: false`), so the hook now emits two known-safe keys and any
  other key is a bug.
  **Step 3 (Architecture) settled 2026-07-16** — clean on the **sixth** round (blocking 2→3→1→1→1→0;
  ARCHITECTURE `WF:arch:control-layer`, DECISIONS 2026-07-16). **Both owed probes were run first and both
  answered:** `SessionStart` **fires and delivers** on the `compact` matcher (D-7 stands on measured
  ground; alternation works on this non-tool event), and project hooks **merge** with user hooks across
  every scope (D-1 cannot be silently disabled) — `CLAUDE_CONFIG_DIR` is real-but-undocumented, which let
  the user boundary be tested without touching live `~/.claude`. The rounds turned real seams: a
  cross-directory import that would blank the status line (renderer belongs in `claude/`, not
  `claude/workflow/`); a round-1 fix that removed a stat-before-import guard (caught round 2); D-8's
  unhomed `enable_statusline` change (a new-box re-run would wipe the `wf:` segment); the test suite's
  **subprocess** CLI calls that, un-aimed after the rooting change, would `reset` the repo's own live
  marker (fixed by `cwd=TMP`); and a broken-branch fail-loud that discarded its own warning (fixed by a
  stdlib-only terminal broken branch). **Human rulings:** the resolved root prints to **STDERR**; the
  **six Need corrections are applied now**, ahead of Implementation. **Owed, now in progress:** the six
  corrections (apply-now). *(Opportunistic-only, design leans on neither: auto- vs manual-compaction;
  `systemMessage` on SessionStart.)*
  **The three M4 debts are homed (M5 proof item 11):** built-in reviewers → **M7**; forcing the cold read
  (α-2) → **M7** (it bit live — every challenger this step held the two passes apart by discipline, not by
  the harness); the research-helper → **dropped**, because every probe this milestone ran on tools the main
  agent already has and nothing was blocked. A closing condition nothing tests
  is a wish.
- **M6 — Transport & packaging.** Grow `sync.py` to deploy whole `skills/ agents/ hooks/` directories
  (retiring the per-file manifest); update the `CLAUDE.md` core and `METHODOLOGY.md`; bump the
  version + `CHANGELOG`. Plain `~/.claude` bundle by default (personal use), not a plugin, unless we
  later choose to share it. *(M5's D-8 does **not** need this: it ships six named files, which the per-file
  MANIFEST expresses fine — verified. RISKS #8 stays M6's.)*
- **M7 — The challenge harness's own honesty.** Created 2026-07-15 by M5's Design, which owed the M4 debts a
  named home (§8.11: "a closing condition nothing tests is a wish"). Everything here is about **the fidelity
  of what a challenger is shown or attacked with** — one theme, unlike M5, which inherited these by date:
  - **Forcing the cold read (α-2)** — deferred out of M3, then M4, and now measured biting: `prepare` writes
    rulebook + COLD + canary + WARM into one file, and **the canary sits near the end of COLD**, so any read
    that reaches it also delivers WARM. Every challenger across M5's eleven rounds reported holding the two
    passes apart *by discipline, not by the harness*. `cmd_prepare`'s own docstring concedes it *surfaces*
    rather than *forces* a cold read. The fix reopens the bundle format (two files, or a canary that lands
    before COLD ends). `workflow.py:387` still says "deferred to M4", a shipped milestone.
  - **RISKS #15** — later steps challenge a record lacking every earlier correction. Re-homed here from M5,
    where it sat by date rather than subject. Same theme: what the challenger is shown.
  - **RISKS #18** — the canary proves a bundle was *read*, not *fresh*. Same theme again; M5's rooting fix
    closes its copy-drift half as a side effect and leaves the general half standing.
  - **Built-in reviewers into Step 4's attacker team** — M4's deferral criterion was *mechanism, not effort*:
    a genuinely different attack mechanism with an open feasibility question.
  - **The skip-warner** (dropped from M5 by human ruling on measured evidence — DECISIONS 2026-07-15), with
    M5's `"ask"` finding preserved: it **is** honored and **does** override a permission allow-list, proven by
    control. A future design can spend that once it has a channel that can explain itself — which today's
    platform does not offer on any of the three events that reach the moment of decision.
  - *Dropped, not re-homed:* **the research-helper**. Every probe in M5 ran on tools the main agent already
    has; nothing was blocked by its absence. Revisit only if a real task is.

**Still open, to decide when we reach them:** plain `~/.claude` bundle vs. plugin (M6). *(Resolved
since: one **adaptable** challenger file, not one per step — ARCHITECTURE; and skeleton the **Need**
step first — M3, 2026-07-14.)*
