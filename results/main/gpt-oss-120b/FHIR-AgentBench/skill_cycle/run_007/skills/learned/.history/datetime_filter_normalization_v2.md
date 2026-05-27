---
description: "Ensure date\u2011only answers when the question asks for a date, stripping\
  \ time components from datetime strings."
name: datetime_filter_normalization
provenance:
  baseline_fixes: 4
  baseline_regressions: 3
  epoch: 4
  failure_mode: datetime_format_mismatch
  fixes: 4
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 00fbe516569113decea8de73
  - 024e5c4760ca03ad0215c516
  - 031f4556ea1fe707a94f58bb
  - 0814561e80d18ee7b5e8e214
  - 0874a8eb9ae4f8b6bb50a1d4
  update_cycle: 1
tags: []
version: 2
---

## When to use
Trigger this skill for any question that requests a date (e.g., "when was …", "last hospital discharge", "first time …"), and the agent has produced a full ISO‑8601 datetime string.

## Procedure
1. **Parse user‑provided dates** – accept any textual format, convert to a Python `datetime` object, and apply inclusive filters on FHIR timestamps as before.
2. **Compute the answer** – perform the required retrieval, filtering, and selection (earliest, latest, etc.) yielding a `datetime` object.
3. **Determine expected granularity** – inspect the original question string:
   - If it contains any of the keywords `time`, `hour`, `minute`, `second`, `timestamp`, or a timezone indicator, keep the full datetime.
   - Otherwise assume the user only needs the calendar date.
4. **Format the answer**:
   - For date‑only expectations, output `dt.date().isoformat()` (e.g., `2023-07-15`).
   - For full‑datetime expectations, output `dt.isoformat()` preserving timezone if present.
5. Return the formatted string as the final answer.

## Checks
- Verify the resource type used in the query matches the question (Observation, MedicationRequest, etc.).
- Confirm the datetime was successfully parsed; if parsing fails, fallback to `None` and let higher‑level logic handle the missing data.
- Ensure the output matches the inferred answer type: a plain `YYYY‑MM‑DD` string for date‑only questions, otherwise a full ISO‑8601 timestamp.

## Avoid
- Returning timestamps with time components when the question only asks for a date, which caused the `datetime_format_mismatch` failures.
- Over‑truncating answers for questions that explicitly request time details.
- Assuming all datetime answers need the time part regardless of context.
