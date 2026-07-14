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

## Workflow machinery (designed 2026-07-14 — M2; not built yet)

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
- **Region-hashing inside shared logs.** The spike gives each step its *own* file, so "the
  artifact" is one cleanly-hashable thing. The real docs are in-place living files
  (OVERVIEW/ARCHITECTURE) and prepend/append logs (DECISIONS/RISKS); whole-file hashing is fine
  for an in-place doc but breaks on a *shared* log written by several steps. So the spike's
  hash-gate result is valid only for **single-file** artifacts, and M3 must design region-anchoring.
- **Backward movement / regression.** `current_step` only advances, but the workflow's own rules
  (reopen on contradiction; a no-go at Judgment sends work back) need a way to step back. The spike
  will not exercise it — flagged as not-yet-covered, not pretended-handled.
- **Deploying whole `agents/`/`hooks/` directories.** `sync.py` copies file-by-file; shipping the
  machinery (M6) needs a directory-copy change. To be logged in `RISKS` at Shipping (M6); not
  an M2 problem.
