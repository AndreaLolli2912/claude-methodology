#!/usr/bin/env python3
"""workflow.py - the spine of the six-step-workflow machinery (M3 walking skeleton: Need slice).

WHY this file exists: the whole design rests on one idea - a *deterministic script*, not the
model, is the single author of every "did this really happen?" signal. The model does the
probabilistic acts (spawn the challenger, draft the prose); this script does every act that
*verifies* one (write a receipt, gate the advance, compute fresh/stale, place the settled prose
between markers). That way the model can never quietly vouch for its own work: if it forgets a
step, the script simply has no receipt to show, and the gap is visible rather than papered over.

It is BOTH a command-line tool (verbs: start / prepare / record / advance / status / reset /
publish) AND an importable library (load_marker + receipt_state), so the status line and hooks
(M5) will read the *exact same* freshness logic instead of re-implementing it and drifting.

Scope (M3): the *Need slice* only - one RECIPE row ("need") and one publish target (OVERVIEW).
Adding the other four review-style steps is a new RECIPE row each (M4); Step 4 (Implementation)
is the exception - its team of attackers does not use this canary/receipt machinery (also M4).
Standard library only, ASCII source, to run on any of the developer's machines with zero installs.
"""

import sys
import os
import re
import json
import hashlib
import secrets
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Layout. Everything is anchored on THIS file's folder so the project can be
# moved or renamed without breaking (the same trick sync.py uses). In the
# deployed shape the script and its rulebook are COPIED INTO the project
# together, so the script's folder is also the project root: script-assets
# (rulebook.md) and project-state (.workflow/, docs/) share ROOT here. If M6
# ever splits the two, this block is the single place that changes.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
RULEBOOK = ROOT / "rulebook.md"       # the nine shared rules, bundled by `prepare` (Decision A-1)

WF = ROOT / ".workflow"               # runtime state dir (gitignored, ephemeral; created by `start`)
MARKER = WF / "marker.json"           # the one state file the whole system reads
CONTEXT = WF / "context.md"           # the bundle `prepare` hands the challenger
CHALLENGE = WF / "challenge.md"       # where the challenger writes its verdicts back
ENTRY = WF / "overview-entry.md"      # the model's drafted prose that `publish` places
#                                       (the "overview-" name is OVERVIEW-specific: this is the
#                                       publish-half v0, which does not yet generalize - see M4.)

# The six steps, in order. "Where are we?" is just an index into this list, held
# in the marker - NOT inferred from which docs are filled (those are full across
# tasks, so they cannot tell you the current step; the Need step settled this).
STEPS = ["need", "design", "architecture", "implementation", "judgment", "shipping"]


def artifact_path(step):
    """The file that IS this step's product - the draft under attack, hashed for freshness.
    Named `draft-<step>.md` (NOT `<step>.md`) on purpose: on a case-insensitive filesystem
    (Windows, default macOS) a bare `docs/architecture.md` collides with the real committed
    `docs/ARCHITECTURE.md` and would clobber it. The `draft-` prefix cannot collide with any
    canonical doc name, so every review-style step's draft is safe (keeps proof #4 honest)."""
    return ROOT / "docs" / ("draft-" + step + ".md")


# ---------------------------------------------------------------------------
# The per-step RECIPE - the ONE place in this script that is step-aware, so
# nothing else has to be. Two halves of very different reach (see ARCHITECTURE
# "M3 walking skeleton - the Need slice"):
#   * challenge-context half (cold_sources / warm_sources / attack_angles):
#     a FROZEN contract the five review-style steps reuse by adding a row;
#     consumed by `prepare`.
#   * publish half (publish: {...}): a v0 seeded on ONE single-writer-prose
#     slice (Need -> OVERVIEW); consumed by `publish`. It does NOT generalize
#     as-is - M4 must enrich it (region-anchoring, list targets, a code mode).
# M3 fills only the "need" row. Step 4 (Implementation) is BOTH halves' named
# exception -> M4.
#
# Source tokens (resolved by _resolve_sources) - the small vocabulary a recipe
# draws from, so adding a step is DATA, not new code (proof #4, replication):
#   "artifact"      -> this step's own draft (the thing under attack)
#   "prior_settled" -> the artifacts of every step before this one
#   "operator"      -> docs/OPERATOR.md (how this developer actually works)
#   "global_habits" -> the hand-filled global-habits slot (usually empty)
# ---------------------------------------------------------------------------
RECIPE = {
    "need": {
        # challenge-context half (cold read = the draft + the settled record; warm
        # adds the operator facts). Frozen shape the other review-style steps reuse.
        "cold_sources": ["artifact", "prior_settled"],
        "warm_sources": ["operator", "global_habits"],
        "attack_angles": [
            "What need is missing, or is true but was never said aloud?",
            "What must this explicitly NOT do?",
            "Who is the real user - and is that assumption right?",
            "What is assumed about the problem that might be false?",
        ],
        # publish half (v0): the settled Need prose lands in OVERVIEW, between the
        # WF:need sentinels, prepended under the "## Current status" heading. `mode`
        # is read (and enforced) by `publish`, so a future mis-moded row fails loud.
        "publish": {
            "mode": "prose_sentinel",
            "doc_target": "docs/OVERVIEW.md",
            "sentinel_key": "need",
            "anchor": "## Current status",
        },
    },
}


