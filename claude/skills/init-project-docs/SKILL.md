---
name: init-project-docs
description: Scaffold the standard project documentation set (OVERVIEW, DECISIONS, ARCHITECTURE, CONTRIBUTING, RISKS, PLAYBOOK, README) and wire the repo to the personal working methodology. Use when starting a new project, when the user asks to "set up docs", "scaffold docs", or "init project docs", or when a repo is missing the standard documentation files.
version: 0.3.0
tools: Read, Write, Edit, Glob
---

# Init Project Docs

Scaffold a project's standard documentation set, following the personal working
methodology's naming convention (`~/.claude/METHODOLOGY.md`). Each file is created with a
header stating its purpose and maintenance rule, plus a minimal skeleton for the user to
fill in.

The `OVERVIEW`, `DECISIONS`, and `ARCHITECTURE` skeletons also carry seeded
`<!-- WF:anchor:<slug> -->` comments — invisible when rendered — so the six-step adversarial
workflow's `publish` step can place its settled prose into them (that engine *refuses* a doc
that lacks the anchor, so a scaffold without them would block the workflow's first publish).
Leave them in place if you use the workflow; they're harmless if you don't.

## When to use
Starting a new project, or an existing repo lacks the standard docs. Safe to re-run: it
never overwrites an existing file — it only creates what's missing and reports the rest.

## Before scaffolding (methodology R1 — disambiguate first)
Question the user across **at least two rounds** (R1's floor for new work) before
scaffolding, the second round drilling into the first's answers, so the docs are filled
meaningfully. Pose them as **structured, concrete options** (methodology R3), one decision
per question, zero ambiguity — never vague prose. Round one covers the essentials:
- What is this project (one sentence), and who is it for?
- What stage is it at (idea / prototype / in production)?
- The main components or subsystems, if known.
- Hard constraints (platform, budget, offline, performance, deadlines).

Then drill into whatever those answers leave ambiguous. Stop when a full round changes
nothing. If the user says to proceed without answering, create the files with
clearly-marked `TODO` placeholders instead.

## Steps
1. **Detect.** Glob the repo root and `docs/` for existing standard files; list what's
   already present so nothing is clobbered.
2. **Create `docs/`** if it doesn't exist.
3. **Create each missing standard doc** using the header template + skeletons below. Never
   overwrite an existing file.
4. **`README.md`** at the root if missing (skeleton: name, one-line "what", quick start,
   link to `docs/`).
5. **Project `CLAUDE.md`** at the root: if absent, create the stub below; if present, do
   NOT overwrite — offer to append the doc map + methodology pointer instead.
6. **Seed `docs/DECISIONS.md`** with the first dated entry recording that the docs were
   scaffolded (methodology P1). Use today's date.
7. **Report** what was created vs. skipped.

## Header template (top of every doc)
```
# <Title>

> <One line: what this file is for.> <Maintenance rule: who updates it, when.>
```

## Skeletons

### docs/OVERVIEW.md
```
# Overview

> What we're building, why, the roadmap, and current status. Living document — update
> whenever direction or status changes.

## What it is
<one paragraph>

## Why (constraints)
<the key constraints and non-negotiables>

## Roadmap
| Stage | What | Status |
|------:|------|--------|
| 1 | <...> | TODO |

## Current status

<!-- WF:anchor:current-status -->

<date + where things stand>
```

### docs/DECISIONS.md
```
# Decision Log

> Why things are the way they are. Add a dated entry whenever a task finishes or a plan is
> executed (newest first). Keep each entry short: what changed and why.

<!-- WF:anchor:decisions-log -->

### <YYYY-MM-DD> — Project docs scaffolded
Standard documentation set created via the init-project-docs skill, following the personal
working methodology's naming convention.
```

### docs/ARCHITECTURE.md
```
# Architecture

> The components, the boundaries between them, the contracts, and the tech stack. Update
> when components are added/removed or the stack changes.

## Components

<!-- WF:anchor:architecture-sections -->

<what each part is; keep the data-moving layer separate from the logic — methodology P4>

## Contracts
<the stable interface(s) between components; which side owns conversion — methodology P5>

## Stack
| Technology | What it is | Why we use it |
|---|---|---|
```

### docs/CONTRIBUTING.md
```
# How to change this project

> A practical guide to changing each part safely. Update when the code structure changes.

## Mental model
<the pieces, in one list>

## The edit -> run -> see-it loop
<how to run it and watch the result>

## Common changes
<where to edit for the usual tasks>
```

### docs/RISKS.md
```
# Risks — read before deploying or scaling

> Things that work now (small / single-user) but will bite under deployment or scale. Each:
> what it is, why it bites, current status, what to do.

| # | Risk | Severity | Status |
|---|---|---|---|
```

### docs/PLAYBOOK.md
```
# Playbook — reusable build recipes

> Timeless, transferable recipes: how to build a similar thing again (distinct from the
> dated DECISIONS log). Grouped by topic. Reusable lessons only.

## Entry template
**When you need this:** <the trigger situation>
**The path:** 1) ... 2) ... 3) ...
**Gotchas:** <traps we hit, so they don't>
**How you know it worked:** <proof / metric / signal>
**Pointers:** <files, dates>
```

### Project CLAUDE.md stub (repo root)
```
# CLAUDE.md — project instructions

> Auto-loaded each session. Keep it short; detailed docs live in `docs/`.

This project follows the personal working methodology (`~/.claude/METHODOLOGY.md`):
Observe -> Orient -> Decide -> Act; disambiguate before building; decide nothing by
assumption; comment to teach; log decisions; keep docs in sync; prove it works.

## What this is
<one or two lines>

## How to run
<command>

## Docs map
`docs/OVERVIEW.md` · `docs/DECISIONS.md` · `docs/ARCHITECTURE.md` ·
`docs/CONTRIBUTING.md` · `docs/RISKS.md` · `docs/PLAYBOOK.md`
```

## After scaffolding
Tell the user which files were created and which were skipped (already present), and remind
them the docs start as skeletons to fill in.
