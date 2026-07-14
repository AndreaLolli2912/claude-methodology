# Playbook — reusable build recipes

> Timeless, transferable recipes: how to build a similar thing again (distinct from the
> dated DECISIONS log). Grouped by topic. Reusable lessons only.

## Deploy dotfiles/config with a non-destructive, cross-platform sync script
**When you need this:** you keep config in a repo but it must live somewhere fixed on the
machine (`~/.claude`, `~/.config`, …), you want one command to deploy it on any box, and it
should work on Windows *and* macOS/Linux without installs.
**The path:**
1) Mirror the target layout inside the repo (here: `claude/` mirrors `~/.claude/`).
2) Write ONE script with `install`/`capture` subcommands, standard-library only. Python 3 is
   the portable, no-install choice — bash isn't native on Windows, PowerShell 7 isn't on Linux.
3) Keep a single manifest list in that script; resolve the repo side from
   `Path(__file__).parent` and the live side from `Path.home()`, so it's location- and
   OS-independent.
4) Before overwriting any existing target file, copy it to `*.<timestamp>.bak`.
5) `capture` is the reverse direction, so live edits round-trip back to the repo.
**Gotchas:** one script kills the two-script manifest-drift trap. One-directional overwrite is
not a merge — decide which side is authoritative and say so loudly. Force `*.py eol=lf` via
`.gitattributes` so a Windows-edited shebang still runs on Linux.
**How you know it worked:** on a fresh machine, one command deploys everything and the tool
picks it up (here: `/skills` lists the bundled skill; core rules take effect after restart).
Prove it first against a throwaway `HOME`/`USERPROFILE` (assert files land + a re-run backs up).
**Pointers:** `sync.py`, `README.md`, `.gitattributes` (2026-07).

## Scaffold project docs from a methodology skill
**When you need this:** every new repo should start with the same documentation spine.
**The path:**
1) One short disambiguation round first (what/stage/components/constraints) — fill docs with
   real content, not TODOs.
2) Detect existing files; never clobber — create only what's missing.
3) Seed `DECISIONS.md` with a dated "docs scaffolded" entry (methodology P1).
4) Report created vs. skipped.
**Gotchas:** don't overwrite an existing `README.md` or project `CLAUDE.md`; offer to append
instead. Keep the content/transport and code/docs boundaries visible in ARCHITECTURE.
**How you know it worked:** `docs/` holds the full set, each with a purpose header, and the
decision log's newest entry records the scaffold.
**Pointers:** `claude/skills/init-project-docs/SKILL.md`, `docs/` (2026-07).

## Report sync/drift state without lying about "which side is newer"
**When you need this:** you're building a "where do I stand?" / "is it in sync?" check between two
copies of files (a repo vs a deployed copy, local vs remote, two mirrors), and you're tempted to use
file modification time to decide which side is newer or which way to sync.
**The trap:** a file's mtime does **not** mean "when someone last edited this." Git rewrites
working-tree file times to the moment of the operation on every clone, checkout, and pull; and a plain
byte-copy (`shutil.copy2`, `cp -p`) *preserves* the source's mtime. So after an ordinary pull, an
untouched repo file can look *newer* than a genuinely-edited copy on the other side — and a naive
"newer side wins → overwrite the older" rule then destroys real work. (Proven here with a throwaway
probe: a fresh clone stamps files at clone time, and a pull that updates a file stamps it at pull time.)
**The path:**
1) Compare **content**, not timestamps — a byte compare (or hash) reliably tells you *that* two copies
   differ.
2) For *direction* ("which way should I sync?"), use a source that actually records intent: git itself
   (`git status` for uncommitted work; `git rev-list --left-right --count @{upstream}...HEAD` for
   ahead/behind). If no reliable signal exists, **report the difference and let the human decide** —
   never guess.
3) Keep the check **read-only** and make it **degrade honestly** — offline / no remote / not-a-git-copy
   must say so, never silently report "in sync."
