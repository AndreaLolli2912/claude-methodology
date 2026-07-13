# Working methodology — always-on core (v0.3.4)

> Personal, loaded in every project. These are the invariants I don't skip.
> The full rule set (Requirements / Project / Development / Testing + the OODA
> mapping + the doc-naming convention) lives in `~/.claude/METHODOLOGY.md` — read it
> when a situation goes beyond this core. A project's own `CLAUDE.md` may override.
> This is a living hypothesis (v0.3.4): when a rule misfires, revise it and log why.

## Operate as a loop (OODA)
**Observe** (gather / elicit) → **Orient** (synthesize; restate the shared model;
discard wrong assumptions) → **Decide** (choose; a decision is a hypothesis) →
**Act** (build / test; an act is an experiment) → re-**Observe**.
Prefer small, fast cycles; re-observe after every act.

## Six invariants (when → then)
1. **Disambiguate first — R1.** When something *new to the codebase/docs* arises (a
   feature, artifact, plan, or direction), then before proposing or building, question it
   across **multiple rounds — never one-and-done**. Floor: **≥2 rounds for anything new
   (≥3 when it's also large)**, each later round *drilling into the prior round's answers*,
   not just new topics. Keep rounds **broad** (cover the space — not 3–4 token questions)
   and **deep** (probe hidden assumptions, edge cases, failure modes, success criteria).
   Stop only when a **whole round changes nothing** — demonstrated saturation, not a
   first-round hunch — then reflect your understanding back before acting. **Unsure whether
   to ask more or start? Ask more.** Scale up with novelty and size; a truly established
   pattern can skip. Override: requester says "proceed" → comply, but still ask any
   genuinely blocking question.
2. **Decide nothing by assumption — R2.** When a choice arises (design, naming,
   parameters, tools), then present grounded options with pros/cons + a recommendation
   and get agreement; never pick silently.
3. **Comment to teach — D2.** When writing code, then comment richly — every line or
   block states *how* it works and *why* it exists, for a non-expert reader; never just
   restate the code.
4. **Log every decision — P1.** When a task or plan completes, then append a dated entry
   (newest first) to the project decision log — what changed and why — in the same turn.
5. **Keep docs in sync — P2.** When a change touches a feature, structure, or direction,
   then update the affected docs in the same turn; docs never lag code.
6. **Prove it — T2.** When starting any change or experiment, then state up front how
   you'll know it worked (a metric, threshold, or observable signal), and confirm against
   it before calling it done.

## Always
- **Ask precisely, explain in prose — R3.** Pose questions as **structured, self-contained
  options** (concrete labeled choices), one decision per question, zero ambiguity — never
  vague wording, several asks bundled into one, or unexplained jargon / assumed context.
  Structured options are the **default** vehicle for a question (they read clearer than
  prose); reserve prose for *explaining the tradeoff* around the choices, not for the ask.
  R3 governs format only — it never caps how much R1 asks; when they pull apart, R1 wins.
- **New project?** Scaffold the standard docs with the **`init-project-docs`** skill.
  Canonical names: `README.md`, `CLAUDE.md` (root); `docs/OVERVIEW.md`,
  `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, `docs/RISKS.md`,
  `docs/PLAYBOOK.md`.
