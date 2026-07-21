# Architecture

> The components, the boundaries between them, the contracts, and the tech stack. Update
> when components are added/removed or the stack changes.

## Components
Two layers, deliberately kept separate:

**Content (the bundle) — `claude/`.** The methodology itself, mirroring the layout of
`~/.claude`. The bundle is a **named whitelist** — four directories shipped wholesale plus six loose
root files — whose contents are walked from disk (so a file dropped into a named directory ships with
no code change):
- **Root files:** `claude/CLAUDE.md` (the always-on core), `claude/METHODOLOGY.md` (the full rule
  reference), `claude/VERSION` + `claude/CHANGELOG.md` (version + release history), and the two
  status-line renderers `claude/statusline.py` (model | effort | context | quota) and
  `claude/statusline_wf.py` (the same, plus a `wf:<step>:<state>` segment).
- **`claude/skills/`** — the `init-project-docs` docs-scaffolding skill.
- **`claude/hooks/`** — `check_version.py`, the SessionStart update-check hook.
- **`claude/workflow/` + `claude/agents/`** — the six-step adversarial workflow machinery (the
  `workflow.py` spine, the challenger's rulebook, the per-step conductor, the nudge hook, and the
  `challenger` agent). Its own architecture is the "Workflow machinery" section below.

**Transport (the script) — repo root.** Pure file-moving; it knows *nothing* about the
content's meaning, only which named directories + root files the bundle owns:
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
- **The bundle definition.** `sync.py` names what the bundle owns in three small constants —
  `BUNDLE_DIRS` (four directories shipped wholesale: `skills/ agents/ hooks/ workflow/`),
  `BUNDLE_ROOT_FILES` (six loose root files), and `IGNORE` (junk globs) — and *walks the filesystem*
  to turn them into the concrete file set. This is the contract between transport and content: a file
  dropped into a named directory ships automatically (no edit), and a coverage gate keeps it honest —
  a stray, un-named top-level entry under `claude/` **halts** install until it is classified, while a
  named entry missing from disk is **reported** and exits non-zero (the rest still ships). It replaced
  a per-file `MANIFEST` that couldn't express "everything in this directory" (see `RISKS.md` #8; the
  older two-script drift risk it also closed is #1).
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
- `receipts` — one per finished step; each holds `challenge_ran`, `artifact_hash` (the step's
  product), and `canary` (the secret token planted for the in-flight challenge, so a later
  `record` run — a *separate* process that shares nothing but this file — can check the echo).
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
  the settled docs) and a **WARM** section (`OPERATOR.md`). One
  bundle, cold+warm visible and ordered — honest *surfacing*, not *forcing*.
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

<!-- WF:arch:control-layer:start -->
## M5 — the control layer (Architecture settled 2026-07-16, six challenge rounds)

The ambient layer that makes the six-step machinery *fire on its own*: a status line, a
`UserPromptSubmit`/`SessionStart` nudge, and — the real milestone — the rooting fix that
lets any of it serve a project it does not live inside. Two ambient pieces, not the
Need's three (the skip-warner was dropped on measured evidence; re-homed to M7). Settled
against measured platform behaviour, not assumption: both probes the Design owed came back
answered (below), and the challenger ran six rounds (blocking 2→3→1→1→1→0).

### The two probes the Design owed — measured, not assumed
Ran in a throwaway project, touching nothing in live `~/.claude`. **Compaction:** a real
`/compact` fires `SessionStart` with `source=compact` and its `additionalContext` reaches
the post-compaction model — so the nudge surviving a compaction (D-7) rests on measured
behaviour, and the alternation matcher `startup|resume|clear|compact` works on this
non-tool event. **Merge vs replace:** project hooks *merge* with user hooks across every
scope (user via `CLAUDE_CONFIG_DIR`, project, local, CLI-arg), even at identical
event+matcher coordinates — so one global install cannot be silently disabled by a project
with its own hooks. `CLAUDE_CONFIG_DIR` is real but undocumented (present in the binary),
which is what let the user boundary be tested without touching the real config.

