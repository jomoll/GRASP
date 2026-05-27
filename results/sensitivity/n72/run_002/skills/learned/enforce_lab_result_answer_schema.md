---
description: "Validate that FINISH output for lab queries is a two\u2011element array\
  \ [numeric value, ISO\u20118601 date] and reject any other shape or type"
name: enforce_lab_result_answer_schema
provenance:
  action: MODIFY
  epoch: 3
  fixes: 9
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task8_14
  - task9_9
  - task8_3
  - task10_24
  - task9_22
  - task8_7
  - task8_13
  - task8_21
  update_cycle: 0
tags: []
version: 2
---

# Enforce Lab Result Answer Schema

## Pattern Description
You must ensure that any FINISH action that returns a lab result follows a strict schema: a JSON array with exactly two elements – the first a numeric value (integer or float) representing the measurement, the second a string in ISO‑8601 date‑time format indicating when the measurement was recorded. This pattern prevents downstream consumers from receiving ambiguous or human‑readable strings and guarantees that decision logic (e.g., threshold checks, ordering rules) can rely on a predictable data shape.

## When to Use This Skill
- When the task asks for "the last *X* value and when it was recorded" (e.g., HbA1c, potassium, magnesium).
- When the task expects a numeric answer only (e.g., magnesium level with sentinel `-1` for missing) – the output must still be a numeric element, not a string.
- Immediately before emitting FINISH for any Observation‑derived answer.

## Common Failure Patterns
- `FINISH(["6.1", "2023-10-13T22:22:00+00:00"])` – numeric value encoded as a string.
- `FINISH([6.1, 2023-10-13T22:22:00Z])` – date not quoted, thus not a string.
- `FINISH(["Latest potassium is 3.9 mmol/L (recorded 2023-11-12T14:07:00+00:00)."] )` – single‑element array of free‑text.
- `FINISH([])` or `FINISH(["No result"])` when the task explicitly expects a numeric/date pair.
- `FINISH([6.1])` – missing date element.
- `FINISH([6.1, "2023-10-13"])` – date missing time component or not ISO‑8601.

## Recommended Patterns
**Pattern 1: Core validation before FINISH**
1. Extract the measurement value from `valueQuantity.value` (or the appropriate field) as a number.
2. Extract the timestamp from `effectiveDateTime` (or `issued`) as a string.
3. Verify:
   - The value is a number (`typeof value === "number"`).
   - The timestamp matches the ISO‑8601 regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$`.
   - The array length is exactly 2.
4. If all checks pass, emit `FINISH([value, timestamp])`.
5. If any check fails, **do not** emit FINISH. Instead, request a corrected GET or raise a clarification.

**Pattern 2: Fallback for missing data**
- If the Observation bundle contains no entries for the requested code within the time window, emit `FINISH([-1])` for numeric‑only expectations **or** `FINISH([])` only when the task explicitly allows an empty result. Do not embed explanatory text inside the array.

**Pattern 3: Formatting rule**
- Always output the array **without** surrounding quotes for the array itself. Example:
  ```
  FINISH([5.9, "2023-11-12T06:19:00+00:00"])
  ```
- Never wrap the entire array in a string or add extra punctuation.

## Example Application
**Task:** "What’s the last HbA1C value for patient S3114648 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S3114648`
2. From the first entry in the Bundle, read:
   - `valueQuantity.value` → `6.1`
   - `effectiveDateTime` → `2023-10-13T22:22:00+00:00`
3. Validate types and format (numeric, ISO‑8601).
4. Emit:
   ```
   FINISH([6.1, "2023-10-13T22:22:00+00:00"])
   ```

## Success Indicators
- FINISH output is a two‑element JSON array.
- First element is a number, second element is a correctly formatted ISO‑8601 string.
- No extra text, brackets, or quotes around the array itself.
- Downstream logic (e.g., threshold comparison) runs without type errors.

## Failure Indicators
- FINISH contains a string where a number is required.
- Date string does not match ISO‑8601 pattern.
- Array length is not exactly two (or contains explanatory text).
- Agent emits FINISH before confirming the schema (e.g., after a failed GET).
- Any `FINISH` that includes free‑text explanations inside the array.
