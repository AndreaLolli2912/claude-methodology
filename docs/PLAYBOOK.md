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
3) **Define the bundle as a named whitelist WALKED from disk, not a per-file list:** a few named
   directories shipped wholesale + a short list of named root files, plus a small `IGNORE` glob list
   for junk. A file added inside a named directory then ships with **no code edit** — a per-file list
   can't express "everything in this directory", and each addition to it is a chance to forget one (a
   silent no-deploy). Resolve the repo side from `Path(__file__).parent` and the live side from
   `Path.home()`, so it's location- and OS-independent.
4) **Fail loud on the two ways the whitelist and disk disagree — asymmetrically.** An *un-named*
   top-level entry (over-inclusion: "what ships" is ambiguous) **halts** and deploys nothing until you
   classify it; a *named* entry missing from disk (under-inclusion: unambiguous) is **reported** and
   exits non-zero but still ships the rest. "Ignore beats ship": the `IGNORE` list drops junk even
   inside a shipped directory. Keep the "is this owned?" test in ONE predicate that both the walker and
   the gate consult, or they silently diverge.
5) Before overwriting any existing target file, copy it to `*.<timestamp>.bak`.
6) `capture` is the reverse direction — but pull back **only the repo's own ship set**, and report a
   live-only file as an *orphan* (exit 0) rather than pulling it, so a repo-side deletion can't
   resurrect itself into the source of truth. Additive only; never delete on the target side.
7) Make every verb **return an exit code** the shell sees (0 clean / non-zero on any anomaly), so the
   everyday command is loud — a warning buried inside an exit-0 `Done.` is the silent-green this design
   exists to kill.
**Gotchas:** one script kills the two-script manifest-drift trap. One-directional overwrite is
not a merge — decide which side is authoritative and say so loudly. Force `*.py eol=lf` via
`.gitattributes` so a Windows-edited shebang still runs on Linux. A directory walk ships *whatever* is
inside a named dir — including a gitignored or scratch file (it doesn't consult git); fine for personal
use on your own machine, but revisit before sharing the bundle (RISKS #25/#26). The walk of the *live*
side must skip the shared-namespace root (`~/.claude` also holds `settings.json`, `projects/`, other
tools) — walk only the named dirs there, or a huge unowned tree gets scanned. And guard the walker
against a not-yet-created target dir (`iterdir()` throws) so the read verbs don't crash on a fresh box.
**How you know it worked:** on a fresh machine, one command deploys everything and the tool picks it up
(here: `/skills` lists the bundled skill; core rules take effect after restart). Prove it first against
throwaway `HOME`/`USERPROFILE` + repo dirs — assert a file dropped in a named dir lands with no code
change, a stray halts and copies nothing, a missing named entry reports + exits non-zero, and junk never
ships either way. Guard the migration with a one-shot "the walk == the old file list" check, then relax
it to a *subset* (the old files still ship) so it doesn't false-fail the day you add a file.
**Pointers:** `sync.py` (`_bundle_files`, `_owns_root_entry`, `_definition_problems`, `_live_orphans`),
`docs/ARCHITECTURE.md` ("M6 — the directory-whitelist transport"), `OVERVIEW.md`/`DECISIONS.md`
2026-07-17 (M6), `.gitattributes` (2026-07).

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
5) **Fire every candidate channel in ONE invocation, each tagged with a unique marker.** When several
   fields might carry your message (a reason, a warning, a context injection), do not probe them one at a
   time — emit them all together, each carrying an unmistakable tag (`[CH-REASON]`, `[CH-SYSMSG]`, …), and
   ask *which tags appeared, and when*. One real run then maps every channel at once, and the tags make the
   answer unambiguous where "did you see a warning?" would not. M5 mapped six channel/event pairs in four
   runs this way, and the map — not the code — turned out to be the milestone's real product.
6) **Do not trust "universal" in the docs, and never generalise a field across events.** Claude Code lists
   `systemMessage` as a common output field. It is universal in *processing* — it fires and is recorded on
   every event — and **not** in *rendering*: it draws on `UserPromptSubmit` and draws nothing on
   `PreToolUse`. A probe emitting *only* that field settled it in one run. The same page shows the pattern
   is real (`sessionTitle` is "ignored on `clear` and `compact`"), so per-event behaviour is the default
   assumption, not the exception.
7) **Read the whole table, not the row you came for** — and re-read your own test output. M5 quoted
   `systemMessage` out of the universal-fields table three times while missing `continue: false` **two rows
   above it**, which outranks every field it did name. Separately, a git test's output showed an unwanted
   file being staged; the write-up reported the three results that supported the conclusion and read past
   the fourth. Running the experiment is half the discipline; reading all of it is the other half.