# ---------------------------------------------------------------------------
# Low-level helpers.
# ---------------------------------------------------------------------------
def sha256_bytes(path):
    """Hash a file's RAW BYTES, or return None if it cannot be read.

    Raw bytes on purpose: this repo fights Windows CRLF/LF translation via
    .gitattributes, and if `record` hashed text-mode while the status line hashed
    bytes (or vice versa) they would disagree and flash a false 'stale'. Hashing
    bytes on both sides makes them provably identical. None means 'cannot verify',
    and every caller treats it as fail-closed - never as an accidental match.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_if_present(path):
    """Return a file's text if it exists and has non-whitespace content, else ''.
    Lets `prepare` skip absent/empty context sources cleanly - an empty OPERATOR.md
    or an unfilled global-habits slot simply doesn't appear in the bundle. A decode
    error is treated as 'not present' rather than crashing the whole assembly."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    return text if text.strip() else ""


def load_marker():
    """Return the marker dict, or None if no task is open (machinery inert here)."""
    try:
        return json.loads(MARKER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _atomic_write_text(path, text):
    """Write text by temp-file-then-replace, so a crash mid-write can never leave a
    half-written file that later reads as corrupt (os.replace is atomic on Windows
    and POSIX). Used for the marker AND for `publish`, where a torn write would land
    in a real committed doc - the worst place to tear.

    Two deliberate choices: a UNIQUE temp name (not a fixed '<name>.tmp') so two
    writers can never share one temp file and adopt each other's bytes; and we write
    ENCODED BYTES (not write_text) so `text` lands VERBATIM - no LF<->CRLF translation -
    which lets `publish` preserve a doc's exact line endings instead of silently
    rewriting the whole file's newlines on Windows, and avoids write_text/read_text's
    version-specific newline= kwarg (read_text only gained it in 3.13; this runs on 3.12)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / (path.name + "." + secrets.token_hex(4) + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    try:
        os.replace(tmp, path)
    except OSError:
        # A failed replace (target locked, or a concurrent writer won the race) must not
        # leave our uniquely-named temp behind to accrete. Clean it up, then re-raise so the
        # failure stays visible rather than silently lost.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _save_marker(marker):
    """Persist the marker atomically (see _atomic_write_text)."""
    _atomic_write_text(MARKER, json.dumps(marker, indent=2))


def receipt_state(step, marker=None):
    """THE shared truth function - imported by the status line and the hooks (M5) so
    the fresh/stale/missing rule lives in exactly one place and can never drift.

    Returns one of:
      "missing" - no receipt for this step (challenge never recorded, or it failed
                  closed, or the step was force-advanced without a real challenge).
                  The honest "not done".
      "stale"   - a receipt exists but the artifact's bytes have changed since (or the
                  artifact became unreadable), so the green no longer reflects what is
                  on disk. ANY edit to the artifact flips fresh -> stale.
      "fresh"   - a receipt exists AND the live artifact still hashes to what was
                  recorded. Only this counts as "the challenge really ran against what
                  is on disk right now."
    """
    if marker is None:
        marker = load_marker()
    if not marker:
        return "missing"
    receipt = marker.get("receipts", {}).get(step)
    if not receipt:
        return "missing"
    if "artifact_hash" not in receipt:
        # A receipt with no artifact_hash is a conscious --force override on a step
        # that never had a real challenge. The honest state is "missing" (no challenge
        # happened), not "stale"; status shows "missing (overridden)".
        return "missing"
    current = sha256_bytes(artifact_path(step))
    if current is None:
        # Had a receipt, but the artifact is gone/unreadable now -> not trustworthy.
        return "stale"
    return "fresh" if current == receipt.get("artifact_hash") else "stale"


def _fail(msg):
    """Uniform fail-closed exit: say why on stderr, return non-zero. Every refusal in
    this script routes through here, so a failure is always visible and never silently
    swallowed - the honest floor depends on that."""
    sys.stderr.write("workflow: " + msg + "\n")
    return 1


def _resolve_sources(tokens, step):
    """Turn a recipe's source tokens into ordered (label, path) pairs. Kept tiny and
    data-driven so ADDING A STEP is a recipe row, never new code here (proof #4,
    replication-ready). An unknown token is a recipe bug, raised loudly rather than
    silently dropping context the challenger needs (a unit test asserts the raise)."""
    pairs = []
    for tok in tokens:
        if tok == "artifact":
            pairs.append(("the proposal under attack (step: {})".format(step), artifact_path(step)))
        elif tok == "prior_settled":
            # every step strictly BEFORE this one, in order (empty for the first step)
            for prior in STEPS[:STEPS.index(step)]:
                pairs.append(("settled record: {}".format(prior), artifact_path(prior)))
        elif tok == "operator":
            pairs.append(("operator context (how this developer actually works)", ROOT / "docs" / "OPERATOR.md"))
        elif tok == "global_habits":
            pairs.append(("global-habits slot (hand-filled; usually empty)", WF / "global-habits.md"))
        else:
            raise KeyError("unknown recipe source token: {!r}".format(tok))
    return pairs


def _append_sources(out, tokens, step):
    """Append each present source as a labelled section to the bundle list `out`.
    Returns True if it appended at least one section. Shared by the COLD and WARM
    assembly so the two are IDENTICAL by construction (a formatting change can't drift
    between them)."""
    added = False
    for label, path in _resolve_sources(tokens, step):
        text = _read_if_present(path)
        if text:
            added = True
            out.append("\n## {}\n\n".format(label))
            out.append(text if text.endswith("\n") else text + "\n")
    return added


# ---------------------------------------------------------------------------
# The verbs.
# ---------------------------------------------------------------------------
def cmd_start(args):
    """Human-owned bootstrap. Starting a task is a deliberate act; this is the only
    way the machinery comes alive. Refuses if a task is already open rather than
    silently clobbering an in-progress one (that clobber would be exactly the kind of
    invisible failure the whole design exists to prevent)."""
    if MARKER.exists():
        return _fail("a task is already open (run `reset` first). Refusing to clobber it.")
    marker = {
        "task_id": secrets.token_hex(4),   # short unique id for this task
        "task_title": args.title,
        "current_step": STEPS[0],          # every task starts at Need
        "receipts": {},                    # filled one step at a time by `record`
        "pending": None,                   # the in-flight challenge (set by `prepare`)
    }
    _save_marker(marker)
    print("started task '{}' [{}] at step: {}".format(
        marker["task_title"], marker["task_id"], marker["current_step"]))
    return 0


def cmd_prepare(args):
    """Assemble the challenger's context bundle from the step's RECIPE, plant a fresh
    secret canary in it, and record that a challenge is now pending.

    The bundle is the honest-floor mechanism made concrete. It bundles the shared
    rulebook as a framing header (Decision A-1), then delivers the context in the
    ordered COLD -> WARM shape the Design settled (alpha-1): the challenger reads and
    verdicts the COLD set first, echoing the canary, then reads WARM. This *surfaces*
    whether a genuine cold read happened; it does not *force* one (forcing is deferred
    to M4). The canary cannot prove an INDEPENDENT party read the bundle (the model can
    read the file too - the accepted permanent ceiling), but it DOES catch an honest
    mistake: a challenge run against the wrong or truncated bundle echoes the wrong
    token and gets rejected at `record`."""
    marker = load_marker()
    if not marker:
        return _fail("no task open (run `start` first).")
    step = args.step
    if step != marker["current_step"]:
        return _fail("current step is '{}', not '{}'.".format(marker["current_step"], step))
    recipe = RECIPE.get(step)
    if not recipe:
        return _fail("no recipe for step '{}' - M3 builds only the Need slice "
                     "(the other steps are M4).".format(step))

    # Fail-closed on a missing rulebook: A-1 was chosen precisely so the rules cannot
    # be silently absent from the one file the challenger reads. No rulebook, no bundle.
    rulebook = _read_if_present(RULEBOOK)
    if not rulebook:
        return _fail("rulebook not found or empty at {} - refusing to prepare a challenge "
                     "without the shared rules (Decision A-1). Nothing prepared.".format(RULEBOOK))

    # Fail-closed on a missing/empty proposal: challenging nothing is meaningless, and
    # (with the snapshot below) would otherwise let a later-written draft earn a receipt.
    if not _read_if_present(artifact_path(step)):
        return _fail("no proposal to challenge at {} - draft the '{}' step first. "
                     "Nothing prepared.".format(artifact_path(step), step))

    canary = "WF-CANARY-" + secrets.token_hex(8)   # fresh every prepare

    out = []
    # Decision A-1: bundle the shared rulebook as the FRAMING HEADER, so the nine rules
    # ride inside the one file the challenger provably reads (canary-adjacent), rather
    # than via a model-mediated path read that could silently miss.
    out.append(rulebook.rstrip() + "\n\n---\n\n")
    out.append("# Challenge for step: {}\n\n".format(step))
    # Two-pass instruction (rule 6 / Design alpha-1): honest ordered-visible delivery.
    out.append(
        "Work in two passes. Read the COLD section, write your COLD verdict, and echo the\n"
        "canary - all BEFORE you read the WARM section. Then read WARM and write your WARM\n"
        "verdict. Attack the proposal under these angles:\n")
    for angle in recipe["attack_angles"]:
        out.append("  - {}\n".format(angle))

    # COLD: the proposal + the settled record. The canary sits at the END of COLD, so
    # echoing it proves the cold section was read THROUGH to the end (a truncated read
    # loses it - the real honest-mistake failure mode).
    out.append("\n===== COLD (read + verdict + canary FIRST) =====\n")
    _append_sources(out, recipe["cold_sources"], step)
    out.append("\nCANARY (echo this token verbatim in your COLD verdict): {}\n".format(canary))

    # WARM: operator + global habits. Delivered in the same bundle (alpha-1) but ordered
    # after the cold canary and labelled "read only after the cold verdict".
    out.append("\n===== WARM (read only AFTER writing the cold verdict) =====\n")
    if not _append_sources(out, recipe["warm_sources"], step):
        out.append("\n(no warm context on file for this task)\n")

    bundle = "".join(out)
    WF.mkdir(exist_ok=True)
    # Write bytes so the file matches the string we hash below exactly (no newline
    # translation), consistent with _atomic_write_text.
    CONTEXT.write_bytes(bundle.encode("utf-8"))

    marker["pending"] = {
        "step": step,
        "canary": canary,
        "context_hash": hashlib.sha256(bundle.encode("utf-8")).hexdigest(),
        # Snapshot the artifact the challenger will actually see. `record` refuses if
        # the live artifact no longer matches this - closing the window where the draft
        # is edited AFTER the challenge but BEFORE record, which would otherwise mint a
        # "fresh" receipt for bytes nobody challenged.
        "artifact_hash": sha256_bytes(artifact_path(step)),
    }
    _save_marker(marker)
    print("prepared challenge for '{}': bundle -> {} (rulebook + canary planted)".format(step, CONTEXT))
    return 0


def cmd_record(args):
    """Read the challenger's written result, verify it echoed THIS prepare's canary,
    confirm the artifact is unchanged since prepare, and write the receipt. FAIL-CLOSED
    on every check: a missing result, a wrong/absent canary, an unreadable artifact, or
    an artifact that changed between prepare and record writes NO receipt and returns
    non-zero. This is load-bearing - the whole honest floor collapses if there is any
    path that writes a partial 'green'."""
    marker = load_marker()
    if not marker:
        return _fail("no task open (run `start` first).")
    step = args.step
    pending = marker.get("pending")
    if not pending or pending.get("step") != step:
        return _fail("no challenge is pending for '{}' (did you run `prepare`?).".format(step))
    if not CHALLENGE.exists():
        return _fail("no challenger result at {} - challenge did not run. No receipt written.".format(CHALLENGE))

    result_text = CHALLENGE.read_text(encoding="utf-8", errors="replace")
    if pending["canary"] not in result_text:
        # The result does not echo this bundle's token -> it did not consume the right
        # context (wrong/stale/truncated bundle, or no real challenge). Reject.
        return _fail("challenger result did not echo the current canary - wrong/stale context. "
                     "No receipt written.")

    artifact_hash = sha256_bytes(artifact_path(step))
    if artifact_hash is None:
        return _fail("artifact for '{}' is unreadable ({}). No receipt written.".format(step, artifact_path(step)))
    if artifact_hash != pending.get("artifact_hash"):
        # The draft changed between `prepare` and `record`: the challenge ran against
        # different bytes than are on disk now. Refuse rather than certify the wrong ones.
        return _fail("artifact for '{}' changed between prepare and record - the challenge ran on "
                     "different bytes. Re-prepare and re-challenge. No receipt written.".format(step))

    marker.setdefault("receipts", {})[step] = {
        "challenge_ran": True,           # self-reported: "the model reports it ran" - never "verified"
        "context_hash": pending["context_hash"],
        "artifact_hash": artifact_hash,  # freshness is keyed to the artifact's live bytes
        "canary": pending["canary"],
    }
    marker["pending"] = None             # consume the pending challenge
    _save_marker(marker)
    print("recorded receipt for '{}' (challenge_ran, artifact hashed).".format(step))
    return 0


def cmd_advance(args):
    """The gate. By default refuse to leave the current step unless it has a FRESH
    receipt (challenge ran AND the artifact has not changed since). This catches a
    premature/accidental advance and a stale green.

    `--force` is the human's conscious override: it advances WITHOUT a fresh receipt and
    records that the human overrode, so the bypass is on the record, never silent. This
    reconciles "advance is gated" with "warn, never block - the human keeps the wheel",
    and gives a lighter path when a benign post-settle edit flips the hash."""
    marker = load_marker()
    if not marker:
        return _fail("no task open (run `start` first).")
    cur = marker["current_step"]
    idx = STEPS.index(cur)
    if idx == len(STEPS) - 1:
        return _fail("already at the last step ('{}'); nothing to advance to.".format(cur))

    state = receipt_state(cur, marker)
    overriding = state != "fresh" and args.force   # computed once so the record + the message agree
    if state != "fresh" and not args.force:
        return _fail("cannot advance: step '{}' is '{}', not 'fresh'. Run the challenge, or "
                     "`advance --force` to override consciously.".format(cur, state))

    if overriding:
        # Record the conscious override so it is visible in status/audit.
        marker.setdefault("receipts", {}).setdefault(cur, {})
        marker["receipts"][cur]["override"] = True
        marker["receipts"][cur]["override_state"] = state

    marker["current_step"] = STEPS[idx + 1]
    marker["pending"] = None  # a new step starts with no challenge pending
    _save_marker(marker)
    print("advanced: {} -> {}{}".format(cur, marker["current_step"], " (HUMAN OVERRIDE)" if overriding else ""))
    return 0


def cmd_publish(args):
    """Auto-docs writer (Decision D-1). The model drafts the settled-step prose into
    .workflow/overview-entry.md; THIS verb places it into the real doc between stable
    sentinels (Design beta-2), so the model owns the wording and the script owns the
    placement/replace. It is the ONLY verb that writes a committed doc, so it is
    FAIL-CLOSED: anything ambiguous refuses rather than risk corrupting a real document.

    Two paths: FIRST WRITE (no sentinel pair yet) prepends the block newest-first under
    the anchor heading; RE-SETTLE (one pair) replaces the content in place, so re-running
    is structurally idempotent (no duplicate block - proof #2)."""
    marker = load_marker()
    if not marker:
        return _fail("no task open (run `start` first).")
    step = args.step
    recipe = RECIPE.get(step)
    if not recipe or "publish" not in recipe:
        return _fail("no publish target for step '{}'.".format(step))
    pub = recipe["publish"]
    if pub.get("mode") != "prose_sentinel":
        # Only one mode exists in M3; a future differently-moded row must add its branch
        # rather than silently fall through to this one.
        return _fail("unsupported publish mode {!r} for step '{}'.".format(pub.get("mode"), step))

    # 1) The model's drafted entry must exist and be non-empty (fail-closed on input).
    try:
        entry = ENTRY.read_text(encoding="utf-8").strip() if ENTRY.exists() else ""
    except (OSError, UnicodeDecodeError):
        return _fail("drafted entry at {} is unreadable. Nothing published.".format(ENTRY))
    if not entry:
        return _fail("no drafted entry at {} (write the settled prose there first). "
                     "Nothing published.".format(ENTRY))
    entry = entry.replace("\r\n", "\n")   # normalize to LF; the doc's own style is re-applied on write

    # 2) The target doc must already exist - we place INTO a real scaffolded doc, never
    #    create one from nothing. Read preserving newlines, then work in LF space and
    #    restore the doc's original newline style on write (so a Windows publish can't
    #    silently flip the whole file LF<->CRLF).
    target = ROOT / pub["doc_target"]
    try:
        raw = target.read_bytes().decode("utf-8")   # bytes: preserve exact newlines on any Python 3
    except FileNotFoundError:
        return _fail("publish target {} does not exist. Nothing published.".format(target))
    except (OSError, UnicodeDecodeError):
        return _fail("publish target {} is unreadable. Nothing published.".format(target))
    doc_nl = "\r\n" if "\r\n" in raw else "\n"
    doc = raw.replace("\r\n", "\n")

    key = pub["sentinel_key"]
    task_id = marker.get("task_id", "unknown")
    # A sentinel is recognized ONLY as a standalone comment line AT COLUMN 0 - the exact
    # shape this verb itself writes (start_full/end_marker are spliced flush-left). That rules
    # out two false positives that would otherwise let publish overwrite the wrong thing:
    # an INLINE mention of the marker syntax mid-line (this project's docs quote it in
    # backticks) is ignored; and an INDENTED example of a marker (e.g. in a how-it-works
    # block) is ignored too - a real marker is never indented, so an example can't be mistaken
    # for the live block. (A column-0 sentinel-shaped line standing alone inside a ``` code
    # fence WOULD still match - a real-system caveat, not something a fresh init-project-docs
    # OVERVIEW contains.) `start_full` is what we WRITE; the patterns are what we SEARCH
    # (task-agnostic, so re-settle finds a block a prior task wrote).
    start_line = re.compile(r"(?m)^<!-- WF:" + re.escape(key) + r":start[^\n]*?-->[ \t]*$")
    end_line = re.compile(r"(?m)^<!-- WF:" + re.escape(key) + r":end -->[ \t]*$")
    # The anchor must be the WHOLE heading line (modulo trailing spaces), not a prefix, so a
    # heading like "## Current status archive" can't be mistaken for "## Current status" and
    # misplace the block. If the exact heading is absent, first-write fails closed (below).
    anchor_line = re.compile(r"(?m)^" + re.escape(pub["anchor"]) + r"[ \t]*$")
    start_full = '<!-- WF:{}:start task="{}" -->'.format(key, task_id)
    end_marker = "<!-- WF:{}:end -->".format(key)

    # The drafted prose must not itself contain a sentinel line, or it would inject a
    # second, bogus pair. Refuse rather than write malformed structure.
    if start_line.search(entry) or end_line.search(entry):
        return _fail("the drafted entry contains a sentinel line - refusing (it would corrupt the "
                     "marker structure). Remove the WF: marker lines from the entry.")

    starts = start_line.findall(doc)
    ends = end_line.findall(doc)

    # 3) Fail-closed on ANY malformed sentinel state - never guess into a real doc.
    if len(starts) != len(ends):
        return _fail("malformed sentinels in {}: {} start marker(s) vs {} end marker(s). "
                     "Refusing to write.".format(target, len(starts), len(ends)))
    if len(starts) > 1:
        return _fail("more than one WF:{} sentinel pair in {}. Refusing to write.".format(key, target))

    block = "{}\n{}\n{}".format(start_full, entry, end_marker)

    if len(starts) == 0:
        # First write: prepend the block newest-first, just under the anchor heading,
        # matching OVERVIEW's real prepend-log convention.
        m_anchor = anchor_line.search(doc)
        if not m_anchor:
            return _fail("anchor '{}' not found as a heading in {}. Refusing to guess a "
                         "location.".format(pub["anchor"], target))
        insert_at = m_anchor.end()                 # end of the anchor heading's line (before its newline)
        new_doc = doc[:insert_at] + "\n\n" + block + doc[insert_at:]
        how = "first write (prepended under '{}')".format(pub["anchor"])
    else:
        # Re-settle (exactly one pair): replace the whole block in place, keeping its
        # position. Guard against a reversed pair (both counts 1 but end before start)
        # before splicing, so we never corrupt the doc.
        m_start = start_line.search(doc)
        m_end = end_line.search(doc)
        if m_end.start() < m_start.start():
            return _fail("end marker precedes start marker for WF:{} in {}. "
                         "Refusing to write.".format(key, target))
        new_doc = doc[:m_start.start()] + block + doc[m_end.end():]
        how = "replaced in place"

    _atomic_write_text(target, new_doc.replace("\n", doc_nl))   # restore the doc's newline style
    print("published '{}' -> {} ({}).".format(step, target, how))
    return 0


def cmd_status(args):
    """Human-readable readout of the marker. (The status line - M5 - renders its own
    compact version by importing receipt_state; this verb is for the terminal.)"""
    marker = load_marker()
    if not marker:
        print("no task open (machinery inert here).")
        return 0
    print("task '{}' [{}]".format(marker["task_title"], marker["task_id"]))
    print("current step: {}".format(marker["current_step"]))
    cur_idx = STEPS.index(marker["current_step"])
    for i, step in enumerate(STEPS):
        if i > cur_idx:
            break
        state = receipt_state(step, marker)
        rec = marker.get("receipts", {}).get(step, {})
        tag = "  <- current" if step == marker["current_step"] else ""
        over = " (overridden)" if rec.get("override") else ""
        print("  {:14s} {}{}{}".format(step, state, over, tag))
    if marker.get("pending"):
        print("challenge pending for: {}".format(marker["pending"]["step"]))
    return 0


def cmd_reset(args):
    """End the task: remove all runtime state. The committed docs remain; only this
    task's live marker/bundle/challenge/entry go away, leaving the machinery inert.

    A file that is already gone is the intended, benign case; a file that EXISTS but
    cannot be deleted (e.g. locked by an editor or a OneDrive sync) is a real failure
    and is reported - never swallowed under a false 'cleared'."""
    failed = []
    for p in (MARKER, CONTEXT, CHALLENGE, ENTRY):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            failed.append("{} ({})".format(p.name, exc))
    if failed:
        return _fail("could not clear: " + "; ".join(failed) + ". Task state may persist - "
                     "close whatever is holding the file and retry.")
    print("reset: task state cleared.")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="workflow", description="Six-step workflow machinery (Need slice).")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="bootstrap a task (human-owned entry)")
    s.add_argument("title")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("prepare", help="assemble the challenger bundle (rulebook + cold/warm + canary)")
    s.add_argument("step", choices=STEPS)
    s.set_defaults(func=cmd_prepare)

    s = sub.add_parser("record", help="verify the challenger result and write the receipt")
    s.add_argument("step", choices=STEPS)
    s.set_defaults(func=cmd_record)

    s = sub.add_parser("advance", help="move to the next step (gated; --force to override)")
    s.add_argument("--force", action="store_true", help="advance without a fresh receipt (recorded)")
    s.set_defaults(func=cmd_advance)

    s = sub.add_parser("publish", help="place the settled prose into its doc between sentinels")
    s.add_argument("step", choices=STEPS)
    s.set_defaults(func=cmd_publish)

    s = sub.add_parser("status", help="print the current task state")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("reset", help="clear task state")
    s.set_defaults(func=cmd_reset)
    return p


def main(argv=None):
    # Make stdout/stderr tolerate non-ASCII task titles (e.g. an arrow in a title) on
    # Windows' legacy cp1252 console, so a print can never crash AFTER the state write and
    # leave "failed" and "succeeded" both looking true. Best-effort: if a stream can't be
    # reconfigured, the verbs' own literal text is ASCII anyway.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
