# Working Methodology (agnostic) — full reference

> The complete working agreement, independent of any language, framework, or tool.
> The **always-on core** (six invariants + the OODA loop) lives in `~/.claude/CLAUDE.md`
> and is loaded every session; **this** file is the full set, read on demand. Maintain it
> as a living document: when a rule proves wrong or missing in real use, revise it here
> and record why in the project's decision log.
>
> **Version 0.4.0** (2026-07-17). Deployed as: lean core → `~/.claude/CLAUDE.md`; this
> reference → `~/.claude/METHODOLOGY.md`; doc scaffolding → the `init-project-docs` skill;
> version + changelog + update-check hook → `claude/VERSION`, `claude/CHANGELOG.md`,
> `claude/hooks/check_version.py`; status line → `claude/statusline.py`; and the **six-step
> adversarial workflow** (below) → `claude/workflow/` + `claude/agents/challenger.md`, activated
> per machine with `python sync.py enable-workflow`. The workflow is the P1/P2 enforcement
> mechanism earlier versions only anticipated: it makes the invariants *run* on a task instead of
> relying on memory.

## How to read this
Two structures, on different axes:
- **OODA is the *verbs*** — how to operate moment to moment (one repeating loop).
- **R / P / D / T are the *nouns*** — where the rules live (four phases of work).

OODA describes *how* you move through the phases; the phases organize *what* the rules
are. When two rules conflict, the six core invariants (in `~/.claude/CLAUDE.md`) win.

## The operating loop (OODA)
Observe → Orient → Decide → Act → (re-)Observe, cycled fast in small steps.

- **Observe** — gather and elicit; treat the opening brief as incomplete. ⟷ *R1*.
- **Orient** — the pivot: synthesize what you gathered into a restated shared
  understanding, and revise or discard prior assumptions, *before* deciding. This is the
  step most easily skipped — make it explicit. ⟷ the reflect-back half of *R1*.
- **Decide** — choose a course; treat each decision as a *hypothesis* to be tested. ⟷ *R2*, *R4*.
- **Act** — build or run; treat each act as an *experiment* that produces observations. ⟷ the *D* rules, *R4*.
- **Loop** — verifying and re-observing feed the next cycle. ⟷ *T2*, *T3*, and R1's iterative rounds.

Guiding notions: prefer small, fast cycles over big-bang steps; re-observe after every
act; a plan is a hypothesis, not a promise.

## 1. Requirements Analysis
*Understanding and de-risking what to build, before building it.*

- **R1 — Disambiguate first, in multiple rounds, scaled to novelty and size.** When
  anything new arises — a feature, artifact, plan, or direction — the first action is to
  ask questions, not to propose or build.
  - *Novelty is the gate:* if the idea or code is new to this codebase/document (nothing
    like it exists here), it must be questioned; a recurring, already-established pattern
    needs little or none.
  - *Volume is the amplifier:* the more output the work is expected to produce, the more
    thorough the questioning — deepest when the work is both new *and* large.
  - *Question in rounds, with a floor — never one-and-done:* at least **two rounds for
    anything new, three when it is also large**; each later round *drills into the previous
    round's answers*, not just new topics. Stop only when a full round surfaces nothing
    that changes your understanding (demonstrated saturation) — not a first-round hunch.
    When unsure whether to ask again or start building, ask again: stopping is what needs
    justifying.
  - *Make each round broad and deep:* cover the space (enough questions, not three token
    ones) and probe beneath the surface — hidden assumptions, edge cases, failure modes,
    and what success looks like — not just the visible choices like scope and naming.
  - *Reflect back:* treat the opening description as incomplete, and reflect your
    understanding back so wrong assumptions surface before you act.
  - *Override (asymmetric):* the requester may declare the matter clear and say "proceed,"
    and you comply — unless you yourself still lack information you genuinely need to
    proceed correctly, in which case ask the blocking question(s) first. In short: clear
    to the requester → proceed; still unclear to the agent → it may still ask.
- **R2 — Decide nothing by assumption.** Once eliciting is done and a choice must be made
  (design, naming, parameters, tooling), present grounded options with pros/cons and a
  recommendation, then get agreement before proceeding. R1 gathers; R2 chooses.
