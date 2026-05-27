---
description: "Return a lab result and its timestamp as a two\u2011element array instead\
  \ of a combined string"
name: format_lab_value_with_date_array
provenance:
  action: ADD
  epoch: 1
  fixes: 14
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_8
  - task10_18
  - task10_24
  - task9_3
  - task10_15
  update_cycle: 1
tags: []
version: 1
---

# Format Lab Value With Date As Array

## Pattern Description
You must present any request that asks for *both* a quantitative lab result **and** the time it was recorded as a JSON array with exactly two elements: the raw numeric (or string) value and the ISO‑8601 timestamp. This keeps the answer type consistent (array of primitives) and lets downstream logic compare dates or trigger orders.

## When to Use This Skill
- When the task wording includes phrases like "last **X** value and when it was recorded", "most recent **Y** and its date", or "return the lab result together with the result date".
- The task expects a primitive answer (no free‑text explanation) and the most recent GET call returned a FHIR `Bundle` of `Observation` resources.
- The lab code is supplied in the query (e.g., `code=A1C`, `code=K`, `code=MG`).

## Common Failure Patterns
- Returning two separate `FINISH` arguments: `FINISH(["6.1 %", "2023-10-13T22:22:00+00:00"])` (strings instead of primitives).
- Concatenating value and date into one string: `FINISH(["5.9% recorded on 2023-11-12"])`.
- Omitting the timestamp or returning it in a non‑ISO format.
- Returning an array with more than two elements or nested objects.

## Recommended Patterns
**Pattern 1: Extract and format correctly**
1. After the `GET Observation?...` call, locate the entry with the most recent `effectiveDateTime` (or `issued`).
2. Extract `valueQuantity.value` **or** `valueString` **as a primitive** (do not include the unit).
3. Extract the timestamp from `effectiveDateTime` (or `issued`).
4. Build the answer array: `FINISH([value, timestamp])`.
   - **CORRECT**: `FINISH([6.1, "2023-10-13T22:22:00+00:00"])`
   - **WRONG**: `FINISH(["6.1 %", "2023-10-13T22:22:00+00:00"])`
   - **WRONG**: `FINISH(["6.1 % recorded on 2023-10-13"])`

**Pattern 2: Fallback when no recent result**
1. If the Observation bundle is empty **or** the most recent `effectiveDateTime` is older than the allowed window (e.g., >1 year), place the appropriate `ServiceRequest`.
2. Return the sentinel array `FINISH([-1])` to signal “no valid recent result”.

**Pattern 3: Validation before finishing**
- Verify the answer array length is exactly 2.
- Ensure the first element is a number (or plain string without units) and the second element matches the ISO‑8601 regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[Z+].*$`.
- If validation fails, fall back to Pattern 2.

## Example Application
**Task:** "What’s the last HbA1C value in the chart for patient S3114648 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S3114648`
2. From the returned Bundle, pick the entry with the greatest `effectiveDateTime`.
3. Extract `valueQuantity.value` → `6.1` (ignore the `%` unit).
4. Extract `effectiveDateTime` → `2023-10-13T22:22:00+00:00`.
5. `FINISH([6.1, "2023-10-13T22:22:00+00:00"])`.

**If the most recent date were `2022-09-01` (older than 1 year):**
- POST a `ServiceRequest` for LOINC `4548-4` (HbA1c).
- `FINISH([-1])`.

## Success Indicators
- The final `FINISH` call contains an array of length 2.
- The first element is a plain number (or unit‑less string) and the second element is a valid ISO‑8601 timestamp.
- No free‑text or combined strings appear in the answer.

## Failure Indicators
- `FINISH` receives a single string that mixes value and date.
- The array contains more than two items or nested objects.
- The timestamp is missing, malformed, or not ISO‑8601.
- The agent orders a new test but still returns a combined string instead of `[-1]`.

---
*Tag your skill with:* `lab`, `answer_format`, `array_output`
