---
description: "Enforce correct string\u2011array format with units for lab query answers"
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 6
  triggering_sample_ids:
  - task9_9
  - task10_15
  - task1_7
  - task4_21
  - task4_10
  - task10_16
  - task2_6
  - task4_26
  - task2_26
  - task4_11
  update_cycle: 1
tags: []
version: 7
---

# Lab Observation Result Formatting

## Pattern Description
You must ensure that any answer derived from a FHIR Observation query is returned as a **single‑element string array** that includes the numeric value **followed by a space and the proper unit** (e.g., `"2.5 mg/dL"`). This pattern applies to all tasks that ask for the most recent lab value within a time window. Returning a bare number or a JSON object violates the expected answer format and leads to `answer_format_wrong_type` failures.

## When to Use This Skill
- When a task requests the most recent value of a lab (e.g., magnesium, potassium, HbA1c) within a specified period.
- After you have performed a GET on `/Observation` with appropriate `code`, `patient`, and `date` parameters and received a Bundle.
- The task expects a numeric result **or** `-1` when no recent observation exists.

## Common Failure Patterns
- `FINISH(2.5)` – raw numeric output.
- `FINISH([-1])` – numeric placeholder without string wrapper.
- Missing unit in the output string (e.g., `"2.5"`).
- Returning a JSON object or array of objects instead of a single string.

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Inspect the Bundle `entry[0].resource.valueQuantity`.
2. Extract `valueQuantity.value` as a number and `valueQuantity.unit` as a string.
3. If the unit is not `mg/dL`, convert the value accordingly (e.g., from `mmol/L` to `mg/dL`).
4. Build the result string: `"${value} ${unit}"`.
5. Call `FINISH([resultString])`.

   **CORRECT**: `FINISH(["2.5 mg/dL"])`
   **WRONG**: `FINISH(2.5)`

**Pattern 2: No recent observation fallback**
1. If the Bundle `total` is `0` or the entry list is empty, set `resultString = "-1"`.
2. Call `FINISH([resultString])`.

   **CORRECT**: `FINISH(["-1"])`

**Pattern 3: Verification before finish**
- Immediately before `FINISH`, verify that the output is an array of length 1 and that the element matches the regex `^-?\d+(\.\d+)?\s+[a-zA-Z/]+$` (or exactly `"-1"`).

## Example Application
**Task:** "What’s the most recent magnesium level of patient S1311412 within last 24 hours?"

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S1311412&date=ge2023‑11‑12T10:15:00&date=le2023‑11‑13T10:15:00&_sort=-date&_count=1`
2. Parse the returned Bundle. Suppose `valueQuantity.value = 2.5` and `valueQuantity.unit = "mg/dL"`.
3. Build `result = "2.5 mg/dL"`.
4. `FINISH(["2.5 mg/dL"])`.

**CORRECT output:** `FINISH(["2.5 mg/dL"])`
**WRONG output:** `FINISH(2.5)`

## Success Indicators
- The FINISH call contains an array with exactly one string element.
- The string ends with a recognized unit (e.g., `mg/dL`, `mmol/L`).
- No extra JSON structure is present.

## Failure Indicators
- FINISH receives a raw number, a JSON object, or an array with more than one element.
- The unit is missing or incorrectly spaced (e.g., `"2.5mg/dL"`).
- The placeholder `-1` is returned as a number instead of a string.