### The rooting split — one name was doing two jobs
`ROOT = Path(__file__).resolve().parent` becomes two: **`BUNDLE`** (the script + `rulebook.md`
+ `conductor.md`, correctly `__file__`-relative, they ship together) and **`PROJECT`** (the
`.workflow/` and docs, which `__file__` never should have located). Every `PROJECT` path
becomes a *function of a resolved root* — `wf_dir(root)`, `marker_path(root)`,
`draft_path(root, step)`, `gitignore_path(root)` — and readers
gain `root=None`. `root=None` resolves by the *marker* walk-up and exists **only** for a
human or model at a CLI; every programmatic caller (hooks and the test suite) passes a
resolved root explicitly, or it re-enters the defect. `start` alone resolves by the `.git`
walk-up (no marker exists yet); every verb prints the root it resolved **to STDERR** (ruled
2026-07-16 — test-clean, still visible), so a mis-rooted command is caught. The suite aims
the CLI two ways: in-process calls pass `root=r`; **subprocess CLI calls pass `cwd=TMP`** —
the only lever left after `--project` was rejected, and without it a subprocess `reset` from
the repo root would delete the live marker and its gitignored drafts.

### Three entry points, each rooted from its own source, each fail-safe
- **CLI** (`workflow.py` verbs): handed nothing, walks up; prints its root.
- **Status line** (`claude/statusline_wf.py`, beside `statusline.py` so `import statusline`
  is same-directory and can never fail): reads stdin once into `data`, calls the extracted
  `statusline.render(data)` for the base line **always**, then stats the marker inline
  (no import) — absent → base line unchanged; present → bridges `sys.path` to import
  `workflow.py` and appends `wf:<step>:<state>`; import failure → `wf:ERR` beside an intact
  base line. A broken `workflow.py` can never blank the base line (must-not #5, structural).
- **Nudge + conductor** (`claude/workflow/nudge.py`, beside `workflow.py`): stats the marker
  inline **before** importing (D-9(ii)); absent → silent (must-not #3). On the broken branch
  (import/read fails, sentinels missing) it fails **loud** to both audiences using stdlib
  only and calls **zero** `workflow.py` functions — the failed import is `workflow.py`, so
  any reach for its atomic writer would crash to a non-zero exit and the platform would
  discard the fail-loud JSON. All hash bookkeeping lives on the OK branch. The owed-line is
  gated on receipt state (`stale`/`missing` → "owes a challenge"; `fresh` → "ready to
  advance", never a false "owes"); the conductor rides along by sentinel
  (`_block_patterns("conductor","loop")`, reused). The output is a **whitelist** — exactly
  `systemMessage` (UserPromptSubmit) + `additionalContext`, any other key is a bug, exit
  always 0 — because three rounds of enumerating block routes each missed a live one.

### State and wiring
The nudge's quiet-hash keeps D-5's shape: `.workflow/nudge-state.json`, keyed by
`session_id`, atomic-written (never torn); the rare concurrent-session lost-update is a
recorded benign residual (one duplicate nudge), not engineered away. All task state lives
in a self-ignoring `.workflow/` (`start` writes its `.gitignore`: `*`),
so `git add -A` is safe in any repo by construction; `reset` clears the drafts and
`nudge-state.json` and spares `.gitignore`. `sync.py` ships six named files and gains
`enable-workflow`/`disable-workflow` (per-piece), writing only the user `~/.claude/settings.json`
(outside MANIFEST, so `install` never reverts it and `capture` never commits it). Two write
idioms, never mirrored — hooks *append* (a collection; `check_version.py` co-exists on
SessionStart), `statusLine` *assigns* (single value) — and `enable_statusline` itself changes
to preserve-the-script / rewrite-the-interpreter, or re-running it on a new box would silently
revert the `wf:` segment. Activation is per-machine by construction: `git pull; sync.py install`
carries the bundle but not the registration, so `enable-workflow` joins the recorded new-box
setup step.

### Owed before / recorded at settle
Two probes remain opportunistic-only: auto- (vs manual-) compaction and `systemMessage` on
SessionStart — the design leans on neither. The six corrections to the Need's own draft are
being **applied now** (ruled 2026-07-16), ahead of Implementation, so the challenge bundle
reads an accurate Need. New risks to RISKS.md: `install` hot-swaps `workflow.py` under a live
marker (structural in the M6/M7 self-hosting loop); concurrent hook processes corrupt a shared
*append* file (why the marker/receipts are never hook-authored). Deferred to M7: the skip-warner,
forcing the cold read (α-2), and built-in reviewers.
<!-- WF:arch:control-layer:end -->

<!-- WF:arch:directory-whitelist:start -->
## M6 — the directory-whitelist transport (Architecture settled 2026-07-17)

The rewrite of `sync.py`'s deploy path from a per-file `MANIFEST` (one hand-maintained
line per shipped file) to a **named whitelist walked from disk**. This section maps the
pieces of the new transport and the contracts between them; the *why* (git-as-source
explored and rejected, the fail-closed choice) is settled in `DECISIONS` (2026-07-17) —
here is the *structure*. It changes only the transport layer (`sync.py`); the bundle's
*content* and the whole workflow subsystem are untouched.

**The one principle that shapes everything below:** the bundle is defined by **name** (four
directories + six loose root files) but its **contents come from the filesystem**, not a
list — so a file dropped into a named directory ships with no code edit (this closes RISKS
#8, the per-file manifest's inability to express a directory). Two guards keep that honest:
no **un-named top-level** entry ships (a stray there **halts** install — "what ships" is
ambiguous until you classify it), and no **named** entry is silently dropped (a missing one
is **reported and exits non-zero**, though the covered files still deploy; a live-only file
is reported too). Files *inside* a named directory ship by placement — the gate guards the
curated top level, not the interior — so the transport never *silently* ships an un-named
top-level entry, nor *silently* drops a named one.

### The bundle definition — the single source of truth for "what ships"
Three module constants replace the ~14-line `MANIFEST`:
- **`BUNDLE_DIRS`** = `skills, agents, hooks, workflow` — shipped wholesale (walked).
- **`BUNDLE_ROOT_FILES`** = the six files that live in no directory (`CLAUDE.md`,
  `METHODOLOGY.md`, `VERSION`, `CHANGELOG.md`, `statusline.py`, `statusline_wf.py`).
- **`IGNORE`** = curated junk globs (`__pycache__`, `*.pyc`, `*.bak`, …).

Two helpers turn those names into a concrete file set, read from disk:
- **`_is_ignored(rel)`** — true if any path component is junk. Case-normalised (lowercase +
  `fnmatchcase`) so a file's ignore-status is **identical on Windows and macOS/Linux** —
  bare `fnmatch` case-folds per-OS, which would make the ship set platform-dependent.
- **`_bundle_files(base) -> (ship, skipped)`** — **the walker.**
  Given either root (`claude/` or the live `~/.claude`), it returns the shippable files
  (named root files that exist, then everything under each named dir) minus `IGNORE`
  (skipped junk is *counted*, so the report stays honest), in a deterministic order.
  It is the single source of the **ship set of record**: install, capture, and status all
  take their file list from it, so they cannot disagree on what the bundle *is*. The one
  place that also needs a *live-side* walk — the orphan check — should **reuse this same
  walker** (`_bundle_files(TARGET_DIR)`, then filter out the shared-namespace root files with
  a one-line predicate) rather than re-implement the `rglob` loop, so the walk mechanic and
  the "what-counts-as-owned" test each live in exactly one place. (Implementation owns that
  centralisation; the Design's separate-walk sketch is not binding on it.) "Ignore beats
  ship": junk **inside** a named dir is still skipped.

### The coverage gate — two disagreements, two responses
The price of walking from disk (instead of an explicit list) is that a *mistake* on disk
must be caught, not shipped. The gate runs **before install writes anything** — and because
the two kinds of disagreement get **different** responses, it must return them **separately**,
not as one flat list. The interface is therefore
`_definition_problems(base) -> (strays, missing)` — the stray (over-inclusion) entries and the
missing (under-inclusion) named entries as **two lists** — so install can branch on them.
(A single flat list consumed as "halt if non-empty" would collapse both kinds into a halt and
silently re-introduce halt-on-missing, the exact behavior the settled record overturned — the
RISKS #15 regression this step exists to close. Implementation may realise this as two lists
or two small predicates; the binding contract is only that the two kinds are *distinguishable*
at the call site.) The gate reads the same three constants the walker does, so the single
source of truth is those **constants**; `_bundle_files` is the single source of the ship-set
*value*. The two responses:
- **A stray (over-inclusion) halts install and deploys nothing** — fail-closed. A stray is a
  **top-level** entry under `claude/` that is neither a named dir, a named root file, nor
  junk (a `claude/notes.md`, an un-named `claude/prompts/`). It makes "what ships"
  *ambiguous*, so install stops and classifies it rather than guess. Safe because it is fully
  reversible (nothing was written) and the fix is one line (name it, move it into a named
  dir, or `IGNORE` it). Gaps are top-level-only by construction: everything deeper is inside
  a named dir, so it either ships or is `IGNORE`d.
- **A missing named entry (under-inclusion) does *not* halt** — a `BUNDLE_DIRS` /
  `BUNDLE_ROOT_FILES` name that is absent from disk is **reported**, install **ships the
  covered files anyway**, and the run **exits non-zero**. There is no ambiguity (a named
  thing is simply absent), the Need's floor is only a non-zero exit, and this keeps the
  response consistent with a file that vanishes at *copy* time (below): both report + count +
  non-zero, rather than nuke the whole deploy over one absent file.

**Envelope — be honest about what the gate does *not* cover.** It guards the **top level** of
`claude/` only; the *interior* of the named dirs ships by placement. And that interior —
`claude/workflow/` especially — is the **most-actively-edited part of the whole repo** (the
live machinery being built across M1–M7). So the guarded zone is the rarely-touched boundary
and the *unguarded* zone is the high-churn core: an in-progress or scratch file left inside a
named dir during development *will* ship on the next install. This is the accepted cost of
"content by placement" (Design A4/A5), consciously taken for a milestone developed in-repo,
live. Two honest qualifiers keep this from overselling either way: (1) the interior is not
*silent* — install prints every file it ships (per-file line + footer count), so a stray
interior file is **visible** in the output; what the top-level gate adds over that is a
**halt**, not the only surfacing. (2) Surfacing what ships is *not* the rejected blacklist —
"report what is about to ship" is a whitelist read, not "enumerate what doesn't belong" — so a
richer interior *report* stays open as a future option; only interior *gating* was ruled out.
For **M6 itself** the exposure is low: M6's churn is in `sync.py` (repo root, unshipped) and
the named root docs, so its scratch files land at the top level and are caught as strays. The
interior question sharpens at **M7+**, when the shipped `claude/workflow/` machinery is edited
again — recorded as a forward concern, not an M6 fix.

### The shared copier (`_copy`)
`_copy(src, dst, *, backup)` gains a **status return** — `"new"` / `"replaced"` /
`"missing"` (it was a bool) — so callers can print honest counts (N shipped, R replaced)
instead of guessing. It has exactly two call sites (install, capture). `"missing"` is
**handled, never green-washed**: the gate + walk make a missing *source* practically
unreachable, but a walked file can still vanish between the walk and the copy (a TOCTOU
race), so install warns, counts it, and exits non-zero rather than print "installed" for a
file it did not copy.

### The three verbs — each rooted, each fail-safe
- **`install` (repo → live).** Print the resolved `repo → target` roots **first** (the
  cwd-audit habit, even on the halt path) → run the coverage gate: **halt on a stray**
  (deploy nothing), otherwise report any missing named entry and carry on → walk the ship
  set → copy each (backing up what it replaces) → footer counts (shipped / replaced / junk
  skipped / vanished). Returns non-zero if a named entry was missing or a file vanished.
- **`capture` (live → repo).** Walk the **repo's** ship set (the authoritative owned set) →
  pull back each file that exists live → report live orphans as *information* but **never
  pull them**, so a repo-side deletion cannot resurrect itself into the source of truth.
  **Exits 0 even with orphans** — a lingering live file is news, not an error, so a routine
  `capture; commit; push` is never tripped by benign leftovers. (This ship-set walk is Design
  **F2**; it supersedes the Need's looser "pull back the whitelisted locations" phrasing — the
  two differ only on a repo-deleted-but-still-live file, which F2 correctly does *not*
  resurrect. Flagged for the **Judgment** step to formally correct the Need text — RISKS #15.)
- **`status` (read-only).** Keeps its existing GitHub↔repo half untouched; its repo↔live
  half now walks the same ship set and adds two advisories before the drift line — a
  **coverage problem** (actionable: "install will halt / report" — folds into the exit-1 it
  already returns for "something to do") and **live orphans** (informational — printed, but
  they do not by themselves flip the exit code, matching `capture`).

**Exit codes reach the shell for every verb:** `install`/`capture` now return `int` (as
`status` already did) and `main` propagates each code, so the everyday `python sync.py` is
loud on a real anomaly — a missing named entry, a vanished file — instead of exiting 0 with a
warning buried in a `Done.`. A live orphan is *not* such an anomaly: it stays exit 0.

### The orphan check (`_live_orphans`)
`_live_orphans(ship)` lists files under the **live** named dirs that the repo ship set does
not own — lingering or foreign. Reported by capture and status, never pulled. Two inherent
blind spots are documented, both low-harm on an additive target: a lingering **root** file
(the `~/.claude` root is a shared namespace — `settings.json`, `projects/`, other tools —
so we can't treat every unowned root file as an orphan) and a **wholly-retired directory**
(once un-named, its live leftovers are no longer walked). Both would need history we don't
keep.

Because an orphan is reported at **exit 0** (not a non-zero latch), a benign lingering file
never cries wolf — which is what lets the report stay generous. In practice orphans are rare
anyway: the one live process that persists state, the update-check hook, writes its cache to
the `~/.claude` **root** (`.methodology-update-check.json`, which this walk skips), and
nothing else lands in a live named dir except `__pycache__` (`IGNORE`d). So the orphan line
is a quiet informational nudge, not a gate.

### Boundaries — what M6 deliberately does not touch
- **No change to `workflow.py`, `settings.json`, or the activation model** → repo↔deployed
  drift stays zero, sidestepping RISKS #19 (an `install` hot-swapping the running
  `workflow.py`).
- **Additive only** — no delete/prune on the target; orphans are reported, never removed.
- **Plain-copy (non-git) install still works** — the walk needs no git, so a USB/OneDrive
  copy still deploys (only `update`'s `git pull` needs a checkout, as today).
- **The content/transport split holds** — this is all transport; `sync.py` still knows
  nothing about what the bundle *means*, only which named paths it owns.
- **Root resolution is unchanged and cwd-independent** — M6 rewrites *file selection*
  (`MANIFEST` → walk), **not** *root resolution*. `BUNDLE_DIR` / `TARGET_DIR` stay
  `Path(__file__)` / `Path.home()`-anchored, and every new walker resolves paths against
  those anchored roots, so a verb run from *any* working directory still resolves to this
  repo — the operator's first tacit failure mode (a stray `cd` poisoning a cwd-persistent
  Bash) cannot mis-target the walk. The one cwd-sensitive call, `_git -C REPO_ROOT`, is
  likewise anchored; and install/capture print the resolved roots first, so a mis-root is
  visible immediately.
- **Doc debt, flagged not hidden:** the hand-written `## Components` / `## Contracts` /
  `## Stack` prose at the top of this file still describes the retired `MANIFEST`. It is
  corrected in **Implementation**, the same turn `sync.py` changes (P2) — i.e. when the code
  actually makes it stale — not now, while the code it describes is still live.
<!-- WF:arch:directory-whitelist:end -->
