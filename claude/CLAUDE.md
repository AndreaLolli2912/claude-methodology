# Working methodology — always-on core (v0.1)

> Personal, loaded in every project. These are the invariants I don't skip.
> The full rule set (Requirements / Project / Development / Testing + the OODA
> mapping + the doc-naming convention) lives in `~/.claude/METHODOLOGY.md` — read it
> when a situation goes beyond this core. A project's own `CLAUDE.md` may override.
> This is a living hypothesis (v0.1): when a rule misfires, revise it and log why.

## Operate as a loop (OODA)
**Observe** (gather / elicit) → **Orient** (synthesize; restate the shared model;
discard wrong assumptions) → **Decide** (choose; a decision is a hypothesis) →
**Act** (build / test; an act is an experiment) → re-**Observe**.
Prefer small, fast cycles; re-observe after every act.

## Six invariants (when → then)
1. **Disambiguate first — R1.** When something *new to the codebase/docs* arises (a
   feature, artifact, plan, or direction), then before proposing or building, ask
   questions in iterative rounds until answers stop changing your understanding — and
   reflect your understanding back. Scale depth to *novelty* (new → question; recurring
   pattern → skip) and to *expected output size*. Override: if the requester says it's
   clear, proceed — unless you still lack something you genuinely need.
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
- **Communicate tradeoffs in prose** — focused conversational rounds, not overwhelming
  multiple-choice menus (R3).
- **New project?** Scaffold the standard docs with the **`init-project-docs`** skill.
  Canonical names: `README.md`, `CLAUDE.md` (root); `docs/OVERVIEW.md`,
  `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, `docs/RISKS.md`,
  `docs/PLAYBOOK.md`.
