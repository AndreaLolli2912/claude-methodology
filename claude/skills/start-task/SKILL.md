---
name: start-task
description: Manually start the six-step adversarial workflow on a task — scaffold any missing standard docs, run the workflow bootstrap, and begin the Need step. Human-owned; invoke only via /start-task, never automatically.
argument-hint: "<what you want to build or change>"
version: 0.1.0
disable-model-invocation: true
---

# Start Task — the workflow bootstrap

<!--
  WHY THIS EXISTS. Driving the six-step workflow by hand means typing
  `python ~/.claude/workflow/workflow.py start "<title>"` — a long path, and `~` doesn't expand
  in PowerShell/cmd. This skill is the friendly front door: the human types `/start-task "<goal>"`
  and Claude runs the real path in its OWN shell, so the human never types it.

  WHY MANUAL-ONLY (disable-model-invocation). The methodology makes starting a task a conscious
  human act — the ONE typed `/` command the design allows (docs/WORKFLOW.md "Ground rules"). The
  rest of the flow is agent-driven via conductor.md; Claude must never start a task on its own.

  WHY PROMPT-DRIVEN, not a pre-executed !`command`. The bootstrap has to BRANCH — is this a git
  repo? are the docs there? is there existing code to survey? — and quote the goal safely for the
  shell. A fixed pre-baked shell line can't do any of that; Claude, reading the steps below, can.
  It also runs in Claude's Bash tool (POSIX on every OS), so this one file works on Windows,
  macOS, and Linux with no per-platform shell handling.
-->

The human wants to start a workflow task. Their goal:

> $ARGUMENTS

Drive the bootstrap below, keeping the human in the loop the whole way (methodology R1 —
disambiguate before building; R2 — decide nothing by assumption; R3 — ask in structured options).
The `$HOME`-rooted paths expand in your Bash tool; if `python` isn't found, use `python3`.

## 1. Preconditions (check before doing anything)
- **A goal.** If the quoted block above is empty (no argument was given), ask the human for a
  one-line description of what they want to build or change, and use their answer as the task
  title. Never invent the goal yourself.
- **A git repository.** The workflow roots a task at the repo root, so `workflow.py start` refuses
  outside one. Check with `git rev-parse --show-toplevel`. If that fails, tell the human this needs
  a git repo and offer to run `git init` here first — don't proceed until there is one.

## 2. Scaffold the standard docs if they're missing
The workflow's steps write their settled prose into `docs/OVERVIEW.md`, `docs/DECISIONS.md`, and
`docs/ARCHITECTURE.md` — so those must exist, and must carry the workflow's `WF:anchor:*` publish
comments, before the flow can fill them.

- Glob the repo root and `docs/` for the standard doc set.
- **If any are missing**, scaffold them with the **`init-project-docs`** skill — but in its
  *skeleton-only* mode: create the files with `TODO` placeholders and its seeded anchors, and do
  **NOT** run its up-front questioning. The workflow's Need step (below) does the real elicitation;
  don't interview the human twice. `init-project-docs` is create-only — it never overwrites an
  existing `README.md` or doc, so this is safe in a repo that already has some of them.
- **If the docs already exist**, leave their content as-is — but confirm `docs/OVERVIEW.md`,
  `docs/DECISIONS.md`, and `docs/ARCHITECTURE.md` each still carry their workflow anchor
  (`<!-- WF:anchor:current-status -->`, `<!-- WF:anchor:decisions-log -->`,
  `<!-- WF:anchor:architecture-sections -->`). If one is missing (an older, pre-anchor scaffold), add just
  that comment under its natural heading — OVERVIEW's status section, below the DECISIONS intro, the
  ARCHITECTURE components area — so the workflow's first `publish` isn't refused. Change nothing else.

## 3. Start the workflow
Run the human-owned bootstrap in your Bash tool, passing the goal as a single quoted title:

```
python "$HOME/.claude/workflow/workflow.py" start "<the goal from above>"
```

This creates `.workflow/marker.json` at the repo root and sets the current step to **Need**. Show
the human the script's confirmation (it prints the resolved repo root to stderr and the started step).

## 4. Begin the Need step — then hand off to the conductor
Read `~/.claude/workflow/conductor.md` and follow its per-step loop from here on (propose → prepare
→ spawn the `challenger` subagent → record → settle with the human → publish → advance). For **Need**
specifically:

- **Existing project (there is already code):** survey what's there FIRST — read the key files, map
  what actually matters — then draft the real need on top of that survey into `.workflow/draft-need.md`.
- **Brand-new project (empty repo):** draft the need straight from the human's goal into
  `.workflow/draft-need.md`.

Then run the challenge loop as the conductor directs, disambiguating the need across multiple rounds
(R1) and putting choices to the human as structured options (R3). Don't race ahead to Design — Need
settles first, and the human makes the call each round.

**After this, the flow is agent-driven — no more slash commands.** `/start-task` only lights the
machinery; the conductor carries it through all six steps. The human ends the task later with
`python "$HOME/.claude/workflow/workflow.py" reset`.

## Done, for this bootstrap
`.workflow/marker.json` exists at step `need`; the standard docs are present (with their
`WF:anchor:*` comments); and you've put the first-round Need in front of the human to react to.
