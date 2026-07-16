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
- **I don't care about latency at this scale — don't design around it.** *(Ruled 2026-07-15.)* Told
  that a globally-installed hook costs **~140 ms per prompt and per file write in every repo**,
  including repos with no workflow task running, the answer was: *"why should I fucking care about
  losing 0.1 seconds, really? I can work in as many repositories as I like."* Consequences: (1)
  per-event overhead at the ~100 ms scale is **not** a design constraint — it sits inside a prompt
  that takes seconds to answer; (2) never trade a simpler design, or a working global status line,
  to avoid it; (3) a requirement demanding a feature cost *nothing measurable* is an invention of
  the writer's unless he said so — he did not, and one such invented absolute ("must feel exactly
  like plain Claude Code — non-negotiable") cost several challenge rounds before it was struck. He
  works in **2–3 repos a day** and wants that to stay unconstrained; right now he is in this repo
  almost exclusively, because he wants this finished.
- **I always open Claude Code at the repo root — never inside a subfolder** — so that Claude can
  see all of the project's files. The two directory paths Claude Code hands a status line or a hook
  are `cwd` ("where the session is *now*") and `workspace.project_dir` ("where the session was
  *launched*"). They diverge two ways: if you launch deeper in the tree, **or if you change
  directory mid-session**. **My habit closes only the first.** So the honest consequence is *not*
  that the two are interchangeable — it is that **`workspace.project_dir` is the stable one**, and
  machinery that must find which project it is serving should prefer it and never needs to walk up
  the tree hunting for a project root. A design that handled subfolder launches would be solving a
  problem I do not have; a design that assumed `cwd` never moves would be solving it wrong.
  *(Recorded 2026-07-15: the M5 Need challenger flagged that this file was silent on the exact
  habit that milestone turns on — the gap this file exists to close. Corrected the same day: the
  first draft of this bullet claimed the two paths are "the same value for me", which overstates
  the habit — it contradicted its own parenthetical, and the M5 Need §2 caught it.)*
- **My projects are git repos, and the repo root IS the project root — machinery may rely on that.**
  *(Ruled 2026-07-15, when asked rather than inferred.)* So when a command has to work out which
  directory it is serving and nothing hands it one, **walking up to the nearest `.git` is the right
  answer**, and it beats trusting the current directory: the workflow's commands are typed by *Claude*
  as often as by me, through a Bash tool **whose working directory persists between calls** — so one
  stray `cd` in an earlier tool call silently poisons every command after it, with no human `cd`
  involved. A command that lands somewhere unexpected must **print the root it chose**, so a wrong
  answer is visible in its first line rather than discovered later. (Non-git folders fall back to the
  current directory; I don't work in those.) *(Recorded because the M5 Design challenger caught the
  builder **deriving** this from the bullet above instead of asking me — twice wrong about that same
  bullet first. This file exists to hold facts I've actually stated: when a design needs one, ask,
  and write the answer here.)*
