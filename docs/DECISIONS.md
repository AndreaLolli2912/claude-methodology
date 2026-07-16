# Decision Log

> Why things are the way they are. Add a dated entry whenever a task finishes or a plan is
> executed (newest first). Keep each entry short: what changed and why.

<!-- WF:anchor:decisions-log -->

### 2026-07-16 — Workflow machinery M5: Steps 4–6 (Implementation, Judgment, Shipping) — the control layer is LIVE + COMPLETE

**M5 is done and deployed.** The control layer — a workflow-aware status line (`wf:<step>:<state>`) and a
`UserPromptSubmit`/`SessionStart` nudge, plus the D-2 rooting fix that makes them possible — is installed in
this machine's `~/.claude` and proven live.

**Implementation (Step 4, the exception step).** Built as four checkpoint blocks, each cleared by a full
five-hat attacker team (fidelity / bugs / verify / simplify / security): (1) the D-2 rooting refactor of
`workflow.py` + D-10; (2) the two hooks (`statusline.py` `render()` split, `statusline_wf.py`, `nudge.py`,
conductor sentinels); (3) the `sync.py` D-8 wiring; (4) the `.wf-sandbox` delete. 205 checks green (was 124).
Closed with `advance --force` (no receipt — the exception step earns none), run with the shipped code from the
sandbox as a bonus live rooting proof.

**Judgment (Step 5).** Held the build against the Need's own 11-item proof bar rather than the test count, and
that reframed the finish: the proof bar is a *live* bar, and 7 of its 11 items were gated on the install (both
signals firing AND honored in a real session, inertness by a live control, latency re-measured,
installed/used/reversible). Verdict — the code half proven, the live half is Shipping's mandate — published to
`OVERVIEW.md` (`WF:judgment:796664b9`); advanced on a human override (the independent challenger consciously
skipped, the build already cleared by 15 attacker passes).

**Shipping (Step 6, the no-publish exception).** Deployed by a deliberate, backed-up, reversible act: `sync.py
install` (6 new machinery files + the `statusline.py` refactor; everything else backed up) then `sync.py
enable-workflow all` (nudge on `SessionStart` *alongside* the preserved `check_version` + on `UserPromptSubmit`;
status line swapped to the wf renderer). The live proof then discharged all 11 items: a fire-probe of the
deployed scripts (execute, whitelist holds, inert → silent); latency re-measured (plain 55 ms baseline; wf
+7–16 ms — recorded, not gated); a real restarted session where both signals rendered on screen and the nudge
oriented a fresh context-free Claude (it even caught that the demo's draft was a hollow placeholder); breakage
sized (corrupt marker → `wf:ERR` + a "broken" notice, exit 0, the prompt proceeds); and a reversibility
round-trip on the real `settings.json` (`disable-workflow` reverts + keeps `check_version`, `enable-workflow`
restores).

**What shipped vs. what was scoped.** TWO ambient pieces, not the Need's original three — the `PreToolUse`
skip-warner was dropped at Design (D-6) on measured evidence that no channel puts a reason on screen at the
moment of a permission decision, and re-homed to M7. **New accepted risks:** RISKS #20–24 (unbounded walk-up;
non-atomic settings write; no `.gitignore` self-heal; nudge-state lost-update; the deploy not advertising its
own off-switch — the last found in the live proof). **PLAYBOOK:** "Tell 'green' from 'done'." The live proof is
what turned an under-scoped "deploy + push" handoff into the step that gathered the real evidence.

### 2026-07-16 — Workflow machinery M5: Step 3 (Architecture) settled — the control layer, structured

**Settled after six challenge rounds** (blocking 2 → 3 → 1 → 1 → 1 → **clean**), each with a fresh
independent challenger. The full architecture is published to `ARCHITECTURE.md` under
`WF:arch:control-layer`; this logs the decision and the human rulings.

**Two probes the Design owed came back first, both answered by measurement** (throwaway project, live
`~/.claude` untouched): `SessionStart` **fires and delivers** on the `compact` matcher (D-7 rests on
this), and project hooks **merge** with user hooks across every scope (D-1's one-global-install cannot
be silently disabled). `CLAUDE_CONFIG_DIR` is real-but-undocumented, which let the user boundary be
tested safely.

**What the rounds bought, concretely:** the status-line renderer would have died on a cross-directory
import (wrong bundle folder); a round-1 "tidy-up" removed a stat-before-import safety guard and round 2
caught the regression; D-8's mandated `enable_statusline` change had no home, so a new-box re-run would
silently wipe the `wf:` segment; the test suite drives the CLI as a **subprocess** that, un-aimed after
the rooting change, would `reset` the *repo's own* live marker and drafts (fixed by `cwd=TMP`); and the
nudge's broken-branch fail-loud routed through the dead module's writer, silently discarding its own
warning (fixed by making the broken branch stdlib-only and terminal).