- **R3 — Ask precisely and structurally; explain in prose.** Pose questions as structured,
  self-contained options — concrete labeled choices, one decision per question, zero
  ambiguity. The failure modes to avoid: vague wording (unclear what is being decided),
  bundling several asks into one, and jargon or assumed context the reader may not have.
  Structured options are the *default* vehicle for a question — they read clearer than a
  prose paragraph, which is why the earlier "avoid menus" guidance is dropped (ambiguity,
  not menus, was the problem). This is R2's grounded options, delivered as the question
  itself. Use prose for what it is good at — *explaining the tradeoff and consequences*
  around the choices — not for the ask. R3 governs format only; it never caps how much R1
  requires you to ask, and when the two pull apart, R1 wins.
- **R4 — Gate risky work behind a feasibility experiment.** A *feasibility experiment* is a
  small, throwaway trial built only to answer one risky question before you commit. When
  success depends on an unproven assumption — a speed/quality number, an unfamiliar tool, a
  capability that may not even work — test only that question first, on realistic inputs.
  Decide the pass/fail line up front; build the real thing only if it passes. (A decision
  is a hypothesis; the experiment tests it — see the OODA loop.)

## 2. Project
*Governance, architecture, and documentation of the whole.*

- **P1 — Keep a dated decision log.** When a task or plan completes, record a dated entry
  (newest first): what changed and why. This is the "why it is the way it is" history.
- **P2 — Keep living docs in sync, in the same change.** Any feature/structural/direction
  change updates the relevant docs in the same turn — the vision/roadmap/status, the
  component map + stack, and the how-to-change guide. Docs never lag the code.
- **P3 — Capture reusable know-how, separately from history.** When you learn something
  transferable to a *future similar system* (a tool that works, a method, a trap), record
  it as a timeless, topic-grouped recipe — distinct from the dated decision log. Reusable
  lessons only, not every task.
- **P4 — Separate the data-moving layer from the logic.** Keep the code that moves
  information around (input, output, wiring) apart from the components that do the
  meaningful work. New capabilities plug in behind a stable boundary without touching the
  wiring.
- **P5 — Define stable contracts; put conversion on one side.** Fix the format/interface
  between components, and make one side own all conversion, so the other never changes when
  internals change.
- **P6 — Maintain a risk register.** Keep a living list of things that work in the current
  small setup but will bite under deployment or scale — each with *what it is, why it
  bites, current status, and what to do.*
- **P7 — Separate the exploration environment from the delivery one.** Use a rich
  environment for tuning/experiments and a lean one for production; choose tools so
  migrating out is a one-way export with nothing trapping you in the original tool.

## 3. Development
*How code is written.*

- **D1 — Write for the reader.** Optimize for readability by the intended audience's skill
  level: small functions, the simplest approach that works, and note the upgrade path
  wherever you chose the simple option.
- **D2 — Comment everything, to teach.** Comment richly — every line or block explains
  *how* it works and *why* it exists, written to inform a reader who isn't already an
  expert, not to restate the code.
- **D3 — Self-explanatory names; no cryptic abbreviations or jargon-as-name.** Names must
  read clearly to a non-expert; avoid cryptic abbreviations and insider jargon as
  identifiers; prefer descriptive names. If a short technical term is unavoidable, define
  it in a comment on that line.
- **D4 — Add features as self-contained components behind the boundary.** Follow the shape
  of existing components and plug into the stable boundary (see P4/P5); don't weave new
  work through the data-moving layer.
- **D5 — Externalize settings as configuration.** Tunable choices (targets, parameters,
  modes) live in a hand-editable settings file, changeable without touching code.

## 4. Testing
*How work is validated and experiments are preserved.*

- **T1 — Preserve every experiment as a "build log with code."** Each throwaway trial
  keeps its own folder and a short write-up: what was tried and what happened. A durable
  record, not deleted after use.
- **T2 — Define the proof-of-success up front.** For every change or experiment, state how
  you'll know it worked — a metric, threshold, or observable signal — and confirm against
  it before calling it done.
- **T3 — Validate on realistic input, then confirm live.** Measure against representative
  data; where offline data can mislead (it often *underestimates* real conditions), confirm
  under live conditions before trusting the result.

## The six-step adversarial workflow (opt-in machinery)
The invariants above say *what* discipline to keep; this machinery makes it *run* on a task, so it
doesn't depend on remembering. It is **opt-in, one task at a time** — it wakes only when a
`.workflow/marker.json` exists in the project you're working in, and only `workflow.py start` creates
it. No marker, no workflow; quick fixes and throwaway scripts stay untouched. Turn on the ambient
status-line indicator + nudge once per machine with `python sync.py enable-workflow`.

### The six steps
A task walks six steps; each settles one question and writes its answer into the project's docs, so
the next task starts from a blank slate and still knows everything that was decided:

| Step | Settles | Lands in |
|---|---|---|
| 1. Need | What is actually needed — and what it must explicitly *not* do | `docs/OVERVIEW.md` |
| 2. Design | Which approach we take, and why the alternatives lost | `docs/DECISIONS.md` |
| 3. Architecture | The internal structure: the parts and the boundaries between them | `docs/ARCHITECTURE.md` |
| 4. Implementation | The code, in small tested + commented blocks | code + tests |
| 5. Judgment | Does the built thing actually meet the Need? Go / no-go | `docs/DECISIONS.md` |
| 6. Shipping | What breaks in the real world; record the risk, harvest the lesson, commit | `RISKS` / `PLAYBOOK` / `CHANGELOG` |

### The per-step loop
For each step, drive this loop. A single deterministic script (`workflow.py`) is the sole author of
every *verifying* act — receipts, freshness, the gate — so the model never vouches for its own work:

1. **Propose.** Do the step's work; write the draft into `.workflow/draft-<step>.md`.
2. **Prepare** — `workflow.py prepare <step>`. Assembles the challenger's bundle at
   `.workflow/context.md` (the shared rulebook + your draft + the settled record + operator context)
   with a fresh one-time canary. It refuses if the draft or rulebook is missing.
3. **Challenge** — spawn the `challenger` subagent, pointed at `.workflow/context.md` and *nothing
   else*. It attacks the proposal and writes `.workflow/challenge.md`, echoing the canary as proof it
   read the real bundle (don't paste the rules or canary into its prompt — they ride inside the
   bundle by design).
4. **Record** — `workflow.py record <step>`. Verifies the canary echo, confirms the draft is
   unchanged since prepare, and writes the receipt. Skip the challenge and there is simply no
   receipt — that gap is meant to be visible.
5. **Settle with the human.** Bring the challenger's ranked points (blocking / material / minor) and
   decide together. **Fold accepted corrections into the DRAFT, not only the published entry** —
   later steps' challengers cold-read the *drafts*, so a fix that lives only in the entry is invisible
   to them. Revising the draft makes the receipt stale and re-runs the round; that round is the point.
6. **Publish** — draft the settled prose into `.workflow/publish-entry.md`, then
   `workflow.py publish <step>`; the script (not you) places it between the doc's sentinels.
7. **Advance** — `workflow.py advance`, gated on a fresh receipt. `advance --force` is a conscious,
   recorded override (it stamps the step "overridden").

Two steps differ in shape: **Implementation** has no single prose challenger — its code is red-teamed
block by block and it earns no formal receipt (advance past it with `--force`, the real proof being
the tests). **Shipping** has no auto-doc — the risk register, playbook, and commit stay hand-written.

### One challenge pass, then settle
Default to **one** challenge round per step. Re-challenge only for a genuine *blocking break* — not
for material, minor, or wording points; fold those in and move on, or note them. Reversing a decision
the human already made, or treating every challenger nit as a redesign mandate, manufactures endless
rounds. Stop when a whole round changes nothing that matters and the human accepts.

## Document naming convention

### Standard document set
Names any developer or tool recognizes on sight. `README.md` and `CLAUDE.md` live at the
repo root; the rest under `docs/`.

| Role | Standard name |
|---|---|
| Orientation & quick start | `README.md` |
| Agent instructions | `CLAUDE.md` |
| Vision, scope, roadmap, status | `docs/OVERVIEW.md` |
| Dated decision log (newest first) | `docs/DECISIONS.md` |
| Components, boundaries, stack | `docs/ARCHITECTURE.md` |
| How to change it safely | `docs/CONTRIBUTING.md` |
| Deploy/scale risk register | `docs/RISKS.md` |
| Reusable cross-project recipes | `docs/PLAYBOOK.md` |

The working methodology itself (this file) is global at `~/.claude/METHODOLOGY.md`; a
project keeps a local `docs/METHODOLOGY.md` only to pin a specific version.

### Naming rules
- Filename = the file's role, ALL-CAPS, one word.
- One responsibility per file — no file wears two hats.
- Every doc opens with a one-line purpose + its maintenance rule (who updates it, when) as
  a blockquote.
- Dated logs are newest-first; cross-link between docs instead of duplicating.

## Changelog
The machine-readable, per-release changelog now lives in **`claude/CHANGELOG.md`** — the same
file the update-notification hook parses to show what changed. See it for the full history
(0.1.0 → today); this reference no longer keeps a second, drifting copy.
