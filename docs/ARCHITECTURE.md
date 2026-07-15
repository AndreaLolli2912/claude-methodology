# Architecture

> The components, the boundaries between them, the contracts, and the tech stack. Update
> when components are added/removed or the stack changes.

## Components
Two layers, deliberately kept separate:

**Content (the bundle) — `claude/`.** The methodology itself, mirroring the layout of
`~/.claude`:
- `claude/CLAUDE.md` — the always-on core, loaded by Claude Code in every project.
- `claude/METHODOLOGY.md` — the full rule reference, read on demand.
- `claude/skills/init-project-docs/SKILL.md` — the docs-scaffolding skill.
- `claude/statusline.py` — the status-line renderer (model | effort | context | quota), run by
  Claude Code on each status refresh and pointed at by a `statusLine` block in `settings.json`.

**Transport (the script) — repo root.** Pure file-moving; it knows *nothing* about the
content's meaning, only which relative paths the bundle owns:
- `sync.py install` — repo → `~/.claude` (deploy; backs up what it replaces).
- `sync.py capture` — `~/.claude` → repo (reverse; stage live edits for commit).
- `sync.py status` — read-only readout of where you stand across GitHub ↔ repo ↔ live
  `~/.claude` (git ahead/behind/uncommitted + a byte-compare of the bundle vs `~/.claude`);
  it only looks and prints, never writes.
- `README.md` — human entry point (install / sync instructions).

One cross-platform script (Python 3, standard-library only) covers every OS; `Path.home()`
resolves `~/.claude` on Windows (`%USERPROFILE%`) and macOS/Linux (`$HOME`) alike. The
content/transport split is the key boundary: you can edit the methodology without touching
the script, and vice versa.

