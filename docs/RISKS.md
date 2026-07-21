# Risks — read before deploying or scaling

> Things that work now (small / single-user) but will bite under deployment or scale. Each:
> what it is, why it bites, current status, what to do.

| # | Risk | Severity | Status |
|---|---|---|---|
| 1 | **Duplicated file manifest.** The bundle-owned path list used to be copy-pasted across two scripts. | Medium | Resolved — one bundle definition in `sync.py` (a directory whitelist since M6) |
| 2 | **No cross-platform transport.** Old scripts were PowerShell-only; macOS/Linux couldn't install/capture. | Medium | Resolved & verified (Win + Linux) |
| 3 | **Silent divergence between repo and `~/.claude`.** Edit live, forget to `capture` → next `install` overwrites your live edits. | High in theory / Low in practice | Overwrite doesn't occur in the repo-only workflow; read-only `status` readout planned |
| 4 | **`sync.py install` overwrites the whole `~/.claude/CLAUDE.md`.** Unrelated personal instructions there are replaced (backed up, but not merged). | Medium | Documented in README |
| 5 | **Root `CLAUDE.md` is gitignored** → not synced; a fresh clone won't have it, and its content only exists on the machine that created it. | Low | Accepted (by design) |
| 6 | **Transport now requires Python 3.** A machine without Python can't install/capture. | Low | Accepted — user runs Python everywhere; stdlib-only |
| 7 | **Status line isn't auto-wired on a new machine.** `install` deploys `statusline.py`, but the `statusLine` block that points at it lives in the personal (un-bundled) `settings.json` and names this machine's Python path. | Low | Resolved — `sync.py enable-statusline` wires each machine's own interpreter |
| 8 | **`sync.py` copied file-by-file.** Deploying the workflow machinery means shipping whole `agents/`/`hooks/`/`workflow/` directories, which the per-file `MANIFEST` couldn't express. | Low | **Resolved (M6)** — `sync.py` walks a named directory whitelist (`BUNDLE_DIRS`); a file in a named dir ships automatically |
| 9 | **Workflow-machinery firing is model-mediated (~70–80%).** The deterministic + live layers are now proven; the residual is that the model *spawning the challenger* is a probabilistic act a hook cannot force. | Medium | Accepted/mitigated — live layer **proven** (smoke-test passed); a miss is made *visible*, not prevented |
| 10 | **`publish` newline handling assumes a consistent-newline doc.** A doc mixing LF and CRLF is homogenized to its dominant ending on write. | Low | Accepted; docs now pinned LF via `.gitattributes` (`*.md text eol=lf`); revisit other in-place docs at real-system |
| 11 | **`publish` has no compare-and-swap.** A concurrent external edit in the read→write window is lost; two concurrent mutating runs race on the atomic replace. | Low | Accepted for M3/M4 (sequential single-user CLI); an **M5 tripwire** once a hook can auto-fire `publish` |
| 12 | **Sentinel matching was code-fence-blind and key-specific.** A column-0 sentinel inside a fence could match; the entry-guard only rejected the current step's key. | Low | **Resolved at M4** — key-agnostic entry guard + fail-closed fence guard (```/`~~~`/indented fences); safe *placement* around fenced markers still deferred |
| 13 | **`publish` certifies the challenged DRAFT, not the ENTRY it writes.** The gate hashes `draft-<step>.md`; the published text comes from `publish-entry.md`, which is not tied to the receipt. | Low | **Mitigated at M4** — `record` clears any leftover entry (no stale prior-round entry can publish); a fresh-but-divergent entry is model-authored + human-reviewed (inherent residual) |
| 14 | **`--update` to a wrong-but-existing section slug replaces the wrong section.** A typo'd `--section` that matches a *different* real section passes the `existing == 1` count check. | Low | Accepted (human-diff-gated) — the operator reviews the diff before commit; no slug registry |
| 15 | **Later steps challenge a record that lacks every earlier correction.** `prior_settled` feeds challengers the *drafts*; challenge-forced corrections live only in the *entry*, and folding them back into a draft flips its receipt stale. | Medium | **Documented at M4**, **reproduced live at M5** (the gate held — see detail). Out of M5's scope; **re-homed to M7** (2026-07-15), whose theme is exactly this: the fidelity of what a challenger is shown |
| 16 | **The machinery cannot run against this repo's own docs in place** (self-hosting gap). `ROOT` is the script's folder, so a `publish` from `claude/workflow/` targets `claude/workflow/docs/`, not `docs/`. Every live proof ran in an external sandbox on *copies*. | Low | Documented at M4 (found by the Shipping challenger) — coverage is equivalent (see detail); a real in-place run needs M6 deployment |
| 17 | **Two writes surface a raw traceback instead of a clean refusal** — `cmd_prepare`'s bundle write and `_save_marker` (all verbs) are unguarded on `OSError`. | Low | Accepted at M4 — fails **loud**, not silent, so the honest floor holds; ugly under M5's hooks, revisit there |
| 18 | **The canary proves the bundle was *read*, not that it was *fresh*.** `prepare` bundles whatever bytes its sources happen to hold; nothing checks them against the real files, so a stale warm source reaches the challenger under a green canary. | Medium | **Found at M5** (live, inside the Need step's own harness) — the copy-drift instance closes with M5's rooting fix; the general property does not. **Re-homed to M7** |
| 19 | **`sync.py install` hot-swaps the live machinery under a running task.** Once M5 deploys one global copy (D-1), the machinery that *runs* a task is the last installed snapshot of the machinery being *edited* — and freshness is hash-based, so a `receipt_state` or `artifact_path` change landing between `prepare` and `record` silently changes what a green receipt means. | Medium | **Found at M5 Design** (2026-07-15), reasoned not yet observed. **Structural, not occasional** — M6/M7 edit `workflow.py` and run through this workflow in this repo, so "install while a marker is live" is the development loop. No mitigation by construction; `sync.py status` is a readout he must remember, and the habit that causes it (`edit, then install`) is the recorded one |
| 20 | **The marker/git walk-up has no HOME or depth bound.** `_walk_up_for_marker` and `_walk_up_for_git` climb toward the filesystem root; a `.workflow/marker.json` or `.git` in an *ancestor* of the cwd is taken as this project's. | Low | Accepted at M5 — harmless in practice (his projects are self-contained repos; HOME is not one); the deleted-cwd variant a reviewer raised isn't reproducible on Windows |
| 21 | **`_write_settings` is non-atomic and its `.bak` names are second-granular.** A crash mid-write can truncate `settings.json`; two writes in the same second share one `*.bak` name, so the earlier backup is overwritten. | Low | Accepted at M5 (pre-existing `enable-*` pattern) — recover from an earlier `.bak` or git; observed benign during the M5 reversibility demo |
| 22 | **No self-heal if `.workflow/.gitignore` is removed mid-task.** `start` writes the ignore rule once; if it is externally deleted, drafts under `.workflow/` become `git add`-able again. | Low | Accepted at M5 — single-user, visible in `git status` before any commit; `start` re-creates it on the next task |
| 23 | **Concurrent same-repo sessions can lose a nudge-state update → one duplicate nudge.** Two sessions racing on `.workflow/nudge-state.json` can clobber each other's quiet-hash. | Low | Accepted/self-healing at M5 — the next turn re-quiets; the message stays true, no correctness impact |
| 24 | **The deployed hooks don't advertise their own off-switch.** Asked to "turn off the flow," a context-free Claude hand-edits `~/.claude/settings.json` instead of running `sync.py disable-workflow all`. | Low | Accepted at M5 — *found in the live proof* (2026-07-16); contained by the permission prompt + `settings.json` backups; a discoverability nicety for M7 |
| 25 | **Interior churn ships silently.** The M6 coverage gate guards only the *top level* of `claude/`; everything inside a named dir ships by placement. A scratch / in-progress file left inside `claude/workflow/` (the most-edited tree) ships on the next `install`. | Low (M6) | Accepted — the conscious cost of "content by placement"; *visible* in install's per-file output (not silently dropped), just not *halted*. Sharpens at M7+ when the shipped `workflow/` is edited again |
| 26 | **A gitignored file inside a named dir ships.** M6 cut git from the ship-set derivation, so the walk doesn't consult `.gitignore` — a secret or local-only file dropped inside a named dir would deploy. | Low (personal use) | Accepted — own `~/.claude`, low blast radius, `claude/` is a curated mirror not scratch space; **the first thing the deferred sharing milestone must revisit**, where the blast radius grows |

## Detail

**#1 — Duplicated manifest (resolved).** Fixed by collapsing to one script: `sync.py` holds one
bundle definition (since M6, the `BUNDLE_DIRS`/`BUNDLE_ROOT_FILES` whitelist that both `install` and
`capture` walk), so there is nothing to keep in sync. Adding a file inside a named directory now needs
no edit at all.

**#2 — Cross-platform (resolved & verified).** Fixed by replacing the two PowerShell scripts
with one portable `sync.py` (Python 3, standard-library only). `Path.home()` handles the
per-OS home directory. Verified on both Windows and real Linux (Ubuntu):
`HOME=/tmp/x python3 sync.py install` resolved `$HOME`, created the nested `skills/…` path,
and deployed all 3 files.

**#3 — Divergence (reframed 2026-07-13).** Originally: edit `~/.claude` live, forget to `capture`,
and the next `install` silently overwrites those live edits (only an easily-missed `.bak` to
recover). In practice the sole developer **always edits in the repo and then installs — never edits
live files directly** — so this overwrite essentially never happens, and the real-world severity is
low. (If the workflow ever includes live edits again, the original High risk returns.) The benign gap
that *does* matter is the reverse: after pulling or editing the repo you may forget to `install`,
leaving the live `~/.claude` behind the repo. *Planned:* a **report-only `sync.py status`** that shows
where you stand across GitHub ↔ repo ↔ live, so nothing is silently out of step (see OVERVIEW and the
DECISIONS entry).

**#4 — Global CLAUDE.md overwrite.** If the machine keeps other content in
`~/.claude/CLAUDE.md`, install replaces it wholesale (backing it up first). *Fix:* split the
core into an imported file, or keep all personal instructions committed here.

**#5 — Gitignored root CLAUDE.md.** Chosen deliberately (avoid confusing it with the bundled
global core). The cost is it doesn't travel — recreate it per machine if wanted.

