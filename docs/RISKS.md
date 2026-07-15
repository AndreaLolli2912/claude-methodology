# Risks — read before deploying or scaling

> Things that work now (small / single-user) but will bite under deployment or scale. Each:
> what it is, why it bites, current status, what to do.

| # | Risk | Severity | Status |
|---|---|---|---|
| 1 | **Duplicated file manifest.** The bundle-owned path list used to be copy-pasted across two scripts. | Medium | Resolved — single `MANIFEST` in `sync.py` |
| 2 | **No cross-platform transport.** Old scripts were PowerShell-only; macOS/Linux couldn't install/capture. | Medium | Resolved & verified (Win + Linux) |
| 3 | **Silent divergence between repo and `~/.claude`.** Edit live, forget to `capture` → next `install` overwrites your live edits. | High in theory / Low in practice | Overwrite doesn't occur in the repo-only workflow; read-only `status` readout planned |
| 4 | **`sync.py install` overwrites the whole `~/.claude/CLAUDE.md`.** Unrelated personal instructions there are replaced (backed up, but not merged). | Medium | Documented in README |
| 5 | **Root `CLAUDE.md` is gitignored** → not synced; a fresh clone won't have it, and its content only exists on the machine that created it. | Low | Accepted (by design) |
| 6 | **Transport now requires Python 3.** A machine without Python can't install/capture. | Low | Accepted — user runs Python everywhere; stdlib-only |
| 7 | **Status line isn't auto-wired on a new machine.** `install` deploys `statusline.py`, but the `statusLine` block that points at it lives in the personal (un-bundled) `settings.json` and names this machine's Python path. | Low | Resolved — `sync.py enable-statusline` wires each machine's own interpreter |
| 8 | **`sync.py` copies file-by-file.** Deploying the workflow machinery (M6) means shipping whole `agents/`/`hooks/` directories, which the per-file `MANIFEST` can't express. | Low | Accepted — deferred to M6 |
| 9 | **Workflow-machinery firing is model-mediated (~70–80%).** The deterministic + live layers are now proven; the residual is that the model *spawning the challenger* is a probabilistic act a hook cannot force. | Medium | Accepted/mitigated — live layer **proven** (smoke-test passed); a miss is made *visible*, not prevented |
| 10 | **`publish` newline handling assumes a consistent-newline doc.** A doc mixing LF and CRLF is homogenized to its dominant ending on write. | Low | Accepted; docs now pinned LF via `.gitattributes` (`*.md text eol=lf`); revisit other in-place docs at real-system |
| 11 | **`publish` has no compare-and-swap.** A concurrent external edit in the read→write window is lost; two concurrent mutating runs race on the atomic replace. | Low | Accepted for M3/M4 (sequential single-user CLI); an **M5 tripwire** once a hook can auto-fire `publish` |
| 12 | **Sentinel matching was code-fence-blind and key-specific.** A column-0 sentinel inside a fence could match; the entry-guard only rejected the current step's key. | Low | **Resolved at M4** — key-agnostic entry guard + fail-closed fence guard (```/`~~~`/indented fences); safe *placement* around fenced markers still deferred |
| 13 | **`publish` certifies the challenged DRAFT, not the ENTRY it writes.** The gate hashes `draft-<step>.md`; the published text comes from `publish-entry.md`, which is not tied to the receipt. | Low | **Mitigated at M4** — `record` clears any leftover entry (no stale prior-round entry can publish); a fresh-but-divergent entry is model-authored + human-reviewed (inherent residual) |
| 14 | **`--update` to a wrong-but-existing section slug replaces the wrong section.** A typo'd `--section` that matches a *different* real section passes the `existing == 1` count check. | Low | Accepted (human-diff-gated) — the operator reviews the diff before commit; no slug registry |
| 15 | **Later steps challenge a record that lacks every earlier correction.** `prior_settled` feeds challengers the *drafts*; challenge-forced corrections live only in the *entry*, and folding them back into a draft flips its receipt stale. | Medium | **Documented at M4** (found by the live smoke-test, empirically verified); the resolution is a design choice — deferred to M5 |
| 16 | **The machinery cannot run against this repo's own docs in place** (self-hosting gap). `ROOT` is the script's folder, so a `publish` from `claude/workflow/` targets `claude/workflow/docs/`, not `docs/`. Every live proof ran in an external sandbox on *copies*. | Low | Documented at M4 (found by the Shipping challenger) — coverage is equivalent (see detail); a real in-place run needs M6 deployment |
| 17 | **Two writes surface a raw traceback instead of a clean refusal** — `cmd_prepare`'s bundle write and `_save_marker` (all verbs) are unguarded on `OSError`. | Low | Accepted at M4 — fails **loud**, not silent, so the honest floor holds; ugly under M5's hooks, revisit there |

## Detail

**#1 — Duplicated manifest (resolved).** Fixed by collapsing to one script: `sync.py` holds a
single `MANIFEST` list that both `install` and `capture` read, so there is nothing to keep in
sync. Adding a bundled file is now a one-line change.

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

**#8 — Directory-copy for the machinery (deferred).** `sync.py`'s `MANIFEST` lists individual files;
the workflow machinery (M6) adds whole `claude/agents/` and `claude/hooks/` trees. Shipping those needs
a small directory-copy capability in `sync.py`. Not an M2 problem — recorded so M6 handles it.

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