## Contracts
- **The file manifest.** `sync.py` holds one list of bundle-owned relative paths in its
  `MANIFEST` constant (currently the core, the full reference, the `init-project-docs` skill,
  `VERSION`/`CHANGELOG.md`, the update-check hook, and `statusline.py` — `MANIFEST` itself is
  the authoritative enumeration). This single list is the contract between transport and content — adding a file
  to the bundle is a one-line edit in one place. (This is why the old two-script manifest
  drift risk is gone; see `RISKS.md` #1.)
- **Path resolution.** `sync.py` anchors on its own folder (`Path(__file__).parent`, repo
  side) and `Path.home() / ".claude"` (live side). Moving the repo is safe; the live target
  follows the OS home directory.
- **Direction is authoritative one way at a time.** Repo is source of truth. `install`
  writes the live side; `capture` writes the repo side. Never run both expecting a merge —
  there is no merge, only overwrite (with a timestamped backup on install).

## Stack
| Technology | What it is | Why we use it |
|---|---|---|
| Python 3 (stdlib only) | The cross-platform `sync.py` install/capture script | Present on all the user's machines; runs on Windows/macOS/Linux with zero installs |
| Git | Version control + multi-machine sync transport | Repo is the source of truth; clone/pull/push is the sync path |
| Markdown | Format of the methodology + these docs | Claude Code loads `CLAUDE.md`/skills as Markdown; human-readable |

## Workflow machinery (M2 designed → M3 Need slice built → M4 completing the step set; 2026-07-14)

<!-- WF:anchor:architecture-sections -->

<!-- WF:arch:workflow-machinery:start -->

> A second, independent subsystem: the machinery that makes the six-step adversarial workflow
> (`docs/WORKFLOW.md`) actually *run*. Designed and de-risked in milestone M2; the throwaway
> spike that proves it is Step 4, and nothing here ships until M3+. The settled **need** is in
> `OVERVIEW` (2026-07-13, "Current status"); the settled **approach** is in `DECISIONS`
> (2026-07-14); this section is the settled **structure** (Step 3, Architecture).

**The one principle that shapes everything below:** a single deterministic script is the sole
*independent author* of every truth signal, so the model never vouches for its own work. The
model does the probabilistic acts (spawn the challenger, draft the artifact); the script does
every *verifying* act (write receipts, gate advancement, compute fresh/stale). See the DECISIONS
entry for why this replaced a same-author first draft.

### Components, and what each maps to in Claude Code
- **`workflow.py` — the spine.** A small standard-library Python module that is *both* a
  command-line tool (the verbs below) *and* an importable library (the one shared fresh/stale
  function). It is the *intended* sole writer of the marker and receipts — the "independent
  author" (a convention, not a platform lock; see the marker section).
- **The marker file — `.workflow/marker.json`** in the project being worked on. The live task's
  state (contract below). Gitignored and ephemeral: it is *this task's* memory, not the
  project's — the committed docs stay the cross-task memory. No marker present = machinery inert.
- **One challenger agent — `claude/agents/challenger.md`** (a net-new directory; today only
  `claude/hooks/` exists). *One adaptable file*, not one per step: the nine rules are constant,
  and each step's specifics arrive in the context bundle the script assembles. (WORKFLOW.md calls
  "a specialist per step" the principle and leaves file-vs-adaptable a build detail — this is that
  detail, settled as one file for the spike; it doesn't prejudge the eventual real system.)
- **Two hooks — both read-only on the marker, neither ever blocking:**
  - a `UserPromptSubmit` **nudge**: if the current step is a draft with no fresh receipt, it
    injects "a challenge is owed for step X"; silent otherwise. It self-silences because
    every-turn reminders get tuned out.
  - a `PreToolUse` **skip-warner** on Write/Edit: if *code* is being written while we're still
    before the Implementation step, it uses `permissionDecision:"ask"` to make the human
    consciously confirm — an "are you sure?", never a hard block. It tells code from docs by file
    extension plus a known-artifact whitelist (a folder rule would misfire on this repo's
    root-level markdown and on artifact writes).
- **The status line** extends `statusline.py` to show the current step and each receipt's state
  (fresh / stale / missing), by importing the one shared function from `workflow.py`.
- **The conductor** is a few lines in the project's `CLAUDE.md` that tell the model the per-step
  loop (below). It is model-mediated, so it *can* be skipped — which is exactly why the nudge and
  the visible receipts exist.

**Isolation boundary (why the experiment is safe — P4/P7).** The whole thing lives in one
throwaway test project with its *own* `.claude/settings.json` carrying both the hooks and the
status line. Confirmed against the Claude Code docs: `statusLine` and `hooks` are both honored at
project scope, and project settings override user settings — so the real `~/.claude` is never
touched or relied upon.

### The marker file — the contract every part reads
`.workflow/marker.json`, whose sole writer is `workflow.py`:
- `task_id`, `task_title` — which task this is.
- `current_step` — one of need / design / architecture / implementation / judgment / shipping.
- `receipts` — one per finished step; each holds `challenge_ran`, `context_hash` (the bundle
  handed to the challenger), `artifact_hash` (the step's product), and `pending_canary` (the
  secret token planted for the in-flight challenge, so a later `record` run — a *separate*
  process that shares nothing but this file — can check the echo).
- an `override` mark on a step — set when the human consciously advanced past the gate.

We deliberately do *not* store a "draft/settled" flag: that state is derivable (a step is settled
once we have advanced past it; the current step is a draft until it earns a fresh receipt), and a
schema should not carry a field nothing writes. All hashes are over **raw bytes**, so the status
line and `record` can never disagree because of Windows line-ending translation (this repo
already fights CRLF/LF via `.gitattributes`).

**Authorship is a convention, not a lock (crux (c), resolved: accept-and-document).** "Sole
writer" above means *by convention*: nothing on the platform stops the model from writing the
marker or a receipt directly — it can write any file the script can. We accept that unenforced,
because it is sound under our threat model. The failure we guard against is the model *forgetting*
to fire the challenger, and a forgotten challenge simply leaves no receipt — which is visible.
Deliberately faking a receipt would be your own tool lying to you, which serves no one on a
single-user machine; signing or locking would defend a threat that does not exist here, at real
cost. So we write the boundary down and rely on it, rather than enforce it.

### `workflow.py` — the verbs (the interface)
- `start "<title>"` — *the human* bootstraps a task: create the marker at step Need. Refuses
  (and says so) if a task is already open, rather than silently clobbering it.
- `prepare <step>` — assemble the challenger's context bundle from a fixed recipe into
  `.workflow/context.md`, plant a fresh secret canary inside it, and record it pending.
- `record <step>` — read the challenger's written result, check the canary echoed back, hash the
  live artifact, and write the receipt. **Its failure path is load-bearing:** any failed check
  (missing result, canary mismatch, unreadable artifact) writes *no* receipt, exits non-zero, and
  is visible — never a partial "green anyway." The whole honest floor rests on this.
- `advance` — the gate: by default it refuses the next step unless the current one has a fresh
  receipt whose artifact-hash matches the live artifact. `advance --force` lets the human
  consciously proceed *without* one and records "human overrode" on that step, so the bypass is on
  the record, never silent. (This reconciles Design's "gated" with the Need's "warn, never block —
  the human keeps the wheel," and gives a lighter path when a benign post-settle edit flips the
  hash.)
- `status` — print the marker; and expose the one shared `receipt_state(step) -> fresh | stale |
  missing` function that the status line and hooks import, so the freshness rule lives in exactly
  one place.
- `reset` — end the task, remove the marker.

### The model's per-step loop (from the conductor)
Propose -> `prepare <step>` -> spawn the challenger on `.workflow/context.md` -> the challenger
attacks and writes its result, echoing the canary -> `record <step>` -> bring the points to the
human -> on settle, `advance`. The model spawns and drafts; the script verifies.

### What the honest floor means — and its permanent ceiling
The "challenge-ran" light is **self-reported**: it can honestly say "the model reports the
challenge ran," never "independently verified." This is a *permanent* ceiling, not a gap to close
later. Because the *model* spawns the challenger, and the model can itself read the canary out of
the bundle and echo it, no on-machine trick can prove an *independent* party ran. The canary still
earns its place — it catches an **honest** wrong-context mistake (challenger ran, but on a
truncated or wrong bundle -> the echo fails -> `record` writes no receipt, so the light reads
*missing*, not fresh), which is the real failure mode under our threat model (forgetting/mistake,
not malice). A true "verified" would require the
*script* to spawn a headless challenger the model never touches; we rejected that — it defends
against your own tool faking a receipt (a threat that does not exist on a single-user machine) at
real cost. Accept-and-document stays sound precisely because the light never over-claims.

### Deliberately deferred (recorded here, not solved in M2)
- **Region-hashing for shared docs (moved to M4 — see DECISIONS 2026-07-14).** The spike gives each step its *own* file, so "the
  artifact" is one cleanly-hashable thing. The real docs are in-place living files
  (OVERVIEW/ARCHITECTURE) and prepend/append logs (DECISIONS/RISKS); whole-file hashing is correct only for a **single-writer** doc; it breaks on a **shared** doc
  written by several steps — and the trigger is *sharing*, **not** log-vs-in-place (`OVERVIEW` is
  in-place yet becomes shared once both Need and Judgment write it). **In M3 the Need step is the
  single writer of `OVERVIEW`, so whole-file hashing is valid here;** region-anchoring is therefore
  **M4** work, first needed at the first shared-writer target (a log like Design->DECISIONS, or a
  shared in-place doc like Judgment->OVERVIEW).
- **Backward movement / regression.** `current_step` only advances, but the workflow's own rules
  (reopen on contradiction; a no-go at Judgment sends work back) need a way to step back. The spike
  will not exercise it — flagged as not-yet-covered, not pretended-handled.
- **Deploying whole `agents/`/`hooks/` directories.** `sync.py` copies file-by-file; shipping the
  machinery (M6) needs a directory-copy change. To be logged in `RISKS` at Shipping (M6); not
  an M2 problem.

### M3 walking skeleton — the Need slice (settled 2026-07-14)

> **Superseded by "M4 — completing the step set: the publish engine" (below).** Kept as the dated M3
> milestone record. Mechanisms it describes were replaced in M4: the start-only `WF:need:start task="<id>"`
> sentinel (now both-ends-identity `WF:<key>:<scope>:start`/`:end`); the `## Current status` *heading* anchor
> (now a seeded `<!-- WF:anchor:<slug> -->` comment); the `{mode, doc_target, sentinel_key, anchor}` publish
> schema (now `{mode, doc_target, block_key, anchor_slug}`); and "the publish half does not generalize as-is"
> (M4 generalized it into `_place_block`). Read the M4 subsection for the current design.

> The **thin** Need-slice structure that hardens the M2 spike into production code for ONE step (Need),
> under the settled Design (α-1 ordered-visible cold/warm delivery + β-2 sentinel auto-docs). M2 fixed the
> marker/verbs/honest-floor/gate; this section adds only what the Need slice needs. Full rationale +
> the two human decisions are in `DECISIONS` (2026-07-14).

**The per-step recipe — one structure, two halves of very different reach.** A `RECIPE` dict in
`workflow.py`, keyed by step name, holds each step's specifics so nothing else is step-aware:
- **Challenge-context half** (`cold_sources`, `warm_sources`, `attack_angles`) — a **frozen contract the
  five review-style steps** (Need/Design/Architecture/Judgment/Shipping) reuse by adding a row; `prepare`
  consumes it. The rulebook/canary/receipt/gate are step-agnostic (M2). M3 proves it on Need; M4 adds the
  other four review-style rows, validating each fit as it builds.
- **Publish half** (`publish: {mode, doc_target, sentinel_key, anchor}`) — a **v0 seeded on one
  single-writer-prose slice** (Need→`OVERVIEW`); `publish` consumes it. It does **not** generalize as-is:
  M4 must enrich it (region-anchoring for shared docs, list-valued targets for Shipping, a code-output
  mode for Implementation, per-target anchor strategy).
- **Both halves name Step 4 (Implementation) as their exception → M4:** its *team of attackers* (four
  context-free built-in tools + one custom fidelity subagent) doesn't use the cold/warm/canary/receipt
  machinery on the challenge side, and writes code (not sentinel-prose) on the publish side. (The custom
  fidelity subagent *is* spine-compatible; the context-free built-ins + the fan-out/aggregate shape are
  what need new M4 wiring.)

**Rulebook delivery (Decision A → A-1).** The nine challenger rules are **extracted into one shared file**
(`claude/workflow/rulebook.md`, MUST DO 2). `prepare` **bundles the rulebook into `.workflow/context.md`**
as a framing header — so the rules sit in the one file the challenger provably reads (canary-adjacent
presence), rather than being pulled by a model-mediated path read that could silently miss.

**The auto-docs verb (Decision D → D-1) — a new `publish <step>`.** Added to the interface **without
altering any settled M2 verb**. The model drafts the settled-step prose into `.workflow/overview-entry.md`;
`publish` places it between β-2 sentinels. **Fail-closed contract** (it is the only verb writing a real,
committed doc): missing/empty entry → no write, non-zero; a `WF:<step>:start` with no matching `:end`, or
more than one pair for the key → **refuse** (never guess into a malformed doc); zero pairs → first-write
(prepend under `anchor`), one pair → replace-in-place; write is atomic (temp-then-replace).

**The contracts (P5) the Need slice adds:**
- `.workflow/context.md` (written by `prepare`, implements α-1): `[rulebook header] [two-pass instruction:
  cold verdict first] [attack angles]` then a delimited **COLD** section (canary token + the artifact +
  the settled docs) and a **WARM** section (`OPERATOR.md` + the usually-empty global-habits slot). One
  bundle, cold+warm visible and ordered — honest *surfacing*, not *forcing*. `context_hash` is over the
  file's raw bytes (M2).
- `.workflow/challenge.md` (written by the challenger, read by `record`): `## COLD verdict` (echoes the
  canary + ranked findings) then `## WARM verdict`. `record` needs only "a result exists + canary echoed";
  the ranked findings are human-facing. The canary proves the context was **read**, not that both passes
  ran (the honest self-reported ceiling stands).
- Sentinels (β-2): `<!-- WF:need:start task="<id>" -->` … `<!-- WF:need:end -->`; `anchor` for OVERVIEW is
  `## Current status` (an OVERVIEW-specific value — part of the non-generalizing publish half).

**Files + how they reach the test project (MUST DO 8).** Bundle-destined, production-quality:
`claude/workflow/workflow.py` (the Need-slice verbs + `publish` + `RECIPE` + shared `receipt_state()`),
`claude/agents/challenger.md` (the one adaptable attacker), `claude/workflow/rulebook.md`,
`claude/workflow/conductor.md`. They reach the **isolated test project** by a **per-iteration** repo→
test-project copy — a *third* propagation direction `sync.py` doesn't cover (extending it is M6). Because
the operator propagates by tool and never manual-diffs, a **report-only byte-compare drift guard** (modeled
on `sync.py status`, harness tooling only) flags a stale copy before each test run. Live `~/.claude` is
never touched; **no workflow hooks** in M3 (nudge/skip-warner are M5).

**Deferred from the Need slice:** publish-half enrichment, the four remaining review-style rows, Step 4's
built-in-tool team, the research helper, forcing the cold read (α-2) → **M4**; the ambient surface (status
line, nudge, skip-warner) → **M5**.

**Built (2026-07-14).** The structure above is implemented (`claude/workflow/workflow.py` + `rulebook.md`
+ `conductor.md`, `claude/agents/challenger.md`) and proven end to end — see DECISIONS (2026-07-14). Two
build-time refinements from the Step-4 red-team, both faithful to the settled contracts: (a) the step draft
lives at `docs/draft-<step>.md`, not `docs/<step>.md` — a bare `docs/architecture.md` collides with the real
`ARCHITECTURE.md` on a case-insensitive filesystem, so every review-style step's draft is collision-proof
(keeps proof #4 honest); (b) `publish` and all doc I/O use **raw bytes** to preserve a doc's exact newlines
(and to avoid `read_text(newline=)`, which is Python 3.13+ while the developer runs 3.12). Harness tooling:
`tools/wf_drift_guard.py` byte-compares the repo→test-project copy before each run. Residual
real-system/M4/M5 tripwires are logged in RISKS #10–12.

### M4 — completing the step set: the publish engine (Architecture settled 2026-07-14; building at Step 4)

> M4 adds the four remaining review-style rows and generalizes the M3 publish half from "one
> single-writer-prose slice" into a data-driven engine that writes the real doc **shapes**. Need + Design +
> Architecture settled **by hand** (dogfooded — the Need step ran on the real machinery). Full rationale + the
> five Design decisions + six Architecture decisions are in `DECISIONS` (2026-07-14).

**One sentinel engine, parameterized.** The old single-mode `cmd_publish` body is retired in favour of one
core `_place_block(doc, block_key, scope, anchor_slug, placement, body)`:
- **Both-ends-identity markers** `<!-- WF:<key>:<scope>:start -->` … `:end` — the identity `(key,scope)` is on
  **both** ends (the M3 start-only format let a second task clobber the first — RISKS #12 key-half). A publish
  matches only *its own* `(key,scope)` pair: `0/0` → insert, `1/1` → replace-in-place, else → fail-closed.
  Other scopes are invisible, so blocks **accumulate**.
- **Two insert strategies** (the only branch): `prepend` for **log-accumulate** targets (DECISIONS, OVERVIEW
  status — newest-first; `scope = task_id`) and `append_section` for **sectioned** targets (ARCHITECTURE —
  after the last managed block under the anchor, **stable order**; `scope = section-slug`).
- **Seeded per-location anchors** `<!-- WF:anchor:<slug> -->` (not fragile prose headings; DECISIONS has no
  `##` heading), shared across keys so Need + Judgment interleave under one OVERVIEW anchor; `findall`+count
  == 1 or fail-closed.

**The RECIPE publish half** grows to `{mode, doc_target, block_key, anchor_slug}` (`mode` ∈ log | section;
the architecture step's `block_key` is `arch`). Section writes take `--section <slug>` + explicit
`--new`/`--update` intent (fail-closed on count mismatch; a typo to a *different existing* slug is the one
accepted, human-diff-gated residual → RISKS). **Both halves of RISKS #12** close here: the fence carve-out
*and* a **key-agnostic** entry guard (reject any column-0 WF marker line in a drafted entry).

**Shipping is a second publish-exception** (alongside Implementation): it has a challenge row but **no publish
half** — there is no valid auto-target (`claude/CHANGELOG.md` is hook-parsed semver; RISKS/PLAYBOOK are
curated). Its docs + the commit stay human. **Proof #4** is amended accordingly: the three publishing steps
prove through `publish`+`advance`; Shipping proves through `record` only.

**Building at Step 4:** retire the old publish body, add the four rows as data, one-time seed + retrofit the
real docs (wrap this `## Workflow machinery` body once as the first managed section), and migrate the tests
(~11 rewritten, #14 retired, mode tests added). Each block is red-teamed by the Step-4 team of attackers; each
row is dogfooded through the machinery (proof #4).

**Built + hardened at Step 4 (2026-07-15).** Implemented as above, plus three builder refinements the red-team
forced (all faithful to the settled contracts):
- **`publish` is gated.** It refuses unless the step is *current* AND holds a *fresh* receipt, so unvouched
  prose can never reach a committed doc — the honest floor, extended from `advance` to the publish verb.
- **The entry lifecycle guarantees a freshly-drafted entry per publish.** `record` clears any leftover
  `.workflow/publish-entry.md` *before* it writes the receipt, and `publish` consumes the entry *before* it
  writes the doc — both fail-closed. So a stale entry from a prior round, or one section's entry re-used for
  another, can never publish (RISKS #13 for the inherent residual — a fresh-but-divergent entry).
- **The challenge lifecycle guarantees a clean bundle per round** (added at Step 5, from the live smoke-test).
  `prepare` clears the previous round's `.workflow/challenge.md` *before* planting the new bundle, fail-closed,
  and *after* every validation check (so a refused `prepare` never destroys the prior result). The challenger is
  told to **write** that path, so whatever sits there is context it reads: leaving it made two live challengers
  echo the prior round's findings back as "corroboration". A stale result could never earn a receipt (the canary
  check rejects it), so this protects the challenger's **independence**, not the receipt — the same
  leftover-file species as the entry clear, one file over.
- **The fence guard is a CommonMark state machine.** `_wf_marker_in_fence` tracks the opening delimiter's
  character and length, honours the backtick-info-string rule, and normalizes all line endings (LF/CRLF/bare
  CR); it refuses any publish with a column-0 `WF:` marker inside a ` ``` `/`~~~`/indented fence. Its fence
  rules were **cross-validated against the CommonMark reference parser by the Step-4 red-team (round 4)** — the
  committed tests themselves are stdlib-only, hand-written to the spec's fence rules (no reference-parser
  dependency ships). This delivers the RISKS #12 "cheap fail-closed guard"; safe *placement* around fenced
  markers stays deferred.

Proven by **124 checks on Python 3.12.7** (5 suites), including a committed read-only test
(`tests/workflow/test_seed_docs.py`) that simulates a publish against the *actual committed* docs and asserts
byte-identity — the real docs are valid publish targets, unmutated. The red-team — the Step-4 team plus four
convergence rounds — found and fixed **eleven blocking defects** (see DECISIONS 2026-07-15); residual risks in
RISKS #10/#11/#13/#14/#15.

**Live-challenger smoke-test passed at Step 5 (2026-07-15) — the owed item, discharged.** The suite's row tests
exercise the deterministic chain with a *scripted* challenger; the M2→M3 pattern owed a **live** run. All four
new rows were then walked with **real spawned Sonnet challengers** against sandbox copies of the real docs:
4/4 echoed a fresh canary verbatim, every publish was byte-surgical, twelve refusals fired, and the three
publishing rows advanced through the gate without `--force`. It found **two things the deterministic suite
structurally could not** — a scripted challenger does only what it is told, a live one reads its whole
environment: the stale-`challenge.md` contamination (**fixed**, above) and RISKS **#15** (later steps challenge
a record that lacks every earlier correction — **not** a code bug; deferred to M5).

<!-- WF:arch:workflow-machinery:end -->