**Human rulings (2026-07-16):** the resolved root prints to **STDERR** (test-clean, still visible — it
is the operator's own mis-root guard); and the **six corrections owed to the Need's draft are applied
now**, ahead of Implementation, so the challenge bundle reads an accurate Need (RISKS #15).

**Held the growth line** the Design broke: 272 → 442 lines across six rounds, all homing real missing
structure, none re-arguing settled decisions. **Step 4 (Implementation) next**; sandbox dogfood; live
`~/.claude` untouched; not committed.

<!-- WF:design:796664b9:start -->
### 2026-07-15 — Workflow machinery M5: Step 2 (Design) settled — the control layer, decided

**Settled after eleven challenger rounds** (blocking: 4 → 3 → 1 → 2 → 1 → 2 → 0 → 1 → 1 → 1 → **clean**).
The Need's eight open questions are answered, plus the four §5.7 items it handed Design. **M5 now ships two
ambient pieces, not three** — the skip-warner does not survive its own evidence (below), which is the Need's
own pre-authorized outcome rather than a scope cut of convenience.

**The milestone's real product is a measured map of what the platform actually does**, built in a throwaway
project with real dialogs, each hook logging its own firing so "never ran" is always distinguishable from
"ran and was ignored". Everything that reaches a human **in time** lives on `UserPromptSubmit`; everything
on `PreToolUse` is silent or too late. Specifically: `systemMessage` **renders on `UserPromptSubmit` and
not on `PreToolUse`** — it is universal in *processing*, not in *rendering*, which no documentation says;
`permissionDecisionReason` never reaches the human at all (it reaches *Claude*, as the tool-error body — so
M2's generic dialog was the platform, not M2's bug); `additionalContext` reaches Claude **before it acts**
on prompt-submit and only after the attempt on `PreToolUse`; and `permissionDecision: "ask"` **is** honored
and overrides a permission allow-list (proven by control: hook removed → the write succeeded; hook emitting
`"ask"` → it did not). `$CLAUDE_PROJECT_DIR` reaches a **status line** (undocumented) but **not the Bash
tool** (measured absent) — and the env var and stdin disagree on slash direction, same directory, same
invocation.

**The decisions.** **D-1** one global install in `~/.claude` (copy drift is what `sync.py` exists to
prevent; `statusLine` is a single value so a per-project line cannot coexist with his). **D-2** the Need's
"line 40 is `__file__`-rooted" is only half the diagnosis — **one name was doing two jobs**: `BUNDLE`
(script + rulebook, correctly `__file__`-relative) and `PROJECT` (`.workflow/` + docs, never). `PROJECT` is
**handed in where the platform hands it, found where it does not**; one normalizer, because of the slash
split. **D-2a** the CLI is handed nothing, so it walks up — for the marker on every verb, for `.git` on
`start` — and **every verb prints the root it resolved**; `Path.cwd()` is rejected because the model types
these verbs through a Bash tool **whose cwd persists between calls**, so no human `cd` is needed to poison
it. **D-3** `root` is a parameter with a default, never a mutable global. **D-4** a separate
`statusline_wf.py` the setting points at — *not* code inside `statusline.py`, because `statusline.py` is in
MANIFEST and `settings.json` is not, and that asymmetry is exactly why `enable-*` is safe; under the
alternative `disable-workflow` had no mechanism at all (`install` reverts a live edit; `capture` would
promote "turn this off" into a commit on every machine). **D-5** one nudge script on two events, quiet rule
scoped to `UserPromptSubmit`, `SessionStart(startup|resume|clear|compact)` always injecting — because a
compaction destroys the model that was told while changing nothing a message-hash is computed from.
**D-7** the conductor rides the nudge, extracted by the same sentinel mechanism `publish` already uses.
**D-8** `sync.py` ships six named files; **`enable_hook` and `enable_statusline` are opposite idioms**
(append-and-identity-match vs. bare assignment) and mirroring the wrong one onto `hooks.SessionStart` would
silently delete `check_version.py`. **D-9** §5.7's ruling: Claude's blindness to a dead hook is **accepted**
— the system is not blind, only the model is, and the honest floor never routes through hooks, so a dead
hook loses a *warning*, never a *truth signal*. **D-10** all task state lives in a self-ignoring
`.workflow/` (drafts move there from `docs/`), so `git add -A` is safe in every repo by construction rather
than by a rule in this one.

**D-6 — the skip-warner does not ship, on four measured grounds.** It cannot explain itself at the moment of
decision (across a *complete* enumeration of the three events that reach that moment — including
`PermissionRequest`, which fires *"when a permission dialog appears"* and carries no human-facing field at
all; it appears nowhere in the Need's survey, because nobody looked). A generic pause is the failure mode
§5.3 names, and the allow-list shows it is *this operator's*: 24 reflex approvals including a wildcard for
arbitrary Python. It **cannot be proven to work** — `Write` prompts here with no hook installed, so the bar
passes on a do-nothing implementation and §8.3's control prompts in both arms. And the evidence for its
fallback came from an **unthrottled** nudge firing on the requesting prompt — the regime D-5 abolishes.
What survives is the mechanism that demonstrably worked: with no hook able to block it, the nudge alone made
the model decline the write and explain why. Re-homed to **M7** with the `"ask"` finding preserved.

**The lesson worth keeping: a blacklist of forbidden routes is unmaintainable by construction.** Three times
this Design enumerated "the ways a hook can block", and three times the list was short — `"ask"`, then
`decision: "block"` (live on the exact event our hook registers), then **`continue: false`**, universal,
outranking every field the list did name, sitting two rows above `systemMessage` in the very table the
Design quotes for `systemMessage`. Each fix repaired the instance and the class walked one row over. The
contract is now a **whitelist** — the hook emits `systemMessage` and `additionalContext` and nothing else,
any other key is a bug — which is complete by construction, checkable in one assertion, and immune to
routes the platform adds later.

**What the rounds bought, concretely:** a gitignore carve-out that provably staged nothing (git will not
re-include a file whose parent *directory* is excluded — the trailing-slash form fails **silently**); an
`enable-statusline` rule that would have no-opped after its first run, defeating the command's whole
recorded purpose on a machine whose Anaconda interpreter moves; the `check_version.py` deletion above; and
`.wf-sandbox/` exposed as **live**, holding a rival marker for this very task — which `__file__`-rooting had
made inert and D-2a's walk-up would have made *findable*.

**Owed, recorded rather than discovered:** two probes before Implementation (what `SessionStart` delivers on
`compact` — D-7 rests on it; and whether project hooks merge or replace, whose dangerous direction would
silently disable the whole layer); **six corrections to the Need's own draft**, including must-not #1's
mechanism, which names a route M5 can no longer reach. **Known false in the settled draft (round 11, minor):**
D-10 justifies its carve-out partly on `reset` deleting `global-habits.md` — `cmd_reset` unlinks four named
paths and never touches it. The decision stands on its other ground; the sentence does not.

**Step 3 (Architecture) next.** Sandbox dogfood; live `~/.claude` untouched; not committed.
<!-- WF:design:796664b9:end -->

### 2026-07-15 — Workflow machinery M5: Step 1 (Need) settled — the control layer, scoped

**Scope, human-sliced.** Build the three ambient pieces **and** solve the rooting problem properly, then
**install it** — rather than prove them in a sandbox shape that hides the difficulty. The operator has stated
this workflow will run on his machine and travel to his others through GitHub, so *"built but never deployed"*
is not an acceptable end state. The Need itself is published in OVERVIEW (2026-07-15); this entry carries what
the Need deliberately does not: the platform reading, the rulings, the risk movement, and the process failure
that cost most of nine rounds.

**The rooting problem is the milestone, not a detail inside it.** `workflow.py` line 40 —
`ROOT = Path(__file__).resolve().parent` — hangs every path off the script's own folder. **Why it stayed
invisible until now:** M3 and M4 ran in a single sandbox folder where script, docs and state sat together, so
`__file__`-rooting was *accidentally* correct; the control layer is the first thing that cannot live in that
shape, because a status line and a hook are handed a project and must serve it from somewhere else. RISKS #16
recorded this at M4 as a self-hosting inconvenience — M5 finds it is the load-bearing blocker. Reproduced live
twice: by import probe (standing in the real repo root, the marker resolved to `claude/workflow/.workflow/`),
and again inside a real hook prototype that read the project path out of its payload correctly and then emitted
nothing, because the import ignored it.

**Three human rulings, recorded so nobody re-opens them by guessing.**
1. **Latency at the ~100 ms scale is not a design constraint.** Put the real numbers to the operator — a
   globally-installed hook costs **~140 ms per prompt and per file write in every repo**, including repos with
   no task open — and the ruling was *"why should I fucking care about losing 0.1 seconds? I can work in as many
   repositories as I like."* Now in `OPERATOR.md`. Inertness stays non-negotiable **as a behaviour** (no marker,
   no sound); its *cost* is accepted. This removes the pressure that made "do project hooks merge with user
   hooks?" look decisive, and points Design at the simple answer — one global install, which also keeps his
   existing status line.
2. **Precision is capped at ~10 ms.** *"If we have to argue about milliseconds let's just not be precise."* The
   measurement noise was always wider than the digits being argued over.
3. **Keep the skip-warner, and he must learn *why* before he answers.** Which channel carries the reason is
   empirical, not ruled — Design probes it. An honest fail is an allowed outcome.

**The document's own worst failure: an absolute nobody asked for.** An earlier draft demanded that inertness
*"feel exactly like plain Claude Code — non-negotiable"*, discovered that unmeetable (a hook must start a
process to learn there is no marker), and then defended it across rounds with **three separate wrong latency
budgets** — one invented below the bare-interpreter floor, one inferred by arithmetic instead of measured, one
subtracting rows with different baselines. All three existed to defend a requirement **the operator never
stated**. Inventing an absolute nobody requested is how a Need manufactures its own crisis; the ruling struck it
entirely.

**Platform contracts are quoted, not summarised — because a summary was wrong twice, both times on exactly the
load-bearing claim.** A research subagent reported that `additionalContext` is a top-level field and the
`hookSpecificOutput` wrapper was "incorrect" (the wrapper **is** required — this is precisely the silently-inert
nudge M2's smoke-test caught, so trusting it would have rebuilt the identical bug), and that project settings
*replace* user hooks (**the docs never say** whether hooks merge or replace — and that fabricated certainty had
already been used to eliminate a design option). So §2 of the Need splits every contract into **QUOTE** (the
doc's words) / **GLOSS** (the inference that gets spent downstream) / **NOT SETTLED**. Three facts each decide a
requirement:
- **Exit 2 is not the only way to block.** `permissionDecision: "deny"` blocks the tool call and is delivered as
  JSON **on exit 0**, one word from `"ask"` in the same enum. So "never hard-block" is **two** commitments, not
  one: never exit 2 **and** never emit `deny`. Stating only the first would guard the invariant against the one
  route we were never going to take while the reachable route sat unmentioned inside its own quote.
- **A non-zero exit and JSON output are mutually exclusive** (*"JSON output is only processed on exit 0"*). One
  invocation cannot both raise the human's transcript notice (needs non-zero) and tell Claude (needs JSON).
- **`systemMessage`** — *"Warning message shown to the user"* — is a universal field emitted on exit 0 **beside**
  `additionalContext`. One invocation, both audiences. It is what makes "never leave Claude thinking a broken
  hook passed" reachable at all, and it is the most promising candidate for the skip-warner's reason.

**Risk movement.** **New: #18** — the canary proves the challenge bundle was *read*, not that it was *fresh*;
found live inside this very step's harness. **#15 reproduced live, and the gate held** — folding challenge-forced
corrections into the draft (the honest path) flipped the receipt stale, `publish` refused, and rounds 8 and 9
existed *because the machinery demanded them*, not by choice. The cheap path (fix only the entry) would have been
silent. #15 stays **out of M5** and needs re-homing: it landed here by date, not subject. M5's honest effect on it
is a narrow tilt the **wrong** way — the nudge makes the honest path's owed round arrive sooner, while the cheap
path stays exactly as invisible as today.

**The process failure, recorded because the record is the only place it gets caught next time.** The Need
converged 7 → 8 → 5 → 4 → 5 → 3 → 1 → 3 → **0**. Nine rounds is the story, and the cause was the builder's, not
the challenger's: **every round added text** — rationale for the fix, the history of the finding, a paragraph of
self-criticism about the previous round — and that new text was never challenged, so it became the next round's
attack surface. The builder was manufacturing findings and reading each one as proof the process worked. Cutting
six rounds of narration dropped the draft ~15% and took findings from five to one. **A revision should usually be
shorter than what it replaced;** history belongs in this log, at settle — not in the artifact under challenge.
The challenger's own best finding names the second half: *"every fix has been applied exactly where the
challenger pointed, and never to the class the challenger named"* — a rule about glosses added, then applied to
**1 of 6** bullets while the header claimed it ran on all of them. **Fix the class, not the instance, and sweep
by search rather than by memory.**

**An open thread the operator raised, not closed here: the `/`-command ban is over-broad, and the record only
half-defends it.** *"Eventually, we could bring the `/` command back if it solves ambiguity or makes the tool
better."* He is right. The ground rule read *"Automatic, never typed `/` commands"* — but **`start` is already a
typed command**, the deliberate human-owned bootstrap the M2 Need settled on purpose. The rationale ("things must
fire on their own, because remembering is what fails") defends banning `/` for **driving the flow**; it says
nothing about the **bootstrap**, and a `/start-task` command would be strictly better than typing `python
claude/workflow/workflow.py start "…"` while violating nothing that rationale protects. The M2 record already
carried the narrow wording (*"drive the flow with typed `/` commands"*, OVERVIEW 2026-07-13), so the ground rule
was simply out of sync with what was decided. **Narrowed to what the record defends; the bootstrap question is
not answered here.** His criterion is **usefulness** (*"we might accept `/` commands if we find them useful"*) —
which is **empirical, and therefore not decidable yet**: nobody has typed the long form on real work, because
nothing is deployed. So it gets a test and a home rather than a "maybe": **decided at M5's Judgment step**, the
first point where real-use evidence exists (M5 ends installed and used). An open question with no test and no
decision point is a wish — the same standard the Need applies to its own closing conditions.

### 2026-07-15 — Workflow machinery M4: Step 6 (Shipping) settled — M4 complete
The last step. Ran **by hand** (M4's `shipping` row exists now, but M4's earlier steps left no `draft-*.md`
files for `prior_settled` to bundle, so a machinery-assembled bundle would have been *thinner* than the real
record — the honest choice was to hand the challenger the real code and docs). The bundle was still assembled
faithfully: the real `rulebook.md` as the framing header and the attack angles pulled **out of
`RECIPE["shipping"]`** rather than paraphrased.

**The challenge: no BLOCKING findings.** The challenger verified rather than accepted — it re-ran the suite
itself (124/124 on 3.12.7), read `sync.py`'s MANIFEST, and checked the diff stats against the claim. Three
MATERIAL findings, all true, all now closed:
1. **The self-hosting gap → RISKS #16.** `ROOT` is the script's folder, so the machinery cannot run its own CLI
   against this repo's `docs/` in place; every live proof ran on sandbox *copies*, and `test_seed_docs.py`
   exercises the pure `_place_block` engine, not `cmd_publish`. Recorded precisely, including *why* coverage is
   still equivalent (the copies were byte-identical, and every doc-specific behaviour is determined by those
   bytes). "Proven on the real docs" now honestly reads "proven on their exact bytes".
2. **The rollback was reasoned, not shown → demonstrated.** Stashed the entire M4 tree: the pre-M4 script still
   parses, the tree is clean, and all three docs show **0 anchors** — confirming the anchors are M4-introduced
   and a revert removes them cleanly. Restored; 124/124 still green after the round-trip.
3. **The evidence trail is ephemeral → harvested into PLAYBOOK.** The smoke-test tally lives only as prose from
   a temp sandbox — and M2/M3 have the same gap ("preserved in the session scratchpad" is not preservation).
   Human call: put the durable value where a future session will look — a PLAYBOOK recipe ("prove a
   model-dependent system with a live smoke-test"), since the load-bearing findings are already locked by checks
   S/S2/S3 and RISKS #15. The tally is colour; the tests are the evidence.
Two MINOR findings folded as **RISKS #17** (`cmd_prepare`'s bundle write and `_save_marker` raise a raw
traceback instead of a clean refusal) — accepted, because they fail **loud**, never silently green: no receipt,
no doc touched, honest floor intact. It is polish, not correctness; M5 revisits it under hooks.

**The harvested lesson (PLAYBOOK).** *The live smoke-test is what pays — budget for it every milestone.* M2's
caught the inert-nudge bug; M4's caught two more against a 121-check green suite. The reason is structural: a
scripted actor exercises the paths you already imagined; a live one reads its whole environment and finds the
ones you did not. Corollary, earned the hard way: **verify every fix with a control** — M4's first fix-check was
a false green because an unrelated `reset` had already removed the file under test.

**M4 is complete.** Six steps, five of them challenged (Implementation by its attacker team instead). Shipped:
the publish engine + four rows + **124 checks** + the synced record. **Not deployed** — `sync.py`'s MANIFEST
does not ship `workflow/*` (RISKS #8, M6), so M4 has zero live blast radius. **M5 (hooks + status line) next**,
inheriting RISKS #15 and #17.

### 2026-07-15 — Workflow machinery M4: Step 5 (Judgment) settled — live smoke-test passed, 2 real findings
Discharged the one item Judgment left owed: the M4 dogfood had proven the chain with a **scripted** challenger,
so "dogfooded end-to-end" only meant the deterministic half. Ran the **live** smoke-test — four real spawned
Sonnet challengers, one per new row — in an isolated sandbox seeded with **copies of the real docs**. Live
`~/.claude` and the real `docs/` untouched; **not committed.**

**Bar (set before the run) — all five met.** (1) The challenger is genuinely spawned, reads the bundle off disk,
and is handed *only* the file path — no canary, no restated instructions, since the design's claim (A-1) is that
the rulebook and the two-pass order ride *inside* the one file it reads. (2) The canary survives a real model:
**4/4 echoed it verbatim**, each round's token fresh, the prior round's absent. (3) **All four new rows ran
live** — design → DECISIONS (log), architecture → ARCHITECTURE (section, both `--new` and `--update`), judgment
→ OVERVIEW (log, shared anchor), shipping (record-only). (4) Every publish was **surgical**: stripping the
blocks back out reproduced all three originals **byte-for-byte**, no newline flips. (5) **Twelve real refusals**
observed. design/architecture/judgment each advanced through the gate **without `--force`**, on receipts earned
by real challengers; both no-publish exceptions refused correctly.

**Why it was worth running: two real findings 121 deterministic checks could not reach.** A scripted challenger
does only what it is told; a live one reads its whole environment.
- **L2 (fixed).** `prepare` never cleared the *previous* round's `challenge.md`. Since the challenger is told to
  **write** that path, it reads what is already there — two live challengers did, then fed the prior round's
  findings back as "cross-round corroboration": contamination reported as independent confirmation. Not a
  receipt hole (a stale result echoes the old canary and `record` rejects it) but a **context-integrity** one
  that undermines "a fresh challenger each step". It is the exact mirror of CB1's leftover-**entry** bug, one
  file over. *Fix:* `prepare` clears `CHALLENGE` fail-closed, placed **after** every validation check so a
  refused prepare has no side effect. Proven live **with a control** — the committed pre-M4 script reproduces
  the bug on the same sequence. Checks S/S2/S3 added; suite **124/124** on 3.12.7.
- **L1 (documented, not fixed — RISKS #15).** Later steps challenge a record that lacks every earlier
  correction: `prior_settled` feeds challengers the **drafts**, while challenge-forced corrections land in the
  **entry**; and folding a correction back into a draft flips its receipt stale, so `publish` refuses. The flow
  therefore *steers* corrections into the one channel no later challenger ever sees. Observed live: the Judgment
  challenger correctly reported that Architecture's correction "isn't written anywhere in the settled
  Architecture I was handed". **Not a code bug** — resolving it means deciding what `prior_settled` should feed,
  which reopens a settled Design/Architecture decision, so it is carried to **M5** rather than patched inside
  M4's Implementation step. Human call: *fix L2 now, document L1.*

**Judgment verdict: GO.** The Need's bar is met on every item and the owed live item is discharged. The
machinery's honest floor held under live conditions — including refusing *me* twelve times.

### 2026-07-15 — Workflow machinery M4 (complete the step set): Step 4 (Implementation) settled
Built the M4 publish subsystem in four tested blocks, then hardened it with a full adversarial red-team — **by
hand** (Implementation has no challenger row; it is the deferred exception). Sandbox only; live `~/.claude`
untouched; **not committed.**

**Built (Blocks A–D).** (A) The data-driven **publish engine** — one `_place_block(doc, block_key, scope,
anchor_slug, placement, body)` core with both-ends-identity markers, seeded per-location anchors, and the
`0/0 → insert · 1/1 → replace · else → refuse` fail-closed guard; the old key-only `cmd_publish` retired.
(B) The **four review rows** as data (design → DECISIONS/log; architecture → ARCHITECTURE/section, `block_key`
`arch`; judgment → OVERVIEW/log sharing Need's anchor; shipping = **no publish half**); `implementation` has no
row; the challenge-context half is a structurally-shared frozen contract. (C) **Test migration** to M4 (the 44
M3 checks migrated + expanded to **121** on 3.12.7, across `test_workflow`/`test_flow`/`test_publish`/
`test_publish_modes`/`test_seed_docs`). (D)
**Seeded the real docs** (OVERVIEW/DECISIONS/ARCHITECTURE anchors; ARCHITECTURE's `## Workflow machinery` body
wrapped once as section `workflow-machinery`; the M3 subsection marked superseded) + `*.md text eol=lf`.

**Red-team — the Step-4 team of attackers plus four convergence rounds.** Block A's team caught three blocking
defects (an **ungated publish** that wrote unvouched prose; a fence **silent-overwrite**; an unbounded
`append_section` scan). A fresh three-attacker team (correctness / fidelity / test-adequacy) then four focused
convergence rounds — all on Sonnet, reading the real code/docs — caught **eight more, every one real and
reproduced**: the published **ENTRY was not tied to the receipt** (a stale, or cross-`--section`, entry could
publish — closed by clearing the entry at `record` before the receipt, and consuming it at `publish` before the
write, both fail-closed, so every publish needs a fresh entry); a test **false-green** (publish was never tested
against a *stale* receipt); and the code-fence fail-closed guard (RISKS #12) defeated **five** distinct ways —
` ``` `-only, mismatched delimiters, an invalid backtick info-string, bare-CR line endings, and over-broad
whitespace-stripping. Each was fixed; the guard's fence rules were **cross-validated against the CommonMark reference
parser during round 4 of the red-team** (the committed tests are stdlib-only, hand-written to the
spec's fence rules — there is no reference-parser dependency in the repo) and pinned by ten checks
(A19–A19i). **Eleven blocking defects total, all fixed** — direct evidence for Judgment that
the adversarial loop earns its cost (a single review pass would have shipped the fence fail-open and the
cross-scope entry publish).

**Human calls settled (R2).** CB1 (entry-not-tied-to-receipt) → **cheap guard + document** (not a stronger
mechanical tie); the **reference-validated fence state machine accepted** (over simplifying to refuse-if-any-fence);
the drafted-prose file **renamed** `overview-entry.md → publish-entry.md`; the ARCHITECTURE M3 subsection **marked
superseded**, its milestone text kept.

**Proof (T2).** Every mode proven byte-level on *fixtures matching the real docs' structure* (LF + CRLF,
cross-task no-clobber, shared-anchor interleave, fail-closed on malformed/fenced/bare-CR input); all four review
rows exercised end-to-end through the CLI; the *actual committed* docs proven valid publish targets **read-only**
by a committed test (`tests/workflow/test_seed_docs.py` — `_place_block` simulated in memory, byte-identity
asserted). **121/121 on 3.12.7** (5 suites).

**Amendment to the settled Need's proof (consciously cleared, rule 3).** The "44 existing checks stay green"
clause is renegotiated to match what happened: the 29 verb-lifecycle + flow checks carried forward (two flow
assertions updated for the new marker format); the 15 M3 publish checks tested the *retired* M3 sentinel format
and were **rewritten/retired**, not kept; the suite migrated to 121 (adding the mode + seed-docs suites).
Coverage rose; no stated bar is silently unmet.

**A caveat written into the record (rule 6).** "Dogfooded end-to-end" for the four new rows means the
**deterministic chain** only — the suite scripts the challenger's canary echo; it does not spawn a real
challenger. Unlike M3's Need row (a live Sonnet challenger, three rounds), the new rows have **not** had a live
real-challenger smoke-test; one against at least one new row is **owed** before treating this on par with M3
(the M2→M3 discharge pattern).

Residuals documented: RISKS #10 (mixed-newline, now LF-pinned), #11 (no compare-and-swap → M5), #13 (entry vs
draft), #14 (`--update` wrong-slug). A new PLAYBOOK recipe captures the doc-seeding method. **Next: Step 5
(Judgment).**

### 2026-07-14 — Workflow machinery M4 (complete the step set): Step 3 (Architecture) settled
Ran M4's Architecture step **by hand** (fresh challenger, **two rounds**, grep-verified against the REAL
`cmd_publish`, tests, and docs; converged 3+3 blocking/material → clean). The internal structure for the
settled one-engine design:

1. **Engine factoring (A1'):** one `_place_block(doc, block_key, scope, anchor_slug, placement, body)` core
   owns identity-match + the `0/0|1/1|else` fail-closed guard + replace; the ONLY branch is insert position —
   `prepend` (log, after the anchor, newest-first) vs `append_section` (section, after the last
   `WF:<block_key>:*` end-marker following the anchor — **stable order, sections never reorder**). A thin
   `cmd_publish` reads the RECIPE and dispatches; the old key-only publish body is **retired**.
2. **Schema + section safety (B/B1'):** publish half `{mode, doc_target, block_key, anchor_slug}`;
   `mode:log`→(scope=task_id, prepend), `mode:section`→(scope=section-slug, append_section). The architecture
   step's `block_key` is **`arch`** (not "architecture"). Section writes require `--section <slug>` + explicit
   `--new` (0 existing) / `--update` (1 existing) → fail-closed on count mismatch. Residual (typo to a
   *different existing* slug on `--update`) accepted as **human-diff-gated** (→ RISKS), not a registry.
3. **Grammar + full RISKS #12 (C):** both-ends `(key,scope)` markers, column-0 whole-line; anchors
   `WF:anchor:<slug>`, `findall`+count == 1 else fail-closed; the entry-content guard is **key-agnostic**
   (rejects ANY column-0 WF marker line — closes RISKS #12's second half) **and** the fence carve-out
   (a same-scope fenced marker → count 2 → refuse). Both halves delivered.
4. **Seeding + placements (D):** manual one-time seed (documented in PLAYBOOK); concrete anchors — OVERVIEW
   `current-status` under `## Current status`; DECISIONS `decisions-log` under the intro blockquote (no `##`
   heading exists); ARCHITECTURE `architecture-sections` under `## Workflow machinery`, its existing body
   wrapped once as section `workflow-machinery`.
5. **Migration (E):** **no real-doc migration** (only the sandbox holds old-format markers); re-express the
   five rows (shipping = none).
6. **Tests (F):** rewrite ~11/15 `test_publish.py` checks + both helpers, **retire #14** (heading-prefix —
   that mechanism is gone), fix `test_flow.py` 2/4, add `test_publish_modes.py` (log-accumulate cross-task;
   section append/replace; `--new`/`--update`; the guards; LF+CRLF) — byte-level, fixtures from real bytes.

**Minors → Implementation:** make the entry-guard's column-0 qualifier explicit; require exactly one of
`--new`/`--update`; fence-guard the `append_section` scan; state the honest test count. **Next: Step 4
(Implementation)** — build in blocks, each red-teamed by the Step-4 team of attackers, dogfooding each row
through the machinery (proof #4). Sandbox/by-hand; **not committed**.

### 2026-07-14 — Workflow machinery M4 (complete the step set): Step 2 (Design) settled
Ran M4's Design step **by hand** — its `design` row does not exist yet (that is what M4 builds; the
machinery dogfood resumes per-row at Implementation). A **fresh** challenger attacked the options over
**three rounds** against the REAL `cmd_publish` and target docs, breaking three of four first-draft
recommendations on contact, then converging clean (findings 4+4 → 0+3 → clean). Five decisions:

1. **Log-accumulate (OQ1):** both-ends full-identity markers `<!-- WF:<key>:<scope>:start/end -->`
   (`scope = task_id`); a task matches only its own `(key,scope)` pair, so tasks **accumulate**
   newest-first instead of clobbering. Fixes the key-half of RISKS #12; a **marker-format change**
   (round 1 killed the "tiny search tweak" framing), **zero migration cost** (no real doc carries WF
   markers — only the throwaway sandbox).
2. **Sectioned replace-or-create (OQ2):** the *same* markers with `scope = section-slug` — replace a
   section in place or create it at a seeded anchor. **Unified with #1 into one sentinel engine**,
   parameterized `(scope: task_id | section-slug) × (placement: prepend | replace-or-create)`.
3. **Shipping (OQ3): no publish half** — a **second exception** alongside Implementation. No valid
   auto-target exists (`claude/CHANGELOG.md` is hook-parsed semver; `docs/CHANGELOG.md` is absent;
   RISKS/PLAYBOOK are shape-rich and human-curated). RISKS/PLAYBOOK/CHANGELOG/commit stay human at
   Shipping — recorded as the second exception in RISKS.
4. **Cold bundle (OQ4): unchanged** — full `prior_settled` inclusion + a RISKS tripwire; no summarizer
   (measure, don't speculate — rule 8).
5. **Anchors:** seeded, **per-location** `<!-- WF:anchor:<slug> -->` sentinels (shared across keys, so
   `need`+`judgment` interleave under one `OVERVIEW` anchor), not fragile heading text (DECISIONS has
   no `##` heading; headings collide and drift). One-time seed + a **bounded** retrofit (wrap
   ARCHITECTURE's hand-written `## Workflow machinery` section once, else create-if-absent duplicates it).

**Amendment to the settled Need's proof #4 (consciously cleared, rule 3):** the three publishing steps
(design/architecture/judgment) prove `prepare → challenge → record → advance → publish`; **Shipping
proves `prepare → challenge → record` only** (it is terminal — no publish, no advance).

**Also folded:** `*.md text eol=lf` in `.gitattributes` (closes RISKS #10 for docs); the log/section
counting guard and the RISKS #12 fence fail-closed guard are implemented together, with tests for both.
**Next: Step 3 (Architecture)** — the engine's internal factoring and *where* a new ARCHITECTURE section
gets seeded. Sandbox/by-hand; **not committed**.

### 2026-07-14 — Workflow machinery M4 (complete the step set): Step 1 (Need) settled
Opened **M4** and ran its Need step as a **dogfood on the real M3 machinery** — the first non-toy run of
`workflow.py` (`start → prepare →` a real challenger over **three rounds** `→ record → publish → advance`),
with the canary/receipt honest floor live throughout. Sandbox only; live `~/.claude` untouched; **not committed**.

**Scope — human-sliced this session** (of the M4 defined in the entry below + WORKFLOW's M4 line): build the
**four remaining review-style rows** (`design`/`architecture`/`judgment`/`shipping`) as data, and generalize
`publish` to the document **shapes** they truly write — **log-accumulate** (a dated-log prepend that accumulates
across tasks) and **sectioned replace-or-create** (region-anchoring). **Deferred, recorded:** Step 4's
built-in-tool attacker team, the research-helper, and forcing the cold read (α-2). Deferral criterion is
**mechanism, not effort** — the Implementation team is a genuinely different attack mechanism (built-in code
tools, no prose canary) with an open feasibility question; the four review steps (incl. Judgment) share the
prose-challenger mechanism, so they are cheap rows.

**Two human calls made at Need (R2):** (1) the scope slice above; (2) **RISKS #12 fence half** — the residual
"sentinel-shaped line inside a ``` code fence" path is made **fail-closed (refuse), never a silent overwrite**;
**full** fence-aware parsing stays a narrowed, still-open RISKS #12 (hazard downgraded corrupts→refuses).

**A real latent bug the challenge surfaced (folded into scope):** M3's `need → OVERVIEW` publish matches its
block by sentinel **key alone**, so a *second* task would clobber the first task's entry — `need → OVERVIEW` is
itself a **log-accumulate** target. M4's log-accumulate mode fixes this while preserving the proven single-task
behaviour (a correction, not a churn).

**Proof-of-success (T2):** every new mode proven surgical at the **byte level** on real docs (LF + CRLF,
cross-task no-clobber, fail-closed on malformed input); a column-0 fenced sentinel pair triggers a fail-closed
refusal; each of the four steps dogfooded end-to-end; the 44 existing checks stay green + new tests, on 3.12.

**Converged clean over three challenger rounds (findings 9 → 2 → 0).** **Open for Design/Architecture:** the
log-accumulate mechanism (task-scoped sentinels?), region-anchoring bounds + create-if-absent, Shipping's scope
+ cross-file partial failure, and whether the growing cold bundle needs a selection policy. **Step 2 (Design) next.**

### 2026-07-14 — Workflow machinery M3 (walking skeleton): Step 4 (Implementation) built + proven
Step 4 of the M3 dogfood — the first step that builds and runs real code — is done: the **production
Need-slice machinery**, built in small blocks (each red-teamed before the next), then proven end-to-end on
a toy Need task. All in the **isolated test project**; live `~/.claude` untouched; **not committed** (owner
approval pending).

**What was built (bundle-destined):** `claude/workflow/workflow.py` — the M2 spine hardened, plus the
two-halved `RECIPE` (only the `need` row filled), α-1 `prepare` (bundles the rulebook as a framing header;
ordered COLD→WARM; canary at the end of COLD), the new `publish` verb (D-1, fail-closed, β-2 sentinels),
and a TOCTOU guard on `record`. Plus `claude/workflow/rulebook.md` (nine rules extracted),
`claude/agents/challenger.md`, `claude/workflow/conductor.md`. **Harness-only** (not shipped):
`tools/wf_drift_guard.py` (report-only byte-compare) and three test suites (`tests/workflow/`, **44 checks**).

**Method — the Step-4 team of attackers.** Each block was attacked by four context-free lenses (bugs /
does-it-run / readability / safety) **plus** a custom **fidelity** attacker (does the code match the settled
Need/Design/Architecture?), then — because the fixes touched load-bearing code — a **second adversarial
round** verified each fix closed and hunted regressions. Round 1 caught real defects, all folded: a
whole-file **LF→CRLF flip** on every Windows `publish`; **sentinel-substring corruption** (a doc merely
*mentioning* the marker syntax could be miscounted then overwritten → now line-anchored, column-0); a
**non-ASCII title** crashing `start`/`status` *after* the state write; a **`record` TOCTOU** (a draft edited
between `prepare` and `record` could mint a fresh receipt for unchallenged bytes); an `artifact_path`
**case-collision** (`docs/architecture.md` == `ARCHITECTURE.md` on Windows → renamed `docs/draft-<step>.md`).
The tests then caught a **second** bug the first fix introduced — `read_text(newline=)` is Python 3.13+ and
the developer runs 3.12 — fixed with raw-bytes I/O. Round 2 came back **clean on all four lenses** (no
blocking/material); residual minors are real-system/M4/M5 tripwires, now RISKS #10–#12.

**Proven (T2 — all four proof items met).** On a toy Need ("add a search command"), a **real challenger**
(Sonnet) attacked cold-then-warm over **three rounds** and genuinely converged (blockers → resolved → two
new materials surfaced *by the revision* → resolved → clean round — the adversarial loop working, not a
rubber stamp). Live: each revision **staled the receipt and blocked `advance`** until re-challenged
(proof #1); the canary was verified each round; `publish` did a first-write then an idempotent **re-settle to
one sentinel pair** (proof #2); `advance` opened only on a fresh receipt. The three `record` failure modes
(proof #3) are the automated forced-failure suite; replication-readiness (proof #4) was empirically confirmed
by the fidelity attacker across all five review-style steps. The honest split held: deterministic parts every
time; model-mediated parts (challenger spawn, warm pass) worked and are visible-on-miss.

**Next: M4** (the other four review-style steps, Step 4's built-in-tool team, region-anchoring, forcing).
Shipping the new bundle files (sync.py `MANIFEST` / directory-copy) stays **M6** — deliberately not done now,
since M3 must not touch live `~/.claude`.

### 2026-07-14 — Workflow machinery M3 (walking skeleton): Step 3 (Architecture) settled
Step 3 (Architecture) of the M3 dogfood is settled after a **three-round challenger cycle** (resumed on
Sonnet, converged clean at Round 3). Architecture decides the *internal structure*; M2 already fixed most
of it (marker, six verbs, honest-floor + canary, advance-gate), so this was the **thin Need-slice map**.
Two decisions were the human's to make.

**A — how the challenger gets its shared rulebook: chose A-1 (script bundles it into `context.md`), NOT
A-2 (challenger reads it by path).** A-1 concatenates the extracted nine-rule rulebook into the challenge
bundle, so the rules sit in the one file the challenger provably reads (canary-adjacent). Traceable to the
settled M2 spine — *the script assembles verified-correct context*, and the rules are part of correct
context — and to M3's make-failure-visible philosophy: under A-1 a rules-missing attack can't happen
silently. **Why A-2 lost:** cleaner P4 separation, but presence becomes model-mediated — "ran without its
rules" is a silent, unsignalled miss. **A-3 rejected** (rules inlined in the agent) — fails MUST DO 2's
"extract into one shared file."

**D — does the auto-docs write get its own verb: chose D-1 (new `publish <step>` verb), NOT folding into a
settled verb.** `publish` reads a model-drafted `overview-entry.md` and places it between β-2 sentinels,
with a fail-closed contract (missing/empty entry → no write; malformed/duplicate sentinel pair → refuse
rather than corrupt a real doc; atomic write). Chosen because it leaves the M2-settled verbs (`advance`,
`record`) **exactly intact** — directly consistent with the α-1 ruling last step (don't churn settled
contracts) — and a single-responsibility verb is what proof #2 (idempotent re-run) needs. **Why D-2/D-3
lost:** folding into `advance` (gate) or `record` (runs every round) modifies a settled verb and muddies
re-settle semantics. *Elevated to a human fork mid-cycle:* the challenger flagged that adding a **seventh**
verb to the spine Need MUST DO 1 enumerates is a real interface change R2 forbids picking silently — so it
went to the judge alongside A rather than being pre-filed as builder-tightening.

**The honestly-bounded replication story (the challenger's central catch, twice).** The skeleton's
per-step `RECIPE` has two halves. The **challenge-context half** (context sources + attack angles) is a
frozen contract the **five review-style steps** (Need/Design/Architecture/Judgment/Shipping) reuse by
adding a row. The **publish half** is a v0 seeded on one single-writer-prose slice. **Both halves name
Step 4 (Implementation) as their exception → M4:** its *team of attackers* (four context-free built-in
tools + one custom fidelity subagent) doesn't use the cold/warm/canary/receipt machinery on the challenge
side, and it writes code, not sentinel-prose, on the publish side. The challenger caught this same
over-generalization first on the publish half, then — after the fold — on the challenge half I'd declared
clean; both are now bounded, and M3 claims only what it proves (the Need slice of each), with M4
validating per-step fit as it builds, not pre-certifying it.

**Operator-habit fit (warm pass).** The Need-slice code reaches the isolated test project by a
**per-iteration** repo→test-project copy — a *third* sync direction `sync.py` doesn't cover. Because the
operator's documented habit is tool-mediated propagation / never manual-diff, that copy gets a cheap
**report-only byte-compare drift guard** modeled on `sync.py status` — harness tooling, not shipped
machinery — so a forgotten re-copy that runs stale code is made visible, not eyeballed.

**Dogfood method note (reusable):** the challenger ran on **Sonnet, resumed across three rounds**, ruling
each of its own prior findings resolved-or-not by cite-the-line. It caught six real fit findings (five
material Round 1, one residual Round 2), all folded; the cargo-cult check (Step 3's job) did exactly its
job — the recommendation didn't flip this time, but the *architecture's honesty* changed materially. M3's
own dogfood record stays **manual** (this entry, by hand).

**Next: Step 4 (Implementation)** — build the Need-slice code in small tested blocks and run it end-to-end
on a toy task. Architecture artifact preserved in the session scratchpad (`m3-architecture-draft.md`,
settled). **No commit yet** (owner approval pending).

### 2026-07-14 — Workflow machinery M3 (walking skeleton): Step 2 (Design) settled
Step 2 (Design) of the M3 dogfood is settled after a **three-round challenger cycle** (resumed on
Sonnet, converged clean at Round 3). Design decides the *approach*; two decisions were in scope.

**α — cold/warm challenge delivery: chose α-1 (ordered-visible, honest), NOT α-2 (presence-
sequenced / forcing).** α-1 hands the challenger one bundle (cold + warm, delimited), instructs
"cold verdict first," and returns verdicts in order — honestly labelled as *surfacing* whether a
cold read happened, **not forcing** one. Traceable to the Need: MUST DO 3 sanctions ordered-visible
and requires honest *separation*, **not** forcing. Chosen because a walking skeleton should stay
thin and **leave the M2-settled verbs intact**, and because forcing lives in the *shared* machinery
(one `workflow.py`, one adaptable challenger), so adding it later is a single-site change.
**Why α-2 lost:** it makes cold-read contamination impossible (under our threat model) but only by
**extending the M2-settled contracts** — `prepare`→two-phase, `record`→per-phase, +a warm-release
gate — too much settled-architecture churn for a thin skeleton now, and cheaply reversible later.

**The conscious call being ratified (challenger's observation):** for *this one decision* we accept
a failure mode with **no clean trace** — a warm-contaminated "cold" verdict is *suspectable, not
detectable* — which the firing machinery elsewhere refuses (the M2 precedent against self-authored
"confident mistakes"). Defensible from the record: the Need author put ordered-visible on the table
knowing its failure isn't cleanly visible.

**Forcing deferred to an *observable* trigger** (not the killed "detect contamination" trigger):
when the warm set grows materially beyond `OPERATOR.md`, or when the M4/M5 control layer is built.
**Owner-anchored** on the `WORKFLOW` M4 build-plan line so the deferral isn't forgotten (P2).

**β — auto-docs authorship: chose β-2 (model drafts prose, script places between sentinels).** The
model writes the settled-Need prose; the script places it between stable sentinels — **prepend
newest-first** on first write (matching `OVERVIEW`'s real prepend-log convention), **replace in
place** on re-settle. Structural idempotence (no duplicate block) satisfies proof #2; semantic drift
between redraws is accepted (proof #2 forbids duplicates, not drift). Keeps the honest split
**model owns wording, script owns placement**. **Why β-1 lost:** a deterministic template is rigid
— real `OVERVIEW` entries are prose, not fielded — and adds a fiddly structured-field contract.
Confirmed **no M4 scope leak**: sentinels do single-writer write-placement, not shared-doc hashing
(region-anchoring stays M4).

**Dogfood method note (reusable):** the recommendation **flipped α-2 → α-1 mid-cycle** because the
challenger disclosed a cost the builder had missed (α-2 extends settled M2 verbs) — the adversarial
process working as designed, not a builder whim. β-2's two write-mechanism gaps (insertion position;
an over-broad "idempotent" claim) were both closed under challenge. Deferred refinements logged: β
diff-on-re-settle and multi-task position-drift → real system.

**Next: Step 3 (Architecture).** Settled at the human's call; Design artifact preserved in the
session scratchpad (`m3-design-draft.md`, v3). **No commit yet** (owner approval pending).

### 2026-07-14 — Workflow machinery M3 (walking skeleton): Step 1 (Need) settled
Opened **M3 — the walking skeleton**: build the *real* machinery for ONE workflow step (Need), thin
but complete, to prove the builder -> challenger -> judge -> auto-docs pattern before replicating it
for the other five steps (M4). Run as the six-step dogfood (builder + a fresh challenger subagent per
round + human judge), same as M1/M2. **Step 1 (Need) is settled** after a **five-round challenger
cycle** (findings converged 11 -> 4 -> 1 -> 0-clean). The settled Need lives in `OVERVIEW` (top status
entry).

**Scope decided (human judge):**
- **Skeleton the Need step first**, proven in an **isolated test project** (`init-project-docs`-
  scaffolded docs; its own project settings; live `~/.claude` never touched).
- **Nudge hook -> M5** (not M3): M3 is the model-driven core + auto-docs; the nudge — already proven
  live in the M2 spike — joins the ambient control layer later. The `PreToolUse` skip-warner is
  Implementation-specific, also out.
- **Auto-docs writes `OVERVIEW` only**; seeding `ARCHITECTURE` (the Step-1 spec's second write) is a
  conscious deferral to M4.

**A settled decision reopened (challenger round 3; human ruled):** `ARCHITECTURE`'s "M3 must design
region-anchoring" is **moved to M4**. In M3 the Need step is the **single writer** of `OVERVIEW`, so
whole-file hashing is correct here. The real trigger for region-anchoring is a doc being **shared
(multiple writers)** — **not** in-place-vs-log, a mischaracterization the challenger caught and killed
twice (`OVERVIEW` is in-place yet becomes shared once Judgment also writes it). Region-anchoring first
bites in M4 at the first shared-writer target — a log (Design->`DECISIONS`) **or** a shared in-place
doc (Judgment->`OVERVIEW`). `ARCHITECTURE` synced this turn (P2).

**Dogfood method note (reusable):** the challenger ran on **Sonnet, resumed across rounds** so each
round drills into the last — judging whether its *own* prior findings were actually resolved
(cite-the-line), not a rubber stamp. It caught a **regression the builder introduced in v3** (the
in-place-vs-log dichotomy) — which is why the *single-writer/shared* and *cold/warm* distinctions are
load-bearing. M3's own dogfood record stays **manual** (this entry, by hand): auto-docs is proven only
inside the throwaway harness, never against the real repo docs.

**Next: Step 2 (Design)** — paused here at the human's call (a clean checkpoint). Need artifact
preserved in the session scratchpad (`m3-need-draft.md`, v4). **No commit yet** (owner approval pending).

### 2026-07-14 — Workflow machinery: M2 condition discharged — live smoke-test passed (caught a real bug)
Ran the live smoke-test that M2's "go, with conditions" verdict was gated on: launched Claude Code
inside the isolated spike project and drove real prompts. **All three live signals confirmed** — the
status line shows `wf: [need!]`; the `UserPromptSubmit` nudge injects the challenge reminder; the
`PreToolUse` skip-warner forces a confirmation on a code write before Implementation.

**The gate earned its keep — it caught a bug the entire off-session suite missed.** The nudge was
*silently inert* live: it printed a bare `{"additionalContext": ...}`, but Claude Code only honours the
wrapped shape `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ...}}`
and drops the bare form. Worse, the record shows the *earlier* fix (Shipping, same day: bare text →
bare JSON) was itself wrong — bare JSON is the one format that fails. The unit tests passed through
**both** wrong versions because they asserted an *assumed* output shape, not the real contract (now
verified against the Claude Code hooks docs). Fixed in the spike to the wrapped form; the test asserts
that exact nesting.

**Proven without fooling ourselves — registered ≠ executed ≠ honoured.** `/hooks` showed all three
registered; a temporary fire-probe (a log line at the top of each hook) proved Claude Code *executes*
them; behaviour proved the *output* is honoured. The nudge was isolated by moving the project
`CLAUDE.md` aside, so post-fix workflow awareness could come *only* from the injected context. The
skip-warner was isolated with a **self-evidencing two-write test**: with Write auto-allowed, a *doc*
write stayed silent while a *code* write at step `need` forced a prompt — the difference can only be
the hook.

**Honest caveat:** the skip-warner's gate fires, but its custom `permissionDecisionReason` did **not**
visibly surface — a generic "Allow write?" prompt appeared both times. The speed-bump works; the
"here's why" does not show on this setup. Logged as an M3 refinement, not a blocker.

**Verdict: M2's condition is discharged — M2 fully passed, M3 unblocked.** The owed live half is now
proven. The residual (the model *choosing* to spawn the challenger, ~70–80%, unforceable) stands
unchanged and is handled by design — a miss is visible, not impossible (RISKS #9). The spike stays in
the scratchpad (throwaway); the corrected contract (wrapped `hookSpecificOutput` for
`UserPromptSubmit`) is carried into M3 via this entry and the PLAYBOOK recipe.

### 2026-07-14 — Workflow machinery: M2 judged (go, with conditions) and shipped (Steps 5–6)
Ran the last two steps of the M2 dogfood. **Built** the throwaway de-risk spike — an isolated test
project holding `workflow.py` + a per-task marker + two read-only hooks + a status line, all wired by
its *own* project-scoped `.claude/settings.json` so the live `~/.claude` was never touched — then put
it through **Judgment (Step 5)** and **Shipping (Step 6)**.

Evidence (all gathered off-session):
- **Deterministic chain: proven, no false-green.** 28 automated checks cover the marker lifecycle, the
  advance-gate (refuses on *missing* and on *stale*), fail-closed `record` (missing result / wrong
  canary / unreadable artifact each write no receipt), raw-byte hashing (a one-byte edit flips
  fresh→stale), and `advance --force` recording an honest "missing (overridden)". A fidelity attacker
  found no path that writes a green receipt on bad input.
- **Context delivery is load-bearing.** A with/without-context control (two runs per arm) showed the
  operator-specific catch appears only when the machinery hands the challenger `OPERATOR.md`. It did
  *not* flip the gate outcome — realistic proposals carry other generic flaws a cold reader also
  blocks on — which is an honest limit, logged rather than hidden.
- **Payload schemas verified against the docs**, which caught a real bug: the nudge hook printed bare
  text instead of the `additionalContext` JSON Claude Code requires, so it would have been silently
  inert live while unit tests stayed green. Fixed; the test now asserts the injection *format*.

**Verdict: go to M3, with conditions.** The deterministic core clears its bar; the reframed bar
("every model-mediated failure is *visible*") is proven off-session but its live half is still owed, so
M3 is gated on a **live smoke-test** — hooks + status line actually fire in a real session, and marker
transitions read from a fresh chat. Firing is model-mediated (~70–80%, unforceable) by design; the
machinery makes a miss visible, not impossible.

**Theory improvements this dogfood surfaced** (folded into `WORKFLOW.md` challenger rules, and inputs
to building the real challenger at M3): rule 3 — a challenger may attack *any relevant* decision,
including settled ones, defended from the written record, with the **human** ruling on reopen and
reopening **capped** to one round / one hop so it can't cascade endlessly; rule 5 — return the **full
findings list tagged blocking / material / minor**, only blocking+material extend a round; rule 6 —
read in **two passes, cold then warm**, because context sharpens but also anchors. These were
themselves found by turning a fast-model attacker on the proposed changes, which improved all three and
caught the cascade trap. Also fixed an honest-accounting gap the Judgment attacker flagged: the
OVERVIEW proof-of-success said firing rate would be "measured"; that was renegotiated at Design to
"made visible, not measured", and OVERVIEW now matches so no stated bar is silently unmet. The spike
code stays in the scratchpad (throwaway, never bundled under `claude/`); this entry plus the
ARCHITECTURE "Workflow machinery" section are its durable write-up (T1).

### 2026-07-14 — Workflow machinery: structure settled (M2 Step 3, Architecture)
Third step of the M2 dogfood. Settled the internal structure and the boundaries between parts after
one moderate challenger round plus a confirming pass (both light, per rule 7 — the hard calls were
made at Design). Written in full into `ARCHITECTURE.md` ("Workflow machinery" section); the shape and
the decisions that moved:
- **The map:** one `workflow.py` (a command-line tool *and* an importable library) is the spine and
  the by-convention sole author of every truth signal; a per-task `.workflow/marker.json` it owns; one
  *adaptable* challenger agent (`claude/agents/*.md`, a net-new dir); two read-only, non-blocking hooks
  (a self-silencing `UserPromptSubmit` nudge, a `PreToolUse` human-confirm skip-warner); the status
  line extended to show step + receipt state; a few conductor lines in the project `CLAUDE.md`. All of
  it isolated in a throwaway test project's own `.claude/settings.json` — confirmed against the docs
  that `statusLine` and `hooks` are honored at project scope, so the live `~/.claude` is never touched.
- **Six verbs:** `start` (human bootstrap; refuses if a task is already open), `prepare` (assemble the
  context bundle + plant a canary), `record` (check the echo, hash the artifact, write the receipt —
  fail-closed: any failed check writes *no* receipt, exits non-zero, stays visible), `advance` (the
  gate; `advance --force` is a *recorded* human override), `status` (+ the one shared
  fresh/stale/missing function the status line and hooks import), `reset`.
- **Two Design-era cruxes closed here.** Crux (c), the receipt-authorship boundary: **accept-and-
  document, do not enforce** — "sole author" is a convention (the model *can* write those files); we
  accept it because the guarded failure is *omission* (forget to fire → no receipt → visible), and
  faking a receipt on a single-user tool serves no one. And the challenger caught a real clash between
  two settled things — Design's "advance is gated" vs the Need's "warn, never block": resolved with
  `advance --force` recording a visible override, so the gate stops *accidental* skips while the human
  keeps the wheel.
- **Honest ceiling made permanent (crux (b), resolved by reasoning — no experiment needed):** because
  the *model* spawns the challenger, it can read the canary and echo it itself, so the challenge-ran
  light is self-reported *forever*, never "verified." The canary is kept but demoted — it catches an
  *honest* wrong-context mistake (wrong/truncated bundle → echo fails → no receipt → reads "missing").
  This shrinks Step 4: it no longer chases "reach verified," only "does the canary catch a
  wrong-context run."
- **One adaptable challenger** (not one file per step) for the spike — the rules are constant, the
  per-step specifics come from the bundle. Does not prejudge the eventual real system.
- **Honestly deferred (recorded, not solved):** region-hashing inside shared append-logs (the spike's
  hash-gate is valid only for *single-file* artifacts; M3 designs anchoring); backward/regression
  movement (the spike won't exercise it); the `sync.py` directory-copy change for M6 (to be logged in
  RISKS at Shipping).
The confirming pass caught three faithfulness bugs in the *write-up* (a false "logged in RISKS"
pointer; the accept-and-document boundary not actually written down; a "stale" that should read
"missing") — all fixed before settling. Next: Step 4 (Implementation) — build the throwaway spike one
tested block at a time in an isolated test project, then run the experiment (deterministic chain works
every time; the canary reliably catches a wrong-context run).

### 2026-07-14 — Workflow machinery: firing strategy settled (M2 Step 2, Design)
Second step of the M2 dogfood (building the six-step workflow's own machinery; the settled Need is in
`OVERVIEW`). Settled the **firing strategy** after two challenger rounds + a confirming pass. Core
decision: a **deterministic `workflow` script — not the model — is the single independent author of
every verifying signal**, so the model still does the probabilistic acts (spawn the challenger, draft
artifacts) but never vouches for itself. This replaced a first draft where the model authored both an
action *and* its own status — which can only surface crude failures (missing/corrupt), never a
confident mistake (wrong-step advance, wrong-context challenge); the challenger showed that defeats the
Need's "every failure visible" guarantee.

The design:
- **State:** one gitignored, ephemeral per-task marker file — task id, current step, draft/settled, and
  a per-step receipt {challenge-ran, context-hash, artifact-hash}. Committed docs stay the cross-task
  memory; the marker is only the live task's state (absent = machinery inert here).
- **Two genuinely-deterministic guarantees** (confirmed solid by the confirming pass): the
  "challenge-ran" light is keyed to the artifact's **content-hash** and the status line hashes the
  *live* artifact directly, so any revision flips it to `stale` (no stale-green); and **advance is
  gated** — the script refuses the next step without a fresh receipt matching the current artifact, and
  even a direct-write bypass shows `MISSING` on the new step. Wrong/premature advance and stale-green
  are both caught.
- **Context correctness — honest floor + an upgrade to test.** Hashing the context *bundle* only proves
  the file is intact (which the script already knew) and the hash is couriered back by the model — so
  it is *not* proof the challenger consumed the right context. Decision (with the user): design the
  **honest floor** — label the context light *self-reported* (`chal:ok(self)`), never a false
  "verified" (the Need forbids a false "verified" but allows an honest "not sure"). The **upgrade** to
  attempt in the experiment: embed a fresh secret **canary token inside the bundle** that the
  challenger can only echo back if it truly read the content (real proof of *consumption*), earning
  "verified" only if that echo can also reach the script through a channel the model can't fake.
- **Nudge:** a `UserPromptSubmit` hook injects "a challenge is owed" **only when one actually is**
  (draft step, no fresh receipt) — self-silencing, not every-turn (every-turn cries wolf and gets tuned
  out).
- **Skip-warner:** a `PreToolUse` hook using `permissionDecision:"ask"` — a **human confirm**, never a
  block or a model-only whisper (matches "warn, human consciously clears"). Must distinguish *code*
  writes from *doc/artifact* writes so it doesn't fire when the builder writes its own design doc.
- **Entry:** natural-language bootstrap; the status line lighting up is the confirmation it took.
- **Dropped** the `SubagentStop` hook — open Claude Code bug #7881 means it can't reliably say which
  subagent finished or see its input, so it added nothing once we stopped trusting it.

What Step 4's experiment must de-risk (the cruxes the rounds surfaced): **(a)** the marker lifecycle
start→advance→reset from a *fresh chat*, each transition force-failed to confirm it honestly reads "not
done" — including that a *wrong* advance is detectable; **(b)** context *consumption* via the
canary-echo (a wrong/truncated-context run must read `stale`/`MISSING`, never `ok`), and whether that
echo can reach the script un-forgeably — else keep the honest self-reported label; **(c)** the
receipt/marker **authorship boundary** — "script is sole author" is a *convention* (the model *can*
write those files directly), sound under the omission threat model (forget to fire → visible) but not
enforced; decide at Architecture whether to enforce/tamper-detect or accept-and-document. Effort note:
ran Design lighter than Need (2 rounds + a confirming pass vs Need's 3), per challenger rule 7. Next:
Step 3 (Architecture) — marker/receipt file layout, the `workflow` script's verbs, and the
authorship-boundary decision.

### 2026-07-13 — `sync.py status` built & verified (Steps 2–5 of the pilot)
Implemented the report-only `status` command: a git check (uncommitted / ahead / behind / diverged,
via a timeout-capped `git fetch` that degrades to "couldn't reach GitHub" when offline) plus a
byte-compare of the `MANIFEST` bundle files against the live `~/.claude` (the repo-vs-live gap no git
command can see). It reports every condition that applies at once, returns exit 0 only when fully in
sync (else 1), and changes nothing. Reused the existing `MANIFEST` as the compare set and mirrored
`update()`'s subprocess style; `GIT_TERMINAL_PROMPT=0` + a fetch timeout keep it from hanging on a
dead network. Verified end-to-end on throwaway repos + a fake `HOME`: 17/17 checks across
not-installed, in-sync, repo-ahead-of-live, unpushed, GitHub-ahead, uncommitted, offline, and
plain-copy — plus a writes-nothing assertion on both `~/.claude` and the working tree. Testing caught
one real bug: an em dash in the output mangled on the Windows console, fixed to plain ASCII (matching
the rest of `sync.py`). Pending Step 6 (Shipping): version bump, `CHANGELOG`, and the commit/push
(user approves).

### 2026-07-13 — Workflow M1 (validate by hand) passed; two lessons folded into the theory
Ran the first real task (`sync.py status`) through the six-step adversarial workflow by hand (M1 in
`WORKFLOW.md`) and judged it a pass: it made a visibly better decision than a normal chat — the
challenger forced a throwaway experiment that killed an unsafe timestamp-based "repo is newer → run
install" hint before it became code, and the questioning reshaped the feature from an overwrite-guard
into a read-only status readout — and it left docs a fresh chat could resume from. Two lessons folded
back into `WORKFLOW.md`:
1. **The AI challenger is only as sharp as the written context it's handed.** The catch that reshaped
   the task ("I never edit the live files, so `install` can't overwrite them") was a tacit working
   habit written down nowhere, and a challenger subagent inherits none of the main chat's memory — so
   the human, not the AI, had to catch it. Fix: added **`docs/OPERATOR.md`** (repo-specific "how I
   work" facts, handed to the challenger each task) and extended challenger rule 6.
2. **"Match effort to novelty" (rule 7) doesn't fire by itself.** M1 ran near-full challenge rounds on
   a small, familiar feature and felt heavy. Fix: rule 7 now opens a task/step by sizing the work and
   setting the round count up front, starting light for familiar changes.
Next milestone: M2 — technical design + de-risk reliable automatic firing.

### 2026-07-13 — `sync.py status`: Need settled (Step 1 of the by-hand workflow pilot)
First real task run through the six-step adversarial workflow (`docs/WORKFLOW.md`, M1) by hand —
Claude as builder, a subagent as challenger, the user as judge. Step 1 (Need) reshaped the task twice:
1. **Direction can't be guessed from timestamps.** The first idea had `status` say which side was
   "newer" and recommend capture-vs-install. A throwaway experiment killed it: git stamps working-tree
   files at *pull/clone* time (not edit time) and `install` (`copy2`) preserves mtime, so after an
   unrelated pull the repo can look "newer" than an un-captured live edit — a timestamp-based "run
   install" hint would then destroy that edit. So the tool never infers direction from mtime.
2. **The original risk-#3 danger doesn't apply.** Established that the sole developer always edits in
   the repo then installs, never editing live files — so "install overwrites forgotten live edits"
   never occurs. The task was reframed from a danger-guard into a **report-only status readout**.
**Settled Need:** `sync.py status` reports, in plain English, where you stand across the whole chain —
**GitHub ↔ repo ↔ live `~/.claude`** — and what to do next. It never acts (no commit / push / pull /
install / file edits), reports every condition that applies at once, and degrades gracefully offline,
with no remote, or on a plain non-git copy. Its uniquely valuable part (no git command can see it):
"your live `~/.claude` is behind the repo — you haven't installed the latest." *How* to detect the
repo-vs-live gap and whether to emit a scripting exit code are Step 2 (Design). See OVERVIEW; RISKS #3
reframed.

### 2026-07-13 — Adversarial phased workflow designed & documented (`docs/WORKFLOW.md`)
Worked out a major new direction and captured it in `docs/WORKFLOW.md`: turn the declarative rules
into an **active six-step workflow** — Need → Design → Architecture → Implementation → Judgment →
Shipping — where at each step a *builder* proposes, a separate *challenger* (a subagent) attacks
across multiple rounds, the human judges, and the docs write themselves. Genuinely new vs. today: the
**challenger** (nine behaviour rules) and making the rules *run*; the rest maps onto existing
R/P/D/T + OODA. **Not built** — this records the design only; next is M1, validate the flow by hand
before building any machinery (R4 gate). Design settled across a long plan-mode session and persisted
so a fresh conversation can resume from the docs (the workflow's own lifecycle rule).

### 2026-07-13 — Status line: show context tokens and the quota reset time
Refined the status line's two data fields per the user (still v0.3.3, unreleased, so folded into
that release rather than a new version). `ctx` now shows the raw token count against the window
size beside the percentage — `ctx:8% 15.5k/200k` — from `context_window.total_input_tokens` (the
exact number behind `used_percentage`: input + cache, current usage, not output) over
`context_window_size`. `5h` now appends the window's reset time — `5h:34% @15:42` — from
`rate_limits.five_hour.resets_at` (a Unix epoch in seconds; `datetime.fromtimestamp` renders it in
the machine's local clock). Chose the **absolute** reset time over a relative countdown (`2h13m`)
so it never goes stale between refreshes and needs no `refreshInterval` polling — the line only
re-runs per message, so a countdown would sit frozen until you typed. Token counts abbreviate to
k/M to fit. Verified against payloads (200k + 1M windows, missing tokens/reset, floats, empty):
correct render — the reset clock matched an independently-computed local time — exit 0, no crash.

### 2026-07-13 — Version-control the docs; add `enable-statusline` to wire it per machine
Two follow-ups to the status-line entry below, both agreed with the user. (1) **Removed `docs/`
from `.gitignore`** — it had been ignoring the whole project doc set (this decision log,
`OVERVIEW`, `ARCHITECTURE`, `RISKS`, `CONTRIBUTING`, `PLAYBOOK`), so the methodology's own P1/P2
records were local-only: missing from a fresh clone and never synced. Only the root `CLAUDE.md`
was meant to be local (repo-navigation context); `docs/` being ignored looked unintentional — now
tracked. (2) **Added `sync.py enable-statusline` / `disable-statusline`**, mirroring
`enable-hook`/`disable-hook`: they write or remove the `statusLine` block in the personal
`~/.claude/settings.json` using this machine's `sys.executable`, so a new box wires its own
interpreter with one command instead of a hand edit — RISKS #7 resolved. Factored the shared
interpreter-path logic into `_python_command(script_rel)` so the hook and the status line build
their command identically (one home for the RISK #6 "never a bare python" rule). Verified
enable/disable against a throwaway home: enable adds the block (with `sys.executable` + the
deployed `statusline.py` path) and preserves other keys, re-enable refreshes idempotently,
disable removes only our key, and a second disable is a no-op.

### 2026-07-13 — Added a custom Claude Code status line to the bundle
Added `claude/statusline.py` — a stdlib-only (`json`) renderer that Claude Code runs on each
status refresh, printing a compact monochrome-green `mdl:… eff:… ctx:… 5h:…` line: model,
reasoning effort, context-window %, and 5-hour Max quota %. Those fields come straight from the
JSON Claude Code pipes in on stdin, so there is **no transcript parsing** — the docs confirm
`context_window.used_percentage`, `effort.level`, and `rate_limits.five_hour` are provided
directly. Chosen as Python (not bash + `jq`) to honour the repo's standard-library-only rule and
avoid depending on Git Bash/`jq` being installed; it reuses the same interpreter path as the
update hook. Optional fields degrade to *omitted* segments (`effort` and `rate_limits` are absent
for effort-less models / API-key accounts), and context shows `--` before the first API call — so
the line never shows an empty key or a misleading 0%. Added `statusline.py` to `sync.py`'s
`MANIFEST` so `install`/`capture` carry it like any bundled file, and wired it live via a
`statusLine` block in `~/.claude/settings.json`. **Known gap (RISKS #7):** `settings.json` is
personal and not bundled, so a fresh machine gets the script but not the wiring until an
`enable-statusline` command (mirroring `enable-hook`) is added — deferred as a follow-up. Bumped
VERSION 0.3.2 → 0.3.3. Verified against six stdin payloads (full, no-effort, no-quota, empty,
float-rounding, garbage): correct line, exit 0, no crash; bundle and live copies byte-identical.

### 2026-07-05 — Cross-platform via a single Python script; `.ps1` retired
Replaced the two Windows-only PowerShell scripts (`install.ps1`, `capture.ps1`) with one
cross-platform `sync.py` (`install` / `capture` subcommands, standard-library only). Chosen
because the user runs Python on every machine and wanted zero installs — bash isn't native
on Windows, PowerShell 7 isn't native on Linux, but Python 3 is present everywhere.
`Path.home()` resolves `%USERPROFILE%` vs `$HOME`. The file manifest now lives once inside
`sync.py`, so **RISKS #1 (duplicated manifest) is closed** and OVERVIEW roadmap stage 3
(cross-platform) is done. Added `.gitattributes` (`*.py eol=lf`) so the Linux shebang
survives Windows edits. Verified on Windows against a throwaway home: install lands all 3
files (hashes match), re-install backs up + refreshes, capture round-trips, bad usage exits
non-zero. Now confirmed on real Linux (Ubuntu) too: `HOME=/tmp/… python3 sync.py install` resolved
`$HOME`, created the nested `skills/…` path, and deployed all 3 files.

### 2026-07-05 — Root CLAUDE.md is local-only (gitignored)
Created a project-level `CLAUDE.md` at the repo root so working *in this repo* loads
repo-specific context on top of the global `~/.claude/CLAUDE.md`. It is added to
`.gitignore` and **not committed**, to avoid confusion with the bundled `claude/CLAUDE.md`
(which is the global core that ships to `~/.claude`). Trade-off: the root file won't sync
across machines — acceptable, since its content is repo-navigation only.

### 2026-07-05 — Project docs scaffolded
Standard documentation set created via the `init-project-docs` skill, following the personal
working methodology's naming convention. Roadmap framed around git-based sync and future
cross-platform support (see `OVERVIEW.md`).
