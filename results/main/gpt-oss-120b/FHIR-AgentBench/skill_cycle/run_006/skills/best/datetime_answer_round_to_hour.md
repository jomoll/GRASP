---
description: "Rounds ISO\u20118601 datetime answers down to the start of the hour\
  \ before returning them."
name: datetime_answer_round_to_hour
provenance:
  baseline_fixes: 4
  baseline_regressions: 3
  epoch: 13
  failure_mode: answer_time_not_rounded_to_hour
  fixes: 6
  probe_score: 2
  regressions: 3
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 0814561e80d18ee7b5e8e214
  - 0901f19617fd97688d40bbbd
  - 098b1301820b7d581a339d0f
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must invoke this skill whenever the question explicitly asks for a point in time (e.g., *"When was the first prescription..."*, *"What time did the patient leave the hospital?"*) and the answer you have assembled is an ISO‑8601 datetime string.

## Procedure
1. **Detect datetime answer** – If the provisional answer is a string that matches the pattern `YYYY-MM-DDTHH:MM:SS` (optionally with a timezone suffix), treat it as a datetime.
2. **Parse** the string using `datetime.fromisoformat` (or an equivalent parser) and discard any timezone information, yielding a naïve `datetime`.
3. **Round down** the datetime to the start of the hour:
   ```python
   rounded = dt.replace(minute=0, second=0, microsecond=0)
   ```
4. **Re‑format** the rounded datetime back to an ISO‑8601 string (preserve the original timezone suffix if it existed).
5. Replace the provisional answer with this rounded string.

## Checks
- Confirm the original answer is a valid ISO‑8601 datetime; if parsing fails, leave the answer unchanged.
- Ensure the answer type is a string (not a boolean, number, or complex object).
- Verify that the question’s intent is to obtain a timestamp; do not apply to dates that are part of a range or duration calculation.

## Avoid
- Rounding values that are already at hour precision (no effect, but skip unnecessary work).
- Applying the skill to non‑datetime answers such as booleans, counts, or free‑text responses.
- Introducing timezone conversion – only the hour component is truncated; the original offset is retained unchanged.
