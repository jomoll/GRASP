---
description: "Round any datetime answer to the nearest hour for time\u2011related\
  \ queries"
name: round_time_to_hour
provenance:
  baseline_fixes: 1
  baseline_regressions: 2
  epoch: 3
  failure_mode: answer_time_not_rounded_to_hour
  fixes: 3
  parent_version: 2
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 017d9aef746962d1c3d9d52e
  - 024e5c4760ca03ad0215c516
  - 03e018e5065829295de0817f
  - 044289b85d5894aef9a9825d
  - 07f02f8bb9cf48ec09ba120e
  - 0814561e80d18ee7b5e8e214
  - 0874a8eb9ae4f8b6bb50a1d4
  - 098b1301820b7d581a339d0f
  update_cycle: 0
tags: []
version: 3
---

## When to use
Any question that asks for a specific point in time (e.g., contains "when", "date", "time", "last", "first", "most recent", "since", "on" followed by a date) and the answer would be a datetime value.

## Procedure
1. **Parse** the raw datetime string obtained from the FHIR resource into a Python `datetime` object (ignore any timezone offset, treat as naive UTC).
2. **Round** to the nearest hour:
   - If `minute >= 30`, add one hour.
   - Set `minute`, `second`, and `microsecond` to `0`.
3. **Format** the rounded datetime back to an ISO‑8601 string without a timezone offset.
4. **Return** this formatted string as the final answer.

## Checks
- Confirm that the value to be returned matches an ISO‑8601 datetime pattern before applying rounding.
- Ensure rounding does not unintentionally roll the date forward (e.g., 23:45 → next‑day 00:00) unless the hour increment crosses midnight.
- Do **not** apply rounding if the answer is not a datetime (e.g., a numeric value, text, or boolean).

## Avoid
- Returning unrounded timestamps for time‑related queries.
- Applying rounding to non‑datetime answers.
- Modifying the original timezone information; the output should be a naive ISO‑8601 string representing the rounded hour.
