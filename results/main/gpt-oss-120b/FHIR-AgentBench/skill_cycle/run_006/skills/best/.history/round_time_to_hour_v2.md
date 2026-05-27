---
description: Round any datetime answer to the nearest hour before responding
name: round_time_to_hour
provenance:
  baseline_fixes: 3
  baseline_regressions: 2
  epoch: 2
  failure_mode: answer_time_not_rounded_to_hour
  fixes: 4
  parent_version: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 0814561e80d18ee7b5e8e214
  - 098b1301820b7d581a339d0f
  update_cycle: 0
tags: []
version: 2
---

## When to use
Trigger this skill whenever the question asks for a specific date‑time value (e.g., "when was …", "last time …", "first prescribed …") and the agent is about to output an ISO‑8601 datetime string.

## Procedure
1. **Detect datetime answer** – If the provisional answer matches the ISO‑8601 pattern (`YYYY-MM-DDTHH:MM:SS` possibly with timezone), treat it as a datetime that needs rounding.
2. **Parse** the string into a `datetime` object (ignore any timezone information; work in naive UTC).
3. **Round** to the nearest hour:
   - If minutes ≥ 30, add one hour.
   - Set minutes, seconds, and microseconds to zero.
4. **Re‑format** the rounded datetime back to ISO‑8601 (preserve the original timezone suffix if present, otherwise output naive ISO).
5. **Replace** the provisional answer with the rounded string.

## Checks
- Verify the provisional answer is a non‑empty string that matches the ISO‑8601 datetime regex.
- Ensure rounding does not change the date part unintentionally (e.g., 2023‑12‑31T23:45:00 rounds to 2024‑01‑01T00:00:00 – this is acceptable).
- Confirm the final answer still satisfies the expected answer format (a single ISO‑8601 datetime string).

## Avoid
- Rounding values that are not datetime strings (e.g., IDs, codes, free‑text answers).
- Changing the answer when the question explicitly requests the original minute/second precision.
- Adding or removing timezone information; keep the original suffix unchanged.
