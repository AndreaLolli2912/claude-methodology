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
