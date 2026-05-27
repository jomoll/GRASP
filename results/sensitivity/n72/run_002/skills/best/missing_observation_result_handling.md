---
description: Handle empty Observation results for value/date answer schema
name: missing_observation_result_handling
provenance:
  action: ADD
  epoch: 1
  fixes: 6
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task5_19
  - task10_12
  - task9_1
  - task9_8
  - task9_20
  - task9_5
  - task9_3
  - task10_21
  - task9_6
  - task9_14
  update_cycle: 1
tags:
- lab
- observation
- error_handling
version: 1
---

# Missing Observation Result Handling for Value‑Date Answers

## Pattern Description
When a task asks for the latest lab value **and** the date it was recorded, the answer must follow the `[numeric_value, "ISO‑date"]` schema. If the FHIR `Observation` search returns no entries, emitting a placeholder such as `[-1]` violates this schema and leads to downstream errors. This skill enforces a consistent fallback: return an empty array `[]` (or a clear “no result” message) instead of a numeric placeholder.

## When to Use This Skill
- After a `GET /Observation?...` request where the response `Bundle.total` is `0`.
- The task explicitly expects a **value‑date pair** (e.g., HbA1c, cholesterol, creatinine).
- The agent is about to call `FINISH` with a single numeric placeholder.

## Common Failure Patterns
- `FINISH([-1])` after an empty Observation bundle.
- Returning `[null, "2023-01-01T00:00:00+00:00"]` when no result exists.
- Omitting the date field while providing a numeric value.

## Recommended Patterns
**Pattern 1: Detect empty result set**
1. Inspect the `total` field of the returned `Bundle`.
2. If `total == 0`, **do not** extract any value.
3. Immediately call `FINISH([])` (or a predefined “no result” string if the task wording requires it).

**Pattern 2: Verify schema before finishing**
1. If a value is extracted, ensure you have both:
   - `valueQuantity.value` (or `valueDecimal`) as a number.
   - `effectiveDateTime` (or `issued`) as an ISO‑8601 datetime string.
2. Only then call `FINISH([value, date])`.
3. If either component is missing, fall back to Pattern 1.

**Pattern 3: Logging for debugging**
- Optionally emit a comment (e.g., `# No Observation found for code=A1C, patient=S123`) before the `FINISH([])` call to aid traceability.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6550627 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6550627`
2. Receive a `Bundle` with `"total": 0`.
3. Apply Pattern 1 → `FINISH([])`.

**Correct output:** `FINISH([])`
**Wrong output:** `FINISH([-1])`

## Success Indicators
- The agent calls `FINISH([])` (or the task‑specified no‑result message) whenever the Observation bundle is empty.
- No `FINISH` calls contain a single numeric placeholder for value‑date tasks.
- Subsequent `enforce_lab_result_answer_schema` validation passes.

## Failure Indicators
- `FINISH([-1])` or any single‑element array is emitted after an empty Observation bundle.
- The output array contains a numeric value but lacks a valid ISO‑date string.
- Validation errors from `enforce_lab_result_answer_schema` persist.