**#6 — Python dependency.** The transport is Python now, not native shell. Low risk: the user
runs Python on every machine and `sync.py` imports only the standard library, so no
`pip install` is ever needed. On a machine truly without Python, install Python 3 first.

**#7 — Status-line wiring doesn't travel.** `statusline.py` is bundled and moves with
`install`/`capture`, but what points Claude Code at it — the `statusLine` block in
`~/.claude/settings.json` — is not, because that file is personal and edited surgically (same
as the update hook). So a fresh machine gets the script but shows no status line until the block
is added, and the block hardcodes this box's interpreter (`…/anaconda3/python.exe`), which
differs per machine. *Fixed:* `sync.py enable-statusline` (and `disable-statusline`) writes the
`statusLine` block using `sys.executable`, mirroring `enable-hook`, so each machine wires its own
interpreter with one command. Run it once after `install` on a new box.

**#8 — Directory-copy for the machinery (resolved, M6).** `sync.py`'s old `MANIFEST` listed individual
files; the workflow machinery added whole `claude/agents/`, `claude/hooks/`, and `claude/workflow/`
trees. M6 replaced the per-file list with a **named directory whitelist walked from disk**
(`BUNDLE_DIRS` + `BUNDLE_ROOT_FILES`), so a file dropped into a named directory ships with no code
edit, and a coverage gate halts on a stray or reports a missing named entry. See DECISIONS/ARCHITECTURE
2026-07-17.

