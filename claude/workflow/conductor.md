# The conductor — how the model drives a workflow step

> These lines go into the working project's `CLAUDE.md`. They are the *conductor*: they tell the
> model the per-step loop and when to bring in the challenger. Everything the conductor asks for is
> model-mediated (it can be skipped) — which is exactly why the script writes the receipts and gates
> the advance, and why a skipped challenge simply leaves a visible gap instead of a false green.
>
> M3 wires only the **Need** step end to end; the loop below is the shape every review-style step
> reuses (the challenge machinery is step-agnostic; only the draft file and the publish target differ).

This project runs under the six-step adversarial workflow. The live task's step is held in
`.workflow/marker.json` — never edit that file yourself; only `python workflow.py` writes it. A task
begins when the human runs `python workflow.py start "<title>"`. Check where you are any time with
`python workflow.py status`.

## For the current step, drive this loop
1. **Propose.** Do the step's work and write the draft into its artifact file — for Need that is
   `docs/draft-need.md` (the file the challenger attacks and the gate hashes). For an existing
   project, survey what's already there first, then draft on top of it.
2. **Prepare the challenge:** `python workflow.py prepare <step>`. This assembles the challenger's
   bundle at `.workflow/context.md` — the shared rulebook as a header, then an ordered COLD section
   (your draft + the settled record) with a fresh canary, then a WARM section (operator context). It
   refuses if the draft or the rulebook is missing, so a green here means the bundle is real.
3. **Spawn the `challenger` subagent** and point it at `.workflow/context.md`. It attacks cold-then-warm
   and writes `.workflow/challenge.md`, echoing the canary as proof it read the bundle.
4. **Record it:** `python workflow.py record <step>`. This verifies the canary echo, confirms the draft
   hasn't changed since `prepare`, hashes it, and writes the receipt. If it fails, the challenge did not
   really happen (or ran on stale bytes) — fix the cause and retry. There is no partial green.
5. **Settle with the human.** Bring the challenger's ranked points (blocking / material / minor). Decide
   together. If you revise the draft, its receipt goes **stale** and the gate blocks advance until you
   re-`prepare`, re-challenge, and re-`record` — that is the multi-round loop working, not a bug. Repeat
   until a whole round turns up nothing new that matters and the human accepts.
6. **Auto-doc the settled step.** Draft the settled prose into `.workflow/overview-entry.md`, then run
   `python workflow.py publish <step>`. The script (not you) places your prose into the real doc between
   its sentinels — first write prepends it newest-first under the doc's anchor; a re-settle replaces it
   in place. You own the wording; the script owns the placement, and it refuses rather than corrupt a
   malformed doc.
7. **Advance:** `python workflow.py advance`. It is gated on a fresh receipt. Use `advance --force` only
   as a conscious, recorded override (it stamps the step "overridden" so the bypass is on the record).

## Rules of the road
- **Never write `.workflow/marker.json`, receipts, or the doc sentinels by hand** — only `workflow.py`
  does. If you skip the challenger, there is simply no receipt, and that gap is meant to be visible.
- **The challenger's rules ride inside the bundle** (the script puts them there); you don't need to
  brief it on them — just point it at `.workflow/context.md`.
- **Warn, never block.** Nothing here hard-stops you; the gate refuses by default but yields to a
  recorded `--force`. The human keeps the wheel.
