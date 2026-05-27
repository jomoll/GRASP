---
description: "Handles observation\u2011related questions (presence, min/max, first/last,\
  \ comparisons, aggregates) for a patient."
name: observation_query
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 1
  failure_mode: no_fhir_query_executed
  fixes: 4
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - 000f58d3abb4ad76b2ebc35c
  - 01c02f4b897bb8192e16bd1d
  - 0266d6e5d007484e57bf12d6
  - 059ed55281d42669ad25d514
  - 05c1bc3943f37d24fbc4a227
  - 06c9202911fa52427beba085
  - 0814561e80d18ee7b5e8e214
  - 0925d99c93fdf4626caf71cc
  - 0a0992495803104da30af972
  - 0a403bb61217529f94970734
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must activate this skill when the user asks about **numeric or coded observations** for a patient. Typical triggers include:
- Presence or count of a specific lab/vital (e.g., "Did patient X have a calcium test?", "How many blood pressure measurements?" )
- Aggregations such as *minimum*, *maximum*, *average*, *sum*, *difference* of an observation value.
- Temporal filters like *today*, a specific month/year, "since <date>", "in the last N days", or a range.
- Value comparisons (e.g., "first time respiratory rate < 23", "observations greater than 140" ).
- Ordering requests like *first*, *last*, *second‑to‑last* measurement.
If none of the above patterns are detected, do not use this skill.

## Procedure
1. **Parse the query**
   - Identify the target observation term (code, display text, or common synonym).
   - Detect any aggregation keyword: `minimum`, `max`, `maximum`, `average`, `mean`, `sum`, `total`, `count`, `difference`, `first`, `last`, `second to last`, etc.
   - Extract any **date filter**:
     * explicit dates (`2023‑04‑12`), month/year (`04/2023`), relative terms (`today`, `this year`, `since 01/2020`).
   - Extract any **value filter** (`< 23`, `> 140`, `= 7.5`).
   - Detect required **output format** (value with unit, date, count, boolean).
2. **Retrieve resources**
   - Call `get_resources_by_patient_fhir_id` with `resource_type="Observation"`.
3. **Filter observations**
   - For each Observation, build a **normalized code string** by concatenating:
     * `code.text`
     * each `code.coding.display`
     * each `code.coding.code`
   - Keep the observation if the normalized string contains the target term (case‑insensitive, whitespace‑collapsed).
   - Resolve the observation date using `effectiveDateTime` first, then `effectivePeriod.start`.
   - Apply the extracted date filter; discard observations outside the window.
   - If a value filter exists, ensure the observation has a numeric `valueQuantity.value` (or `valueDecimal`) and that it satisfies the comparator.
4. **Perform aggregation**
   - **Count**: number of remaining observations.
   - **Minimum / Maximum**: pick the observation with the smallest/largest numeric value.
   - **Average / Mean**: compute arithmetic mean of numeric values.
   - **Sum / Total**: add all numeric values.
   - **Difference**: if the query asks for difference between two ordered values (e.g., "last vs second to last"), sort by date and subtract the earlier from the later.
   - **First / Last / N‑th**: sort by date (ascending) and pick the requested position.
5. **Compose the answer**
   - If the result is a **value**, include the unit from `valueQuantity.unit` when available.
   - If the result is a **date**, return the ISO‑8601 string.
   - If the result is a **boolean** (e.g., presence), answer `Yes` or `No`.
   - If the result is a **count**, return an integer.
6. **Return** the answer as plain text (no JSON wrapper).

## Checks
- Verify that at least one Observation resource was retrieved; if none match, answer appropriately (`No` for presence queries, `0` for counts, or a clear "No matching observations found" message).
- Ensure the resource type is **Observation** and that any numeric aggregation uses `valueQuantity.value` (or `valueDecimal`).
- Confirm the date filter produced a non‑empty set; if the filter is contradictory, fall back to an empty‑set answer.
- When returning a value, include the unit; if multiple units appear, report the most common one or note the inconsistency.
- Validate that the answer format matches the expected type (boolean, number, date, or count).

## Avoid
- Returning raw FHIR JSON objects instead of a concise answer.
- Ignoring case or extra whitespace when matching observation terms.
- Using `effectivePeriod.end` for the observation timestamp; always prefer `effectiveDateTime` or `effectivePeriod.start`.
- Mixing observation filtering with unrelated resources (e.g., Procedure, Medication).
- Dropping observations that lack a numeric value when the query explicitly asks for a numeric aggregation.
- Performing aggregations on an empty list and producing errors.
- Assuming a single unit for all observations without checking; report unit mismatches.
