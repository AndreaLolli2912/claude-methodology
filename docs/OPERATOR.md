# Operator context

> How the developer actually works on this repo — the tacit facts that aren't visible in the
> code or git history, but that change what the *right* answer is. The builder and challenger
> are handed this file each task so they don't have to rediscover it (or, worse, miss it).
> Living document: add a plain, concrete line whenever a working habit turns out to matter.

## Why this file exists
In the first by-hand run of the six-step workflow (M1, 2026-07-13), the catch that reshaped the
whole task — *"you never edit the live files, so `install` can't overwrite them"* — was a fact
about how the developer works, and it was written down **nowhere**. The AI challenger starts
isolated, with no memory of past conversations (that isolation is what gives it fresh eyes), so
it couldn't see the fact; the human had to supply it by hand, which cost several extra rounds.
Writing these facts down lets the AI challenger carry that weight next time instead of the human.

The general rule this taught us: **the AI challenger is only as sharp as the written context it
is handed.** A challenger subagent inherits none of the main chat's memory, so anything tacit has
to be on paper and passed in explicitly.

## Scope
**Repo-specific** operator facts live here. Global habits — plain-language, one-topic-at-a-time
communication; the Windows `git push` schannel fix — live in `~/.claude` memory. A challenger
subagent doesn't inherit that memory either, so if a task turns on a global habit, hand that over
too.

## Working habits
- **I edit in the repo, then run `python sync.py install`. I never hand-edit the live `~/.claude`
  files directly.** Consequence: `install` overwriting un-captured live edits is not a real
  failure mode for me — which is exactly why `sync.py status` became a read-only readout rather
  than an overwrite-guard (see `RISKS.md` #3 and the 2026-07-13 decision in `DECISIONS.md`).
