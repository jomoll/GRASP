---
description: Extend to handle numeric value comparisons and ordering for observation
  queries
name: fetch_observations_by_code_with_date_filter
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 3
  failure_mode: no_resource_query_performed
  fixes: 6
  parent_version: 1
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - 000f58d3abb4ad76b2ebc35c
  - 01c02f4b897bb8192e16bd1d
  - 0925d99c93fdf4626caf71cc
  update_cycle: 0
tags: []
version: 2
---

## When to use
You must invoke this skill whenever the user asks for a measurement (e.g., respiratory rate, blood pressure, heart rate, lab value) **and** the question includes:
- a specific observation code or free‑text name,
- an optional date window (e.g., "today", "since 06/07/2133", "in 09/this year"), **and**
- any numeric condition such as "< 23", ">= 120", "minimum value", "maximum value", "first measured", "last measured", or a comparison between two sequential measurements.
If any of those elements are present, this skill replaces a generic fetch‑encounter call.

## Procedure
1. **Parse the query** to extract:
   - Observation code/name (case‑insensitive, allow partial match).
   - Date constraints (start/end dates or relative periods like "today").
   - Numeric condition:
     - Comparison operator (`<`, `<=`, `>`, `>=`, `=`) with a constant value, **or**
     - Aggregation keyword (`minimum`, `maximum`, `first`, `last`, `second`, `third` etc.).
2. **Call the FHIR API** `get_resources_by_patient_fhir_id` with `resource_type="Observation"` and the patient FHIR ID.
3. **Filter the returned Observation bundle**:
   - Keep only those whose `code.coding.display`, `code.coding.code` or `code.text` contain the normalized target phrase.
   - Apply the date filter using `effectiveDateTime` or `effectivePeriod.start`.
   - If a numeric comparison is requested, extract the numeric value from `valueQuantity.value` (or `value` when appropriate). Discard observations without a numeric value.
   - For aggregation requests (`minimum`, `maximum`, `first`, `last`), collect all matching observations after steps above.
4. **Perform the requested calculation**:
   - For simple comparisons (`< 23`), find the earliest observation that satisfies the condition.
   - For `minimum`/`maximum`, select the observation with the smallest/largest numeric value.
   - For positional requests (`first`, `second`, `last`), sort by the effective datetime and pick the appropriate element.
   - For a *difference* between two measurements, obtain the two values in chronological order and compute `later - earlier` (preserving sign).
5. **Prepare the answer**:
   - Return the value and unit (e.g., `22 breaths/min`) when a single measurement is required.
   - Return a formatted date/time string (`YYYY‑MM‑DDThh:mm:ss`) when the question asks "when".
   - Return a numeric difference with unit when asked for a change.
   - If no matching observation is found, answer with a clear statement (e.g., "No respiratory rate observations found for the specified period").

## Checks
- Confirm the resource type is **Observation**.
- Verify that each candidate observation contains a numeric `valueQuantity.value` (or comparable field) before applying a numeric condition.
- Ensure the effective datetime is parsed correctly and falls within the requested window.
- Preserve the original unit from the observation; if the unit is missing, omit it in the answer.
- When the user asks for a date, return an ISO‑8601 timestamp without timezone conversion (use the stored value).
- Validate that the comparison operator and constant are present; if the user only asks for "first"/"last" without a numeric filter, skip step 3‑d.

## Avoid
- Do not return a result when the observation lacks a numeric value or when the date cannot be parsed.
- Do not assume a default unit; always use the unit supplied in the Observation.
- Do not answer with a boolean when the user expects a concrete value or timestamp.
- Do not ignore the user's explicit ordering request (e.g., "second measured") – always sort chronologically.
- Do not treat a free‑text code that matches multiple observation types as a match; require the normalized phrase to be present in the coding display/text.