**#9 — Model-mediated firing (accepted, mitigated).** The deterministic parts
(detect the marker, show it, gate the advance, warn on skip) are ~100% reliable, but getting the model
to *spawn the challenger on its own* is a model decision (~70–80%; a hook cannot force it). Mitigation
is by design: the machinery makes a miss **visible and hand-recoverable** (no receipt → the step reads
"not done"), not impossible. **Update (2026-07-14): the live smoke-test passed** — the hooks and status
line fire in a real session, and it caught and fixed a nudge that was silently inert live (wrong output
format). So the deterministic *and* live layers are now proven; the only residual is the model's own
choice to spawn the challenger. A secondary observed limit: the skip-warner's confirmation *reason
text* doesn't surface in the dialog (a generic prompt) — an M3 refinement, logged not solved.

**#10 — publish newline homogenization (M3-safe).** `publish` detects a doc's dominant newline (`\r\n` if
any CRLF is present, else `\n`) and re-applies it to the whole file on write. A *consistently* LF or CRLF
doc round-trips byte-clean (proven both directions in `test_publish.py`); a *mixed* doc gets homogenized to
the dominant ending — a noisy whole-file diff, though never corruption (git recovers). The real
`OVERVIEW.md` is pure-LF, so this can't bite today. **Update (M4):** `.gitattributes` now pins `*.md text
eol=lf`, so committed docs are LF and stay LF through publish — the mixed case is now only reachable on a
locally-dirty doc. *Fix at real-system:* splice into the raw string without a global newline pass, or
normalize the doc deliberately.

**#11 — publish has no compare-and-swap (M5 tripwire).** `publish` reads the target once, splices, and
atomically replaces — with no mtime/hash check that the doc is unchanged since the read. In M3's sequential,
single-user CLI there is no concurrent writer, so the window is inert; the atomic write also guarantees the
target is never left torn. It graduates to a real risk at **M5**, when a hook could auto-fire `publish`
while an editor holds the doc open (a lost edit), or two invocations race on `os.replace` (the loser
raises — now cleaned up, but still surfaced). *Fix when M5 lands:* a hash compare-and-swap (refuse if the
doc changed since the read), or a lock.

**#12 — sentinel matching was code-fence-blind + key-specific (resolved at M4).** Two gaps in the M3 publish:
a column-0 sentinel line standing alone *inside a code fence* would be counted as a real block, and the
entry-guard only rejected the *current* step's key (an entry carrying another step's `WF:<other>:` line passed
through). Both are closed in M4: (1) the entry-guard is **key-agnostic** — `_entry_has_marker_line` refuses
*any* column-0 `WF:` marker line in a drafted entry; (2) a **fail-closed fence guard** (`_wf_marker_in_fence`)
refuses the entire publish if any column-0 `WF:` marker sits inside a ```` ``` ````, `~~~`, or 0–3-space-indented
code fence. (The ```` ``` ````-only first cut failed *open* on `~~~` and indented fences — caught by the M4
correctness red-team, CB2, and fixed.) What remains deferred is only the *harder* half: safely **placing**
content around a fenced marker instead of refusing — refusing is the correct, safe behavior until then. Real
docs have no such fences (grep-verified), so the guard is dormant; it exists so that a future fenced example
can never cause a silent mis-edit.

**#13 — publish certifies the DRAFT, not the ENTRY it writes (mitigated at M4).** The fresh-receipt gate proves
the challenger ran against `docs/draft-<step>.md` (the artifact) and that it is byte-unchanged — but the prose
`publish` actually writes comes from `.workflow/publish-entry.md` (the entry), a *separate* file the model
drafts at settle that is never hashed into the receipt. So a stale or divergent entry could publish under a
green receipt. The entry is *inherently* un-vouchable this way: it is a post-settle summary that does not exist
when the challenge runs and is not a copy of the draft, so it cannot be hash-compared to what was challenged.
*Mitigation (M4):* `record` deletes any leftover entry on success, so a stale entry from a *previous* round can
never publish under the next fresh receipt — the model must draft a fresh entry each settle. The residual — a
*fresh-but-divergent* entry — is a model-mediated act like spawning the challenger: the human reviews the entry
at settle, and it is accepted-and-documented, consistent with the honest floor's self-reported ceiling. **See
#15:** the live smoke-test showed this residual has a second-order effect the above understates — the
divergence does not just risk one publish, it silently propagates into every later step's challenge.

**#15 — later steps challenge a record that lacks every earlier correction (documented at M4).** Found by the
M4 live smoke-test and verified empirically, not by reasoning. Three facts combine:
1. `_resolve_sources`'s `prior_settled` token resolves to `docs/draft-<step>.md` — later challengers cold-read
   the **drafts**, never the published docs.
2. A correction that a challenge forces is folded in at settle, *after* `record`, and therefore lands in
   `.workflow/publish-entry.md` — which reaches the published doc but **not** the draft.
3. Folding the correction back into the draft flips that step's receipt `fresh → stale` (verified), so
   `publish` then refuses. The honest path is re-`prepare` + re-challenge the corrected draft; the flow never
   prompts for it, so the cheap path is entry-only.
The net effect: the draft and the published doc diverge permanently, and **every later step's challenger reviews
the pre-correction record**. Observed live — the Judgment challenger raised a blocking finding that the
Architecture "correction isn't written anywhere in the settled Architecture I was handed", which was exactly
right: it had been handed the draft. This is *not* a code bug. Resolving it means deciding what `prior_settled`
should feed (drafts as-is / the published blocks / force a re-challenge on any corrected draft), which reopens a
settled Design/Architecture decision — so it is recorded here and carried to **M5**, not patched inside M4's
Implementation step. Mitigating factor: the human reads every entry at settle and the drafts are preserved, so
the divergence is visible in the working tree rather than hidden.

**Update (M5 Need, 2026-07-15) — reproduced live, and the gate held.** M5's own Need step walked into this from
the *other* side and confirmed the mechanism costs exactly what #15 predicts. Corrections forced by rounds 7 and
8 were folded back into `draft-need.md` — the honest path — which flipped the receipt `fresh → stale`, so
`publish` refused, so the draft had to be re-challenged. **Rounds 8 and 9 existed because the machinery demanded
them, not because anyone chose to run them.** That is the design working: the honest path is enforced, not
merely encouraged. The finding is the **cost asymmetry** it makes concrete — the honest path costs a full extra
round; the cheap path (fix only the entry) costs nothing and leaves no trace. That asymmetry **predates M5** (the
gate already refused a stale publish before any hook existed), so M5 does not create it — but M5's nudge does
tilt it slightly the **wrong** way: the nudge makes the honest path's owed round arrive *sooner and louder*,
while the cheap path stays exactly as invisible as it is today. A narrow tilt, and an argument for re-homing #15
to its own milestone **soon** rather than never. **M5 explicitly scopes #15 out**: it is about the *challenge
record*, not the *control layer*, and it landed on M5 by date rather than by subject.

**#14 — `--update` to a wrong-but-existing slug (human-diff-gated).** Section publishes require `--section
<slug>` plus explicit `--new`/`--update`, and the count guard fails closed on a mismatch (`--new` needs 0
existing, `--update` needs exactly 1). The one residual: a *typo* whose slug happens to match a *different*
real section passes the `existing == 1` check and replaces that wrong section. We accept this rather than
maintain a slug registry: the operator reviews the diff before committing (Shipping is human-gated), so a
wrong-section replace is caught by eye, not silently shipped.

**#16 — the self-hosting gap (documented at M4).** Raised by the M4 Shipping challenger and verified: `ROOT` is
the script's own folder, so running `python claude/workflow/workflow.py publish need` from this repo targets
`claude/workflow/docs/OVERVIEW.md` — a path that does not exist — not `docs/OVERVIEW.md`. This repo is the
*source* of the machinery, not a project that has it deployed, so **the machinery has never run its own CLI
against these real docs in place**. Two consequences worth stating plainly rather than leaving implied:
`tests/workflow/test_seed_docs.py` proves the real docs are valid targets by exercising the pure `_place_block`
engine (with its own path resolution), *not* `cmd_publish`; and the live smoke-test published into sandbox
**copies** of the real docs. *Why coverage is nonetheless equivalent:* the copies were byte-identical, and every
doc-specific behaviour in the publish path (anchor count, marker identity, fence detection, newline style) is
fully determined by those bytes — `cmd_publish` adds only the gate, the entry handling, and the newline restore,
all of which the 124-check suite exercises directly. A genuine in-place run becomes possible once M6 deploys the
machinery into a project (RISKS #8). Until then, "proven on the real docs" means *proven on their exact bytes*.

**#17 — two writes raise a raw traceback (accepted at M4).** `cmd_prepare`'s bundle write
(`CONTEXT.write_bytes`) and `_save_marker` (used by every verb) are not wrapped in the `try/except OSError ->
_fail()` that the rest of the script uses, so a locked or unwritable `.workflow/` surfaces a Python traceback
instead of a clean one-line refusal. Accepted for M4 on the principle that decides the whole design: this fails
**loud**, never silently green — no receipt is written, no doc is touched, so the honest floor is intact and the
failure is impossible to mistake for success. It is a polish issue, not a correctness one. Revisit at **M5**,
where a hook swallowing or mangling a traceback would make it genuinely confusing.

**#19 — `install` hot-swaps the machinery under a live task (found at M5 Design, 2026-07-15).** Before M5 this
was unreachable: the machinery could not run against a project in place, so there was no "live task" for an
install to land in the middle of. D-1 (one global copy in `~/.claude`, pointed at whichever project it serves)
makes it reachable, and the operator's recorded habit is what triggers it — *"I edit in the repo, then run
`python sync.py install`"* (`OPERATOR.md`). Two consequences: (1) `install` between `prepare` and `record`
swaps `workflow.py` while a receipt is pending, and freshness is **hash-based**, so a change to
`receipt_state` or `artifact_path` silently changes what a green receipt *means*; (2) the running machinery is
the last *installed* snapshot of the machinery being *edited*, and nothing in the status line, the nudge, or
the hooks reports drift between `claude/workflow/workflow.py` and `~/.claude/workflow/workflow.py`. **This is
structural, not occasional** — M6 and M7 both edit `workflow.py` and run through this workflow in this repo, so
"install while a marker is live" *is* the development loop. Related to but distinct from #16: that one says the
machinery cannot self-host; this one says self-hosting brings its own hazard. *Deliberately recorded without a
mitigation.* `sync.py status` (`sync.py:404`) reports repo-vs-live drift, but it is a **read-only readout he
must remember to run**, and RISKS #3 still calls it "planned" — so it mitigates by habit, not by construction,
and the habit that causes the swap is the one he actually has. M5's D-11 candidates (print `sync.py status` at
`enable-workflow` time; refuse `start` when live differs from the repo) cover the *edges*, never an `install`
run *during* a task. Revisit when M5's install lands and the loop is real.

**#18 — the canary proves the bundle was READ, not FRESH (found at M5).** The honest floor rests on the canary:
`prepare` plants a secret token in the challenge bundle and `record` refuses the challenge unless the challenger
echoes it back. That is a real guarantee, and it is **narrower than it looks** — it proves the challenger *read
the bundle it was handed*. It says nothing about whether that bundle reflected the current state of its sources,
because `prepare` bundles whatever bytes its warm sources happen to hold and never compares them against
anything. **Found live, inside M5's own Need step:** the sandbox's copy of `OPERATOR.md` was frozen at round 2,
so **every warm pass from round 3 to round 8 ran on stale operator context** — under a green canary, with nothing
anywhere reporting it. Confirmed by `diff` against the real file, and only noticed because a challenger flagged
that `OPERATOR.md` was silent on the exact habit the milestone turns on — the file had in fact been updated,
several rounds earlier, in a copy the harness never saw. This is a miniature of #15 (a record diverging from
what the challenger is shown) living one level down, inside the harness. **Two halves, and only one closes:**
the *copy-drift* half is an artifact of the sandbox shape (#16 — warm sources are copies because the script can
only see its own folder), and M5's rooting fix closes it by letting `prepare` read the real files in place. The
*general* half does not close — a source edited after `prepare` but before the challenge runs is still stale in
the bundle, and the canary will still be green. *Fix when it matters:* hash the warm sources into the receipt
alongside the artifact, so a bundle assembled from stale bytes reads `stale` the same way a corrected draft does.
Recorded rather than fixed at M5: it is not in the control layer's scope, and it belongs with #15's re-homing —
both are about the fidelity of what a challenger is shown.

**#20 — unbounded walk-up (accepted at M5).** The D-2 rooting refactor resolves a project by climbing from the
cwd until it finds `.workflow/marker.json` (`_walk_up_for_marker`, every verb but `start`) or `.git`
(`_walk_up_for_git`, `start` only), with no HOME boundary and no depth cap. If an *ancestor* of where you stand
holds either, it is taken as this project — a stray marker in `~` would capture every project beneath it. In
practice his projects are self-contained git repos and HOME is not one, so it does not bite; the deleted-cwd
variant a reviewer raised isn't reproducible on Windows. Bound it (stop at HOME, cap the depth) the day a
home-level marker is plausible.

**#21 — non-atomic settings write, second-granular backups (accepted at M5).** `enable-*`/`disable-*` read →
mutate → `write_text` the whole `settings.json` rather than writing a temp file and renaming, so a crash
mid-write can leave it truncated. And `_timestamped_backup` stamps to the second, so two writes inside one
second reuse the same `*.bak` name — the M5 reversibility demo did exactly this (`disable` then `enable` both
wrote `settings.json.20260716-160358.bak`, the second overwriting the first). Both are benign for a single
operator with git and per-write backups; revisit with an atomic replace if settings writes ever go concurrent or
programmatic.

**#22 — `.workflow/.gitignore` has no self-heal (accepted at M5).** `start` writes `.workflow/.gitignore`
(`*`) once, so a task's transient state (marker, drafts, nudge-state) stays untracked. If
that file is deleted mid-task those files become stageable again — but the gap shows in `git status` before any
commit, and the next `start` re-creates it. Single-user, low-stakes; recorded, not guarded.

**#23 — nudge-state lost-update → a duplicate nudge (accepted at M5).** The nudge quiets itself by hashing what
it would say into `.workflow/nudge-state.json` per session. Two sessions open on the *same* repo can
read-then-write that file concurrently and lose one update, so one re-emits a nudge it would otherwise have
suppressed. No correctness impact — the message is still true — and the next turn re-quiets. Recorded as
self-healing.

**#24 — the deploy doesn't advertise its off-switch (found in the M5 live proof, 2026-07-16).** During Part B,
asked to "turn off the flow," a fresh context-free Claude went to hand-edit `~/.claude/settings.json` (via an
`update-config` skill) rather than run `sync.py disable-workflow all`, and was interrupted. The running hooks
carry no pointer to their own clean removal, so an agent asked to disable them improvises on global settings —
risking a partial disable (a dropped `check_version`, malformed JSON). Contained today by the permission prompt
the edit must pass and the `settings.json` backups, but a real discoverability gap: a one-line "to turn this
off, run `sync.py disable-workflow all`" in the conductor slice or a `sync.py` hint would close it. **Re-deferred
past M7 (updated 2026-07-21):** M7's round-11 trim scoped the skip-warner / off-switch **out** (its mechanism
was found defective, not merely thin), so M7 did not close this; revisit at the next milestone touching the
deploy/control layer.

**#25 — interior churn ships silently (accepted at M6).** The directory-whitelist gate
(`_definition_problems`) classifies only the *top-level* entries under `claude/`; everything deeper is inside
a named dir, so it ships or is `IGNORE`d — by placement, ungated. That interior — `claude/workflow/`
especially — is the most-actively-edited part of the repo across M1–M7, so an in-progress or scratch file
left inside a named dir *will* ship on the next `install`. This is the conscious cost of "content by
placement" (Design A4/A5), taken for a milestone developed in-repo, live. Two honest qualifiers: the interior
is not *silent* — `install` prints every file it ships (per-file line + footer count), so a stray interior
file is *visible* in the output; what the top-level gate adds over that is a **halt**, not the only surfacing.
And a richer interior *report* stays open as a future option (it is a whitelist read — "show what is about to
ship" — not the rejected blacklist); only interior *gating* was ruled out. For M6 itself the exposure is low
(its churn is in `sync.py` at the repo root + the named root docs, so its scratch files land at the top level
and are caught as strays). The question sharpens at **M7+**, when the shipped `claude/workflow/` machinery is
edited again. **M7 did edit it** (`workflow.py`, `rulebook.md`, `challenger.md`), so M7 Shipping
(2026-07-21) honored this with a **walk-faithful pre-flight clean-check** — enumerate what the *install
walk* will ship from `claude/{skills,agents,hooks,workflow}/` and confirm it is exactly the intended
payload. `git status` is the *wrong* detector: a git-ignored editor/scratch artifact whose pattern is not
in `sync.py`'s `IGNORE` passes git clean and still ships (see #26).

**#26 — a gitignored file inside a named dir ships (accepted at M6, personal use).** M6's Design explored
deriving the ship set from `git ls-files` and **rejected** it (it needed a git checkout, broke the
edit→`install`-to-test loop for brand-new untracked files, and coupled coverage to git). The filesystem walk
that replaced it does not consult `.gitignore`, so a gitignored file placed *inside* a named directory — a
secret, a local-only note — would deploy. Accepted as low-harm **today**: the target is the operator's own
`~/.claude`, `claude/` is a curated mirror not a scratch space, and there is no public audience. It is flagged
as **the first thing the deferred sharing milestone must revisit** (Need §4 / A1), because the blast radius
changes the day the bundle is shared. See DECISIONS 2026-07-17 (M6 Design — the git-as-source rejection).

**#27 — R-1's added instruction is reassured, not proven (accepted at M7, 2026-07-21).** M7's honest
replacement for "the bundle is all you get" newly instructs the challenger to *use the injected methodology
core as the cold standard, but hold injected memory (habits, preferences, or facts) for the warm pass.*
That is the milestone's central behavioral claim, and its cold-discipline is supported only by a **fail-only**
probe: a rule-8 experiment (n=3, faithful runtime injection, cold-pass physically enforced, exercising this
repo's real leak-path fact) did not fire, but a pass is *expected regardless* (challengers held discipline
even under the old false text, 16/16) — so it can disconfirm, never confirm. The evidence is also a **proxy
agent** (not the shipped `challenger.md`) and **cold-arm only**: direction (b), "use the core as the
standard," is untested, and its worst case — the injected, pinned core being a *prior version of the very
document under change* (a live edge in this methodology repo, #28) — is trusted to the challenger's
judgement, not mechanized. Consciously accepted (the honest position: strictly more honest than the deleted
lie, still instructs hold-out, erosion not expected — *asserted, not measured*). The milestone's thinnest T2 corner.

**#28 — the honest block's standard is a runtime-injection dependency, two faces (accepted at M7).** The
canonical block is **presence-guarded** — it asserts nothing about what the runtime injects, so no clause
goes *false* if injection stops (only "to the extent you carry the core" becomes a vacuous conditional). But
the standard it names is **variable**: because the clause is conditional on what a challenger *carries*,
different runtimes/versions judge the same proposal against different amounts of injected methodology core.
Accepted: a varying-but-honest standard beats the fixed-but-false "the bundle is all you get."

**#29 — Axis-1 completeness is a bounded, single-party semantic review (accepted at M7).** The absence tests
guard four *known* deleted strings + the A2 seam; a *novel* over-claim in the block's connective middle (the
class the milestone re-introduced 3+ times, always in new words) is caught only by the bounded closed-set
review + the manual seam eyeball + the challenger loop (which reached 4 rounds at Judgment). No complete
automated guard exists — a full one would be the forbidden open blacklist. Bounded, not closed.

**#30 — the honest text's only live check is post-deploy and covers one repo (accepted at M7).** The
"live-after-close" probe (first post-`reset` task: `prepare`/`record` behave with no `context_hash`, the
`global_habits` retire holds, and a fresh-session decoy re-probe) runs *after* `install` deploys the changed
`challenger.md` to **every** repo, and only in *this* repo. Cross-repo exposure is unobserved and — the
operator works 2–3 repos/day — **imminent, not theoretical**, though his current near-exclusive focus here
is an informal detect-before-spread window. **Method finding (2026-07-21):** editing `MEMORY.md` mid-session
does **not** reach spawned subagents (they receive the session-start snapshot), so a live decoy re-probe of a
*new* fact needs a fresh session. No pre-ship close is possible (we cannot probe future runtimes).

**#31 — the wrong-copy warning (R-4) is deferred (trimmed at M7 round 11).** A task driven by a non-deployed
`workflow.py` copy is unwarned; `_print_root` surfaces a wrong *root* (the usual cwd-drift symptom) but not a
wrong *copy* with the right root. The proposed start-copy proxy missed the common case and could not be
dogfooded; deferred as a defective mechanism, hazard recorded. Revisit on a witnessed copy-mismatch or a
non-nagging deployed-location design.

**#32 — warm-source drift detection (R-2's dropped half) is deferred (trimmed at M7 round 11).** `record`
re-hashes the artifact and refuses a change; a warm source gets no equivalent. The only design so far fires
on the common **edit-then-record** order (alarm fatigue → self-defeating) and triggers outside the observed
workflow. Revisit with a witnessed incidental-race need and a response-edit-safe design.