**How you know it worked:** the test would fail if the output format were wrong, and a live run shows
the host actually invoking and honoring it — with the hook isolated so nothing else could have caused
the effect.
**Pointers:** `docs/DECISIONS.md` 2026-07-14 (M2 live smoke-test + nudge-hook bug); `docs/DECISIONS.md`
2026-07-15 (M5 Design — the channel map, and the blacklist→whitelist inversion after three missed block
routes) (2026-07).

## Edit part of a text file without a surprise whole-file diff (and don't get version-pinned)
**When you need this:** a tool edits *part* of a committed text file (insert a block, replace a region) and
must leave the rest byte-for-byte unchanged — no phantom diff — on Windows *and* macOS/Linux, across Python
versions.
**The trap:** `Path.read_text()`/`write_text()` do universal-newline translation. Read text on Windows and
every `\r\n` becomes `\n` in memory; write it back and every `\n` becomes the platform separator (`\r\n`) —
for the WHOLE file, not just your edit. A one-line change then silently rewrites every line ending, burying
the real diff and defeating "the human reviews the diff before committing." And the obvious fix,
`read_text(newline="")`, only exists in Python **3.13+** (`write_text(newline=)` is 3.10+) — so it *crashes*
on 3.12. A green test on the author's box can hide both bugs at once, if the test seeds its fixture through
the same translating call it's testing.
**The path:**
1) Do the file I/O in **raw bytes**: `raw = path.read_bytes().decode("utf-8")`; write with
   `path.write_bytes(text.encode("utf-8"))`. No `newline=` kwarg anywhere → no version pin.
2) Detect the doc's newline once (`"\r\n" if "\r\n" in raw else "\n"`), do all matching/splicing in **LF
   space**, then re-apply that newline before writing — untouched regions keep their exact bytes and the
   inserted block matches the doc's style.
3) **Run the tests on the actual target interpreter**, and seed fixtures from raw bytes
   (`write_bytes(b"...\n...")`), not through the translating call under test — else the fixture is already
   "wrong" and the bug is invisible. Assert *both* directions: an LF doc stays LF, a CRLF doc stays CRLF.
**Gotchas:** hash raw bytes too (a text-mode hash disagrees with a byte-mode one across platforms). Match
structural markers as **whole lines at column 0** (exactly what you write), never as substrings, so prose
that merely mentions the marker syntax can't be miscounted into an overwrite.
**How you know it worked:** a partial edit changes only its own region's bytes; a pure-LF file stays pure-LF
and a pure-CRLF file stays pure-CRLF — proven on the real interpreter, both directions.
**Pointers:** `claude/workflow/workflow.py` (`_atomic_write_text`, `cmd_publish`),
`tests/workflow/test_publish.py` (LF+CRLF checks) (2026-07).

## Seed an existing hand-written doc as a machine-writable target
**When you need this:** a tool will start writing settled content into a doc humans have maintained by
hand (a status log, a decision log, an architecture section), and it must place content deterministically
— without a fragile heading match, without duplicating what's already there, and without ever corrupting
the human prose around it.
**The path:**
1) **Anchor on a SEEDED comment, not a heading.** Drop one HTML-comment sentinel where new content should
   land — `<!-- WF:anchor:<slug> -->` — under the relevant heading. Comments are invisible when rendered,
   never collide, and don't drift the way heading *text* does (a doc may have no stable heading at all).
2) **Match whole lines at column 0** (exactly what the tool writes), and carry identity on BOTH ends of a
   managed block (`<!-- WF:<key>:<scope>:start -->` … `:end`), so one block can never be mistaken for
   another's and a second writer *accumulates* instead of clobbering.
