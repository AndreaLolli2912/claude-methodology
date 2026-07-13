# Playbook — reusable build recipes

> Timeless, transferable recipes: how to build a similar thing again (distinct from the
> dated DECISIONS log). Grouped by topic. Reusable lessons only.

## Deploy dotfiles/config with a non-destructive, cross-platform sync script
**When you need this:** you keep config in a repo but it must live somewhere fixed on the
machine (`~/.claude`, `~/.config`, …), you want one command to deploy it on any box, and it
should work on Windows *and* macOS/Linux without installs.
**The path:**
1) Mirror the target layout inside the repo (here: `claude/` mirrors `~/.claude/`).
2) Write ONE script with `install`/`capture` subcommands, standard-library only. Python 3 is
   the portable, no-install choice — bash isn't native on Windows, PowerShell 7 isn't on Linux.
3) Keep a single manifest list in that script; resolve the repo side from
   `Path(__file__).parent` and the live side from `Path.home()`, so it's location- and
   OS-independent.
4) Before overwriting any existing target file, copy it to `*.<timestamp>.bak`.
5) `capture` is the reverse direction, so live edits round-trip back to the repo.
**Gotchas:** one script kills the two-script manifest-drift trap. One-directional overwrite is
not a merge — decide which side is authoritative and say so loudly. Force `*.py eol=lf` via
`.gitattributes` so a Windows-edited shebang still runs on Linux.
**How you know it worked:** on a fresh machine, one command deploys everything and the tool
picks it up (here: `/skills` lists the bundled skill; core rules take effect after restart).
Prove it first against a throwaway `HOME`/`USERPROFILE` (assert files land + a re-run backs up).
**Pointers:** `sync.py`, `README.md`, `.gitattributes` (2026-07).

## Scaffold project docs from a methodology skill
**When you need this:** every new repo should start with the same documentation spine.
**The path:**
1) One short disambiguation round first (what/stage/components/constraints) — fill docs with
   real content, not TODOs.
2) Detect existing files; never clobber — create only what's missing.
3) Seed `DECISIONS.md` with a dated "docs scaffolded" entry (methodology P1).
4) Report created vs. skipped.
**Gotchas:** don't overwrite an existing `README.md` or project `CLAUDE.md`; offer to append
instead. Keep the content/transport and code/docs boundaries visible in ARCHITECTURE.
**How you know it worked:** `docs/` holds the full set, each with a purpose header, and the
decision log's newest entry records the scaffold.
**Pointers:** `claude/skills/init-project-docs/SKILL.md`, `docs/` (2026-07).

## Report sync/drift state without lying about "which side is newer"
**When you need this:** you're building a "where do I stand?" / "is it in sync?" check between two
copies of files (a repo vs a deployed copy, local vs remote, two mirrors), and you're tempted to use
file modification time to decide which side is newer or which way to sync.
**The trap:** a file's mtime does **not** mean "when someone last edited this." Git rewrites
working-tree file times to the moment of the operation on every clone, checkout, and pull; and a plain
byte-copy (`shutil.copy2`, `cp -p`) *preserves* the source's mtime. So after an ordinary pull, an
untouched repo file can look *newer* than a genuinely-edited copy on the other side — and a naive
"newer side wins → overwrite the older" rule then destroys real work. (Proven here with a throwaway
probe: a fresh clone stamps files at clone time, and a pull that updates a file stamps it at pull time.)
**The path:**
1) Compare **content**, not timestamps — a byte compare (or hash) reliably tells you *that* two copies
   differ.
2) For *direction* ("which way should I sync?"), use a source that actually records intent: git itself
   (`git status` for uncommitted work; `git rev-list --left-right --count @{upstream}...HEAD` for
   ahead/behind). If no reliable signal exists, **report the difference and let the human decide** —
   never guess.
3) Keep the check **read-only** and make it **degrade honestly** — offline / no remote / not-a-git-copy
   must say so, never silently report "in sync."
**How you know it worked:** the check flags exactly the files that differ, only points a direction when
it truly knows, and writes nothing (assert that in a throwaway run).
**Pointers:** `sync.py` (`status` + `_git_status`/`_live_status`), `DECISIONS.md` 2026-07-13 (the
mtime experiment) (2026-07).
