---
description: Format medication prescription dates as MM/DD/YYYY when the question
  asks for a date
name: medication_datetime_format
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 3
  failure_mode: datetime_output_format_incorrect
  fixes: 6
  probe_score: 3
  regressions: 3
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 03e018e5065829295de0817f
  - 0814561e80d18ee7b5e8e214
  - 0874a8eb9ae4f8b6bb50a1d4
  - 098b1301820b7d581a339d0f
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must trigger this skill whenever a user asks **when** a medication was prescribed (first, last, earliest, most recent, etc.) and the answer is expected to be a calendar date, not a full timestamp. Typical question patterns include:
- "When was patient X first prescribed ...?"
- "When did patient X last receive a prescription for ...?"
- "What was the date of the first medication ...?"
If the query involves a medication request and the desired output is a date, apply this skill.

## Procedure
1. **Run the existing medication request query** to obtain the relevant `authoredOn`, `occurrenceDateTime`, or any other date field as a Python `datetime` object.
2. **Extract only the date component** (year, month, day) from the `datetime`.
3. **Format the date** as a string in the exact form `MM/DD/YYYY` (zero‑padded month and day). Example: `datetime_obj.strftime('%m/%d/%Y')`.
4. Return the formatted string as the final answer **without any time‑of‑day information or timezone suffix**.
5. If multiple dates are possible (e.g., earliest vs. latest), select the appropriate one **before** formatting.

## Checks
- Verify that the resource type used is `MedicationRequest` (or a related `MedicationAdministration` when appropriate).
- Ensure a date was successfully extracted; if none is found, answer with a clear statement that the date is unavailable.
- Confirm that the output matches the `MM/DD/YYYY` pattern (regex `^\d{2}/\d{2}/\d{4}$`).
- Do not include time, timezone, or milliseconds in the answer.

## Avoid
- Returning the raw ISO‑8601 timestamp (e.g., `2110-04-11T15:57:43`).
- Adding extra text or explanations; the answer must be exactly the formatted date string.
- Applying this formatting to non‑date questions (e.g., lab values, counts, or observations that legitimately require timestamps).