**How you know it worked:** the check flags exactly the files that differ, only points a direction when
it truly knows, and writes nothing (assert that in a throwaway run).
**Pointers:** `sync.py` (`status` + `_git_status`/`_live_status`), `DECISIONS.md` 2026-07-13 (the
mtime experiment) (2026-07).

## Run an adversarial AI-reviewer pass without fooling yourself
**When you need this:** you're using a separate AI subagent to attack a proposal, design, or code (a
"challenger"), and you want its verdict to actually mean something.
**The path:**
1) **Ask for the FULL ranked list, not the single worst thing.** A "give me your top finding" prompt
   hides coverage — in M2 a context-fed reviewer reported one flaw and stayed quiet on others it had
   silently dismissed. Ask for everything, each tagged blocking / material / minor; let only
   blocking+material drive another round, so "list everything" doesn't become an incentive to pad.
2) **Read cold first, then with context.** Context sharpens *and* anchors: handed the domain facts, a
   reviewer catches domain-specific flaws but can call a self-contradictory proposal "coherent". Do a
   cold pass (artifact + docs only) before the context-fed pass — same agent, in that order.
3) **Let it attack settled decisions, and defend them from the written record.** A decision nobody
   re-questioned isn't proven. If you can't defend it from the docs, the docs were incomplete (write the
   missing reason down); if you can, it's re-proven cheaply. The *human* rules on reopen, and caps it
   (one round, one hop) so it can't cascade forever — and the attacker, biased toward reopening, never
   referees whether its own attack landed.
4) **Turn the attacker on its own conclusions.** A quick, cheap pass attacking the reviewer's *proposed
   fixes* found better/cheaper alternatives and a convergence trap in M2.
**How you know it worked:** the review changes a real decision on evidence (not vibes), and a later
fresh reader can see *why* from the docs alone.
**Pointers:** `docs/WORKFLOW.md` challenger rules 3/5/6, `docs/DECISIONS.md` 2026-07-14 (M2) (2026-07).

## Verify a hook/integration's contract against the real system, not just your unit test
**When you need this:** you wrote a script a host system invokes on a fixed input/output contract (a
Claude Code hook, a webhook, a plugin callback), and your tests feed it an *assumed* payload shape.
**The trap:** the test passes because it uses the shape *you guessed*, but the host sends/accepts a
different one — so the thing is silently inert in production while every test is green. In M2 the nudge
hook went through **two** wrong output formats — bare text, then a bare `{"additionalContext": ...}`
object — and the unit tests passed on *both*, because they asserted the shape we assumed. Claude Code
actually requires the wrapped `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
"additionalContext": ...}}`; the bare form is parsed as an empty protocol object and dropped. Only a
live run exposed it. Lesson: a green unit test on an *assumed* contract is worth little — it will
happily pass through several wrong fixes in a row.
**The path:**
1) Look up the host's actual payload/return contract in its docs *before* trusting the tests, and make
   the test assert the real output *format*, not just presence.
2) A live smoke-test is **non-negotiable**, not a nicety — it is the only thing that proves the host
   invokes and honors your script. Treat it as an explicit gate, not a "later".
3) Separate three questions and test each: is the hook **registered** (the host's `/hooks`-style
   inspector), does it **execute** (drop a temporary fire-probe — one append-to-logfile line at the top
   of the script, so an empty log = never ran), and is its **output honored** (observe the behavior it
   should cause)? Registered and executed are not honored.
4) **Isolate the hook from confounds.** If another mechanism (a rules file, a default prompt) could
   produce the same behavior, a pass proves nothing. Remove the confound: move the rules file aside so
   only the hook can act; or run a **self-evidencing** test where the *difference* between two cases
   isolates it (e.g. with writes auto-allowed, a doc write stays silent while a code write prompts —
   only the hook explains the gap).
**How you know it worked:** the test would fail if the output format were wrong, and a live run shows
the host actually invoking and honoring it — with the hook isolated so nothing else could have caused
the effect.
**Pointers:** `docs/DECISIONS.md` 2026-07-14 (M2 live smoke-test + nudge-hook bug) (2026-07).
