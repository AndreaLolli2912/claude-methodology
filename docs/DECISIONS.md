# Decision Log

> Why things are the way they are. Add a dated entry whenever a task finishes or a plan is
> executed (newest first). Keep each entry short: what changed and why.

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
