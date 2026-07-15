# The conductor — how the model drives a workflow step

> These lines go into the working project's `CLAUDE.md`. They are the *conductor*: they tell the
> model the per-step loop and when to bring in the challenger. Everything the conductor asks for is
> model-mediated (it can be skipped) — which is exactly why the script writes the receipts and gates
> the advance, and why a skipped challenge simply leaves a visible gap instead of a false green.
>
> M4 wires all five review-style steps (Need / Design / Architecture / Judgment / Shipping) end to end;
> the loop below is the shape they share (the challenge machinery is step-agnostic; only the draft file
> and the publish target/shape differ). **Implementation** is the exception — its attacker team is a
> different mechanism, not yet wired — so it has no `prepare`/`publish` recipe.

This project runs under the six-step adversarial workflow. The live task's step is held in
`.workflow/marker.json` — never edit that file yourself; only `python workflow.py` writes it. A task
begins when the human runs `python workflow.py start "<title>"`. Check where you are any time with
`python workflow.py status`.

## For the current step, drive this loop
1. **Propose.** Do the step's work and write the draft into its artifact file, `docs/draft-<step>.md`
   (e.g. `docs/draft-need.md` — the file the challenger attacks and the gate hashes). For an existing
   project, survey what's already there first, then draft on top of it.
2. **Prepare the challenge:** `python workflow.py prepare <step>`. This assembles the challenger's
   bundle at `.workflow/context.md` — the shared rulebook as a header, then an ordered COLD section
   (your draft + the settled record) with a fresh canary, then a WARM section (operator context). It
   refuses if the draft or the rulebook is missing, so a green here means the bundle is real.
3. **Spawn the `challenger` subagent** and point it at `.workflow/context.md`. It attacks cold-then-warm
   and writes `.workflow/challenge.md`, echoing the canary as proof it read the bundle. Point it at the
   bundle and **nothing else** — don't paste the canary or restate the rules in its prompt. The rules and
   the two-pass order ride *inside* the bundle by design; re-stating them bypasses the mechanism, and a
   handed-over canary proves nothing. `prepare` has already cleared the previous round's `challenge.md`,
   so the challenger starts from a clean directory rather than reading the last round's verdict as context.
4. **Record it:** `python workflow.py record <step>`. This verifies the canary echo, confirms the draft
   hasn't changed since `prepare`, hashes it, and writes the receipt. If it fails, the challenge did not
   really happen (or ran on stale bytes) — fix the cause and retry. There is no partial green.
5. **Settle with the human.** Bring the challenger's ranked points (blocking / material / minor). Decide
   together. If you revise the draft, its receipt goes **stale** and the gate blocks advance until you
   re-`prepare`, re-challenge, and re-`record` — that is the multi-round loop working, not a bug. Repeat
   until a whole round turns up nothing new that matters and the human accepts.
   **Fold accepted corrections into the DRAFT, not only into the entry** (RISKS #15). Later steps'
   challengers cold-read the *drafts* — a correction that lives only in the published entry is invisible
   to every one of them, and they will challenge a record you already know is wrong. Correcting the draft
   costs a re-`prepare`/re-challenge round (the receipt goes stale, as above): that round is the point,
   not an obstacle. Putting the fix only in the entry is the cheap path, and it is the wrong one.
6. **Auto-doc the settled step.** Draft the settled prose into `.workflow/publish-entry.md`, then run
   `python workflow.py publish <step>`. The script (not you) places your prose into the real doc between
   its sentinels, and refuses rather than corrupt a malformed one. You own the wording; the script owns
   the placement. Draft a **fresh** entry for *each* publish — `record` and a successful `publish` both
   consume the entry file, so the machinery refuses (no drafted entry) rather than re-publish a stale one.
   Two shapes:
   - **Log steps (Need / Design / Judgment)** accumulate a dated entry — newest-first under the doc's
     anchor, or replace *this task's own* block in place on a re-settle. Just `publish <step>`.
   - **Architecture** writes one section per component: `publish architecture --section <slug> --new`
     for a component's first section, or `--update` to re-settle an existing one. The script refuses a
     `--new` whose section already exists (or an `--update` whose section doesn't), so a mistargeted
     slug fails loud instead of overwriting the wrong section.
   - **Shipping has no auto-doc** — `RISKS` / `PLAYBOOK` / `CHANGELOG` / the commit stay hand-written.
7. **Advance:** `python workflow.py advance`. It is gated on a fresh receipt. Use `advance --force` only
   as a conscious, recorded override (it stamps the step "overridden" so the bypass is on the record).

## Rules of the road
- **Never write `.workflow/marker.json`, receipts, or the doc sentinels by hand** — only `workflow.py`
  does. If you skip the challenger, there is simply no receipt, and that gap is meant to be visible.
- **The challenger's rules ride inside the bundle** (the script puts them there); you don't need to
  brief it on them — just point it at `.workflow/context.md`.
- **Warn, never block.** Nothing here hard-stops you; the gate refuses by default but yields to a
  recorded `--force`. The human keeps the wheel.
