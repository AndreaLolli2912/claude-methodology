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
