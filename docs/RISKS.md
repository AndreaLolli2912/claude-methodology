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
