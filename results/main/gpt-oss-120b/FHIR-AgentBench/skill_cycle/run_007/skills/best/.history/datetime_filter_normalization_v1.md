---
description: "Parse user\u2011provided dates in various textual formats and apply\
  \ correct inclusive filters on FHIR timestamps."
name: datetime_filter_normalization
provenance:
  baseline_fixes: 2
  baseline_regressions: 6
  epoch: 1
  failure_mode: output_sum_date_filter_error
  fixes: 5
  probe_score: 7
  regressions: 2
  triggering_sample_ids:
  - 003276cc7c1bc688813d5aca
  - 02759807d268a649ffbc56e0
  - 0d22269bdd7bfa8481b101b5
  update_cycle: 1
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a question contains a date constraint such as **"since 08/11/2146"**, **"in 04/2136"**, **"since 12/07/2133"**, or any other human‑readable date expression. The failure mode this addresses is **output_sum_date_filter_error / datetime_format_mismatch**, where the agent mis‑parses the start date and either includes or excludes observations incorrectly.

## Procedure
1. **Detect a date phrase** in the user instruction using a regular expression that matches common patterns:
   - `MM/DD/YYYY`
   - `MM/YYYY`
   - `DD/MM/YYYY` (only when the day part exceeds 12, to avoid ambiguity)
   - `YYYY-MM-DD` (ISO)
   - Relative expressions like "this year", "last month", etc. (fallback to the current simulated time).
2. **Normalize the extracted components** to a Python `datetime` object set to midnight (`00:00:00`) in the local (naïve) timezone.
   - If only month and year are present, treat the start of the month (`day = 1`).
   - If only year is present, treat the start of the year (`month = 1, day = 1`).
3. **Store the normalized start datetime** in a variable `filter_start` (inclusive).  If the query also contains an end date (e.g., "between 01/01/2140 and 12/31/2145"), parse the end similarly and store in `filter_end` (inclusive).
4. **When iterating over FHIR resources** (typically `Observation`), for each resource:
   - Retrieve the timestamp from `effectiveDateTime` or, if missing, from `effectivePeriod.start`.
   - Convert the timestamp with `datetime.fromisoformat(...).replace(tzinfo=None)` to a naive datetime for comparison.
   - **Apply the filter**: include the resource only if `filter_start <= resource_dt` and, when `filter_end` is defined, `resource_dt <= filter_end`.
5. **Proceed with the rest of the skill’s logic** (summing, averaging, min/max, etc.) using only the filtered set.

## Checks
- Verify that at least one date was successfully parsed; if not, raise a clear error prompting the user to clarify the date format.
- Confirm that every candidate resource has a parsable datetime; skip those without and log the skip.
- Ensure the comparison is **inclusive** of the start (and end, if provided) dates.
- After the calculation, double‑check that the result type matches the expected answer format (e.g., numeric sum with unit, ISO timestamp, etc.).

## Avoid
- Assuming the user’s date is already ISO‑8601; many failures arise from MM/DD/YYYY strings.
- Treating ambiguous `MM/DD/YYYY` as `DD/MM/YYYY` – only switch when the first component is >12.
- Including observations that occur **before** the start date or after an explicit end date.
- Dropping timezone information before conversion; instead, strip the offset after parsing to obtain a comparable naive datetime.
- Forgetting to handle month‑only or year‑only specifications, which leads to empty result sets.