3) **Adopt existing content by wrapping it ONCE.** For a doc whose current body should become
   machine-managed (so a later "create if absent" won't duplicate it), wrap that body by hand in a
   start/end block with a stable slug — the tool then recognizes it and *replaces in place* on the next
   write instead of appending a copy.
4) **Fail closed on anything ambiguous:** exactly one anchor or refuse; a marker inside a code fence
   (```` ``` ````, `~~~`, or indented) → refuse (you can't safely place around a quoted example); a
   malformed/duplicate block → refuse. Never guess into a committed doc.
5) **Seed once, by hand, and VERIFY read-only before trusting it:** run the placement function in memory
   against the real doc's bytes and assert it lands correctly AND leaves every existing byte untouched —
   keep the placement logic a pure function so this proof writes nothing.
**Gotchas:** don't reuse heading text as the anchor (it collides and drifts); if the doc doubles as a
milestone record, *mark* superseded sections rather than deleting them; pin `*.md eol=lf` in
`.gitattributes` so a publish never flips the whole file's newlines.
**How you know it worked:** a simulated write inserts/replaces exactly one block under the anchor and a
byte-for-byte comparison shows every other byte unchanged; a doc missing the anchor, or carrying a fenced
marker, is refused rather than mis-edited.
**Pointers:** `claude/workflow/workflow.py` (`_place_block`, `_wf_marker_in_fence`, `cmd_publish`),
`docs/ARCHITECTURE.md` ("M4 — the publish engine"), `DECISIONS.md` 2026-07-14 (M4) (2026-07).

## Prove a model-dependent system with a live smoke-test (not just a green suite)
**When you need this:** your system's value depends on a *model* really doing something — spawning a
reviewer, reading a bundle, following an instruction — and your test suite fakes that part with a script.
A green suite then means "the code paths I thought of work", which is not the same claim. Twice now (M2,
M4) a passing suite hid a real defect that one live run surfaced immediately.
**Why it works:** a scripted actor does only what it is told, so it exercises the paths you already
imagined. A live one reads its whole environment — files you forgot were there, instructions you assumed
were clear — so it finds the paths you did not. That difference is structural, not a matter of test
quality: at M4 the suite had 121 green checks and still could not have reached either finding.
**The path:**
1) **State the bar before you run** — what must be true for this to count (T2). Write it down first; a
   live run produces a lot of interesting noise, and a bar set afterwards bends to fit it.
2) **Isolate, but keep it real.** Run in a throwaway sandbox that holds *copies* of the real artifacts,
   so placement/parsing hits real anchors and real size while the real files stay untouchable.
3) **Hand the actor the entry point and NOTHING else.** No pasted secrets, no restated instructions. If
   the design's claim is "the rules ride inside the bundle", then restating them in the prompt tests your
   prompt, not the design. A handed-over secret proves nothing about whether it was read.
4) **Use a fresh actor per round** if independence is part of the design, and check what the previous
   round left on disk — that is exactly where M4's contamination bug lived.
5) **Watch what it does that you did not ask for.** The findings come from the actor's *incidental*
   behaviour: what it read on the way, what it inferred, what it reported back as fact.
6) **Verify every fix with a CONTROL.** Run the *pre-fix* code over the same sequence and watch the bug
   reproduce. Without that, a green check may just mean the setup no longer triggers the bug.
**Gotchas:** the false green is the trap — M4's first fix-check passed because an unrelated `reset` had
already removed the file under test, so nothing was proven. Budget for it: a live run is slow (minutes per
actor) and cannot be replayed, so its evidence is inherently a witnessed event, not a re-runnable artifact
— which is why the *findings* must be converted into permanent tests and recorded risks the same turn.
**How you know it worked:** every bar item is met by an observation, not an inference; each new finding is
either fixed-and-locked by a test that fails on the pre-fix code, or recorded as a named residual with its
severity and owner. A live run that finds nothing is a result too — but only if it was free to.
**Pointers:** `DECISIONS.md` 2026-07-15 (M4 Step 5) and 2026-07-13 (M2's live half); `RISKS.md` #15;
`tests/workflow/test_workflow.py` (checks S/S2/S3 — the fix L2 earned) (2026-07).

## Tell "green" from "done": judge a build against the Need's proof bar
**When you need this:** you've built and unit-tested something (suite green, code reviewed) and you're tempted
to call it done — but the original Need's acceptance list includes *observed* behavior, not just "the tests
pass."
**The path:**
1) At the judgment step, re-read the Need's own "how we'll know it worked" list and hold the build against
   EACH item — confirmed / live-gated / not done — scored against the Need, never against the test count.
2) Separate "proven by tests" from "proven by observation." Unit-green is a filter, not a substitute: a hook can
   pass crafted-stdin tests and still be inert or unrendered in a real session (the M2 trap). Say which items
   are live-gated in plain words — "the code is proven; these N items are the deploy step's mandate."
3) Run the deploy AS the evidence-gathering step, not a victory lap: install, then observe each live item — the
   signal fires AND is honored on screen, inertness by a real control, the one-command removal — and record the
   numbers. (For *how* to run that live actor test, see the smoke-test recipe above.)
4) Finalize the record only AFTER the live proof. A "done" written before the observation is exactly what the
   judgment step exists to catch.
**Gotchas:** whoever hands off tends to under-scope the deploy as "ship + push" — the live proof is the larger
half. Some live items are the operator's to observe (status-line chrome you can't see), so plan them as a
collaborative checklist, not a solo run.
**How you know it worked:** every proof-bar item has a named source — a test, a measurement, or a witnessed
observation — and the ones that needed a real session were seen in one.
**Pointers:** M5 Judgment→Shipping (`OVERVIEW.md` `WF:judgment:796664b9`, `DECISIONS.md` 2026-07-16); the
live-proof screenshot; the deployed-scripts probe pattern (2026-07).
