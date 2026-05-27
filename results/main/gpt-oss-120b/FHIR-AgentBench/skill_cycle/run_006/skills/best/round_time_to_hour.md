---
description: Rounds datetime values down to the start of the hour instead of nearest
  hour.
name: round_time_to_hour
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 7
  failure_mode: answer_time_rounded_up_unexpected
  fixes: 3
  parent_version: 3
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 03e018e5065829295de0817f
  - 07f02f8bb9cf48ec09ba120e
  - 0a5e5b2f22a73ebf9ddd7a3a
  update_cycle: 1
tags: []
version: 4
---

## When to use
You should invoke this skill whenever a question asks for a time value (e.g., prescription date, discharge time, lab timestamp) and the answer must be expressed as an ISO‑8601 datetime rounded to the hour **without** rounding up. This replaces the previous "nearest hour" behavior which caused unexpected upward rounding.

## Procedure
1. **Identify the datetime field** you will return (e.g., `authoredOn`, `effectiveDateTime`, `period.start`, `period.end`).
2. Parse the string with `datetime.fromisoformat` (ignore any timezone offset; treat all times as naive UTC).
3. **Floor the datetime**:
   ```python
   dt = dt.replace(minute=0, second=0, microsecond=0)
   ```
   Do **not** add an hour when the original minute is ≥ 30.
4. Convert the floored datetime back to an ISO‑8601 string (`dt.isoformat()`).
5. Return that string as the final answer.

## Checks
- Verify the resource type contains a datetime field you are rounding (Observation, MedicationRequest, Encounter, etc.).
- Ensure the datetime is not `None`; if missing, answer "No date found" or the appropriate fallback.
- Confirm the answer format is a plain ISO‑8601 string (e.g., `2023-05-18T19:00:00`).
- Do not modify the date beyond flooring; the year, month, day must stay unchanged.

## Avoid
- Adding an hour when the original minutes are 30 or greater (the previous "nearest hour" logic).
- Changing the timezone or offset; keep the original offset stripped.
- Returning a datetime with minutes, seconds, or microseconds non‑zero.
- Applying this skill to non‑datetime answers (e.g., boolean, numeric) – use other appropriate skills instead.
