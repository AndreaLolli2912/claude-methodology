# Working Methodology (agnostic) — full reference

> The complete working agreement, independent of any language, framework, or tool.
> The **always-on core** (six invariants + the OODA loop) lives in `~/.claude/CLAUDE.md`
> and is loaded every session; **this** file is the full set, read on demand. Maintain it
> as a living document: when a rule proves wrong or missing in real use, revise it here
> and record why in the project's decision log.
>
> **Version 0.2** (2026-07-06). Deployed as: lean core → `~/.claude/CLAUDE.md`; this
> reference → `~/.claude/METHODOLOGY.md`; doc scaffolding → the `init-project-docs` skill.
> Enforcement hooks for P1/P2 are planned for v0.3 after further real-project use.

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
- **v0.2 (2026-07-06)** — First experience-driven revision, after real use showed the Q&A
  process under-asking. Strengthened **R1**: questioning is now multi-round with a floor
  (≥2 rounds for new work, ≥3 when also large), each round drilling into the last, made
  broad *and* deep (assumptions / edge cases / failure modes / success criteria), stopping
  only at demonstrated saturation, and defaulting to *ask more* when unsure. Rewrote **R3**:
  questions are posed as precise, structured, self-contained options — the "avoid menus"
  guidance is dropped (ambiguity, not menus, was the problem) — with prose reserved for
  explaining tradeoffs; R3 never caps how much R1 asks. The `init-project-docs` skill was
  updated to match. Enforcement hooks deferred to v0.3.
- **v0.1 (2026-07-02)** — Initial extraction from the voice-assistant-concierge project's
  conventions; generalized to be technology-agnostic; added R1 (disambiguate first) and the
  OODA operating loop; strengthened D2 to "comment everything (how + why)." Deployed as a
  lean core + this reference + the `init-project-docs` skill. Enforcement hooks deferred.
