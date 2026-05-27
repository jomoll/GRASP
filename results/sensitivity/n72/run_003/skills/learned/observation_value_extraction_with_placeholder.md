---
description: "Extract latest numeric observation and date, always return a two\u2011\
  element array with placeholders when missing"
name: observation_value_extraction_with_placeholder
provenance:
  action: MODIFY
  epoch: 4
  fixes: 4
  parent_version: 3
  probe_score: 2
  regressions: 0
  triggering_sample_ids: []
  update_cycle: 1
tags:
- observation
- extraction
- placeholder
version: 4
---

# observation_value_extraction_with_placeholder

## Pattern Description
You must reliably pull the most recent numeric value for a given Observation code (or any numeric‑valued element) together with its `effectiveDateTime`.  The output **must always** be a two‑element array `[value, timestamp]`.  If the search returns no Observation, emit `[null, null]` (or a task‑specified placeholder) so downstream logic never receives a single‑element or missing array.

## When to Use This Skill
- When a task asks for "the last *X* value and when it was recorded".
- When the downstream logic expects a fixed‑size array (e.g., age checks, conditional ordering) and would break on a missing element.
- When the Observation bundle may be empty or may contain non‑numeric representations (e.g., `valueString`).

## Common Failure Patterns
- Returning `[-1]` or a single number instead of `[value, date]`.
- Concatenating the unit with the numeric value (`"5.4 mmol/L"`).
- Using `issued` or `effectivePeriod.start` instead of `effectiveDateTime`.
- Omitting the placeholder when the bundle is empty, causing downstream index errors.

## Recommended Patterns
**Pattern 1: Core extraction**
1. Issue a GET request:
   ```
   GET {api_base}/Observation?code={code}&patient={patient_id}&_sort=-effectiveDateTime&_count=1
   ```
2. If `Bundle.total == 0` → **fallback** (Pattern 2).
3. Otherwise, locate the first `entry.resource`.
4. Extract the numeric value:
   - Prefer `valueQuantity.value` (number).
   - If missing, try parsing `valueString` for a leading number.
5. Extract the timestamp from `effectiveDateTime`.
6. Return `FINISH([value, timestamp])`.

**Pattern 2: Placeholder fallback**
- When no Observation is found, return the placeholder defined by the task (default `[null, null]`).
- Example:
  ```
  FINISH([null, null])
  ```

**Pattern 3: Validation**
- Verify that the extracted `value` is a number; if parsing fails, treat as missing and use the placeholder.
- Ensure the timestamp is an ISO‑8601 string.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6521727 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6521727&_sort=-effectiveDateTime&_count=1`
2. Bundle contains one entry → extract:
   - `valueQuantity.value` → `5.8`
   - `effectiveDateTime` → `2022-09-09T15:33:00+00:00`
3. `FINISH([5.8, "2022-09-09T15:33:00+00:00"])`

**If the bundle were empty:**
- Return `FINISH([null, null])` (or the task‑specified placeholder).

## Success Indicators
- The final `FINISH` output is always a two‑element array.
- Numeric value is a plain number, not a string with units.
- Timestamp is a valid ISO‑8601 datetime.
- No `IndexError` or missing‑element errors in downstream logic.

## Failure Indicators
- Output array has length ≠ 2.
- Value is a string containing units.
- Timestamp is missing or malformed.
- Agent returns `[-1]` or an empty array for a task that expects a two‑element result.
