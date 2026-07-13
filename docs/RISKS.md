# Risks — read before deploying or scaling

> Things that work now (small / single-user) but will bite under deployment or scale. Each:
> what it is, why it bites, current status, what to do.

| # | Risk | Severity | Status |
|---|---|---|---|
| 1 | **Duplicated file manifest.** The bundle-owned path list used to be copy-pasted across two scripts. | Medium | Resolved — single `MANIFEST` in `sync.py` |
| 2 | **No cross-platform transport.** Old scripts were PowerShell-only; macOS/Linux couldn't install/capture. | Medium | Resolved & verified (Win + Linux) |
| 3 | **Silent divergence between repo and `~/.claude`.** Edit live, forget to `capture` → next `install` overwrites your live edits. | High | Mitigated by `.bak` backups only |
| 4 | **`sync.py install` overwrites the whole `~/.claude/CLAUDE.md`.** Unrelated personal instructions there are replaced (backed up, but not merged). | Medium | Documented in README |
| 5 | **Root `CLAUDE.md` is gitignored** → not synced; a fresh clone won't have it, and its content only exists on the machine that created it. | Low | Accepted (by design) |
| 6 | **Transport now requires Python 3.** A machine without Python can't install/capture. | Low | Accepted — user runs Python everywhere; stdlib-only |
| 7 | **Status line isn't auto-wired on a new machine.** `install` deploys `statusline.py`, but the `statusLine` block that points at it lives in the personal (un-bundled) `settings.json` and names this machine's Python path. | Low | Resolved — `sync.py enable-statusline` wires each machine's own interpreter |

## Detail

**#1 — Duplicated manifest (resolved).** Fixed by collapsing to one script: `sync.py` holds a
single `MANIFEST` list that both `install` and `capture` read, so there is nothing to keep in
sync. Adding a bundled file is now a one-line change.

**#2 — Cross-platform (resolved & verified).** Fixed by replacing the two PowerShell scripts
with one portable `sync.py` (Python 3, standard-library only). `Path.home()` handles the
per-OS home directory. Verified on both Windows and real Linux (Ubuntu):
`HOME=/tmp/x python3 sync.py install` resolved `$HOME`, created the nested `skills/…` path,
and deployed all 3 files.

**#3 — Divergence.** There is no merge — only one-directional overwrite. The `.bak` files on
install are the only safety net, and they're easy to overlook. *Fix:* a `status`/diff check
that warns when live and repo differ before install; discipline to `capture` before `install`.

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
