#!/usr/bin/env python3
"""statusline.py — render Claude Code's status line: model | effort | context | quota.

Claude Code runs this on every status refresh, handing us the live session state as a JSON
blob on stdin and displaying our stdout (first line) under the prompt. We pull four facts out
of that blob and print one compact "key:value" line in a monochrome-green terminal palette:

    mdl:opus-4.8 eff:max ctx:8% 15.5k/200k 5h:34% @15:42
      model, effort, context (% used + tokens used / window size), 5h quota (% used + reset time)

Standard-library only (`json` + `datetime`), so it runs under any Python 3 with nothing to
install — the same zero-dependency rule the rest of this repo follows. Every field we read is
documented at https://code.claude.com/docs/en/statusline.md.
"""

# json parses the blob Claude Code sends; datetime turns the reset epoch into a clock time; sys
# gives us stdin/stdout. Nothing third-party, so nothing can be missing at runtime.
import json
import sys
from datetime import datetime

# --- Palette -----------------------------------------------------------------------------
# The status line renders raw ANSI escape codes, so colour is just a string we wrap values in.
# "Monochrome green": labels are dim green, values bright green — one hue, two weights — which
# reads as a classic terminal line. RESET after every span stops the colour bleeding onward.
RESET = "\033[0m"        # SGR reset — return the terminal to its default colour
KEY = "\033[2;32m"       # dim (2) + green (32) — the "key:" labels, deliberately quieter
VAL = "\033[32m"         # green (32) — the values, the part the eye should land on


def _pair(key, value):
    """Format one segment as a dim-green `key:` followed by a bright-green `value`.

    Every field routes through here so all segments look identical — change the look once and
    the whole line follows. Each span is individually reset so a later segment can't inherit an
    earlier one's colour.
    """
    return f"{KEY}{key}:{RESET}{VAL}{value}{RESET}"


def _k(n):
    """Abbreviate a token count to a short unit: 15500 -> "15.5k", 200000 -> "200k", 1e6 -> "1M".

    A status line has almost no room, so raw six-digit token counts would swamp the line. We show
    one decimal but drop a trailing ".0" (so 200000 reads "200k", not "200.0k") and fall back to
    the plain integer below 1000. `M` covers the 1,000,000-token extended-context window.
    """
    n = round(n)
    if n >= 1_000_000:
        s, unit = f"{n / 1_000_000:.1f}", "M"
    elif n >= 1_000:
        s, unit = f"{n / 1_000:.1f}", "k"
    else:
        return str(n)                     # under 1k: abbreviating adds no clarity
    # Trim a ".0" so round thousands read cleanly ("200k" not "200.0k"); keep real decimals.
    return (s[:-2] if s.endswith(".0") else s) + unit


def main():
    # Claude Code pipes the session JSON to us on stdin. If we're ever handed nothing or garbage
    # (e.g. a human runs the script directly), fall back to an empty dict instead of raising — a
    # status line that crashed would show nothing and noise up the session, so every field below
    # is written to degrade quietly rather than assume its data is present.
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}

    # Build the line segment-by-segment, then join with single spaces. A list lets us simply
    # *skip* an optional field, so an absent segment leaves no separator or empty "key:" behind.
    segments = []

    # model — the always-present identity field. `display_name` ("Opus 4.8") is lower-cased and
    # hyphenated into a compact, log-like token ("opus-4.8"). `or {}` guards a missing "model".
    model = (data.get("model") or {}).get("display_name") or "?"
    segments.append(_pair("mdl", model.lower().replace(" ", "-")))

    # effort — reasoning level (low/medium/high/xhigh/max). Claude Code includes it only when the
    # current model supports the effort knob, so it's optional: drop the segment when absent.
    effort = (data.get("effort") or {}).get("level")
    if effort:
        segments.append(_pair("eff", effort))

    # context — how full the window is, shown two ways: the pre-computed percentage AND the raw
    # token count against the window size ("8% 15.5k/200k"). `total_input_tokens` is the exact
    # number behind `used_percentage` (input + cache tokens, current usage — not output, not
    # cumulative) and `context_window_size` is the denominator (200k, or 1M extended). Any of the
    # three can be missing right after /compact or before the first API call, so we build only
    # the parts we actually have and fall back to "--" if we have none.
    cw = data.get("context_window") or {}
    pct = cw.get("used_percentage")
    used_tokens = cw.get("total_input_tokens")
    window = cw.get("context_window_size")
    ctx_parts = []
    if isinstance(pct, (int, float)):
        ctx_parts.append(f"{round(pct)}%")
    if isinstance(used_tokens, (int, float)):
        tokens = _k(used_tokens)
        if isinstance(window, (int, float)):        # only show "/total" when we know the window
            tokens += f"/{_k(window)}"
        ctx_parts.append(tokens)
    segments.append(_pair("ctx", " ".join(ctx_parts) if ctx_parts else "--"))

    # quota — the rolling 5-hour Max/Pro window, shown as percent used plus the wall-clock time it
    # resets ("34% @15:42"). `resets_at` is a Unix epoch in SECONDS; `datetime.fromtimestamp` with
    # no tz argument converts it to THIS machine's local time — which is what "when does my limit
    # reset" wants to read off the clock. We chose an absolute time over a relative countdown so it
    # never goes stale between refreshes (the line only re-runs per message, not on a timer). Both
    # parts are optional — a plain API key has no rate_limits — so assemble what's present and omit
    # the whole segment if nothing is.
    five_hour = (data.get("rate_limits") or {}).get("five_hour") or {}
    quota_parts = []
    used_pct = five_hour.get("used_percentage")
    if isinstance(used_pct, (int, float)):
        quota_parts.append(f"{round(used_pct)}%")
    resets_at = five_hour.get("resets_at")
    if isinstance(resets_at, (int, float)):
        try:
            # "@HH:MM" — the leading @ reads as "at <time>", setting it apart from the percent.
            quota_parts.append("@" + datetime.fromtimestamp(resets_at).strftime("%H:%M"))
        except (OSError, OverflowError, ValueError):
            pass                                    # an absurd epoch must not kill the line
    if quota_parts:
        segments.append(_pair("5h", " ".join(quota_parts)))

    # Emit the finished line. Single spaces separate segments (the dim keys already mark each
    # boundary), and a trailing RESET is belt-and-braces. Only this first line is shown.
    sys.stdout.write(" ".join(segments) + RESET + "\n")


if __name__ == "__main__":
    main()
