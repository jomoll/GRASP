---
description: Preserve time component unless the question explicitly asks for a date
  only
name: datetime_filter_normalization
provenance:
  baseline_fixes: 2
  baseline_regressions: 0
  epoch: 19
  failure_mode: datetime_missing_time_component
  fixes: 4
  parent_version: 4
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 01bb1845215fb7cc77678534
  - 05bb819666668fc43bad2666
  - 0a5e5b2f22a73ebf9ddd7a3a
  update_cycle: 0
tags: []
version: 5
---

## When to use
You should trigger this skill for any answer that is a FHIR datetime **and** the original user question is asking for a date without a time component. Typical cues are words like "date", "day", "on which day", "when was" (without a following time phrase). If the question includes time‑specific words such as "time", "at", "hour", "datetime", or provides a concrete timestamp, do **not** strip the time.

## Procedure
1. **Inspect the original question** (the raw user prompt) before formatting the answer.
2. Detect date‑only intent:
   - Lower‑case the question.
   - If it contains any of the tokens `date`, `day`, `on which day`, `which date`, and does **not** contain any of the tokens `time`, `at `, `hour`, `datetime`, `timestamp`, treat it as date‑only.
3. After you have computed the answer datetime (ISO‑8601 string), apply the following:
   - If the question was classified as date‑only, truncate the string to the date part (`YYYY‑MM‑DD`).
   - Otherwise, keep the full datetime (including time and offset) exactly as returned by the FHIR resource.
4. Return the formatted answer.

## Checks
- Verify that the answer originates from a resource field that is a datetime (`effectiveDateTime`, `issued`, `performedDateTime`, etc.).
- Confirm the original question text is available for the keyword scan.
- Ensure the final answer respects the required format: either `YYYY‑MM‑DD` for date‑only or full ISO‑8601 for datetime.

## Avoid
- Stripping the time component when the question asks for an exact moment (e.g., "When did the patient receive the test?" or "What time was the discharge?`).
- Leaving the time component when the user only wants a date, which leads to mismatched answer types.
