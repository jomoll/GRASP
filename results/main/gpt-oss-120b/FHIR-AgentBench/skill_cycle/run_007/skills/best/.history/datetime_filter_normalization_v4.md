---
description: "Normalize datetime answers to date\u2011only when the question asks\
  \ for a date, removing time and timezone offsets."
name: datetime_filter_normalization
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 8
  failure_mode: datetime_format_mismatch
  fixes: 2
  parent_version: 3
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 0814561e80d18ee7b5e8e214
  - 0874a8eb9ae4f8b6bb50a1d4
  update_cycle: 0
tags: []
version: 4
---

## When to use
You must invoke this skill whenever the original user question clearly requests a **date** (e.g., it contains phrases like "when was", "what date", "first", "last", "since", "on */\d{4}", or any wording that does **not** ask for a specific time of day) and the raw answer you have retrieved from FHIR resources is an ISO‑8601 datetime string (e.g., `2023-04-11T15:57:43-04:00`).

## Procedure
1. **Detect date‑only intent** – Scan the user question (available to the agent) for any of the following case‑insensitive cues:
   - `when was`
   - `what date`
   - `first`
   - `last`
   - `since`
   - a month/year pattern like `04/2136` or `04/this year`
   - any phrase that ends with a year without a time component.
   If none of these cues are present, **do not** apply the skill (the time part may be required).
2. **Validate the answer format** – Confirm that the current answer is a string matching the ISO‑8601 datetime regex:
   ```
   ^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$```
   If it does not match, leave the answer unchanged.
3. **Parse and normalize** – Use a datetime parser (e.g., `datetime.fromisoformat` after stripping a trailing `Z`) to obtain a timezone‑aware `datetime` object.
4. **Strip time and offset** – Convert the datetime to its date component and format it as `YYYY‑MM‑DD`.
5. **Replace the answer** – Overwrite the agent's answer with the normalized date string.

## Checks
- The resource type of the original answer must be one that provides a datetime (e.g., `Observation.effectiveDateTime`, `Encounter.period.start`, `MedicationRequest.authoredOn`).
- The question must have been identified as date‑only in step 1.
- After normalization, the answer string must match the regex `^\d{4}-\d{2}-\d{2}$` (exactly a date, no time, no timezone).
- If the question explicitly asks for a time (e.g., contains "at 13:00", "hour", "minute"), skip this skill.

## Avoid
- Stripping the time component when the user explicitly requests a timestamp.
- Changing answers that are already in date‑only form.
- Applying the skill to non‑datetime answers (e.g., numeric values, free‑text).
- Leaving a timezone offset in the final answer when only the date is required.
