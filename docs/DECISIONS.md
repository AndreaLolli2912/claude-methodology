# Decision Log

> Why things are the way they are. Add a dated entry whenever a task finishes or a plan is
> executed (newest first). Keep each entry short: what changed and why.

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
