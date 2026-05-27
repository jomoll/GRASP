---
description: "Add explicit empty\u2011result handling for numeric aggregation queries"
name: numeric_aggregation_query
provenance:
  baseline_fixes: 2
  baseline_regressions: 2
  epoch: 3
  failure_mode: empty_result_not_handled
  fixes: 4
  parent_version: 1
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 01389011a3cea028b226b95b
  - 02885cc1fb11efec74cb16fd
  - 0424a90b6986dc6ca2da8b3b
  update_cycle: 1
tags: []
version: 2
---

## When to use
Trigger this skill when the user asks for an aggregate (average, min, max, total, count, sum, etc.) of numeric values from Observation, Measurement, LabResult, or similar resources and the query includes date/encounter filters.

## Procedure
1. **Retrieve resources** – Use `get_resources_by_patient_fhir_id` (or by encounter) for the relevant resource type.
2. **Filter by user constraints** – Apply any date range, encounter scope, or keyword matching on the observation code (display, code, or text) exactly as the user described.
3. **Extract numeric values** – For each remaining resource, pull the value from `valueQuantity.value`, `valueDecimal`, or `valueInteger` (ignore non‑numeric entries).
4. **Compute the requested aggregate** – Calculate `average`, `min`, `max`, `total`, or `count` as specified.
5. **Empty‑result check** – If the filtered list contains zero numeric values, **do not** proceed to step 4. Instead set the answer to a clear message:
   - For average/min/max/total: `"No matching observations found for the requested criteria."`
   - For count: `"0"` (as a plain number) – this is the only case where a numeric zero is a valid answer.
6. **Format the answer** – Return the aggregate as a plain number (or the explicit message from step 5). Do not wrap the result in additional text.

## Checks
- Verify the resource type is numeric (Observation, Measurement, etc.).
- Ensure at least one resource passes all filters before computing the aggregate.
- Confirm the extracted values are of type `int` or `float`.
- If the user asked for a count, returning `0` is acceptable; otherwise return the explicit *no‑data* string.
- The final answer must match the requested unit‑less format (e.g., `42.5` or the message above).

## Avoid
- Returning an empty string or `null` when no data matches.
- Implicitly treating an empty list as `0` for aggregates other than count.
- Adding extra explanatory sentences; the answer should be exactly the number or the predefined no‑data message.
