---
description: Format lab observation answers as raw numeric sentinel instead of list
name: structured_lab_observation_answer
provenance:
  action: MODIFY
  epoch: 3
  fixes: 4
  parent_version: 2
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_5
  - task3_17
  - task9_8
  - task5_3
  - task9_20
  - task9_27
  - task9_14
  - task9_6
  - task9_3
  - task1_7
  update_cycle: 1
tags: []
version: 3
---

# Structured Lab Observation Answer Formatting

## Pattern Description
You must ensure that any task that asks for the most recent lab value and expects a single numeric answer receives **only the numeric value**. The default `recent_lab_observation_query` skill returns a two‑element list `[value, timestamp]`. For answer‑type tasks this list is the wrong type and causes failures. This skill extracts the numeric component, discards the timestamp, and returns a raw numeric sentinel (`FINISH([value])`). It also preserves the sentinel `-1` when no recent observation exists.

## When to Use This Skill
- When a task description includes phrases like "most recent *lab* level", "last *lab* value", or "check patient ... *lab*" and the expected answer is a single number.
- After `recent_lab_observation_query` has been invoked and produced a list `[numeric, iso_timestamp]`.
- When the task does **not** request the date as part of the answer (i.e., the instruction does not ask for "when was it recorded").

## Common Failure Patterns
- Returning `FINISH([4.7, "2023-11-12T18:06:00+00:00"])` – a list instead of a single number.
- Including the timestamp in the final answer when the task only expects the value.
- Propagating the raw bundle entry without extracting `valueQuantity.value`.

## Recommended Patterns
**Pattern 1: Extract numeric sentinel**
1. Verify the last action was `recent_lab_observation_query` and its result is a list of length 2.
2. Assign `numeric_value = result[0]`.
3. If `numeric_value` is a number, call `FINISH([numeric_value])`.
4. If `numeric_value` is `-1` (no observation), call `FINISH([-1])`.

**Pattern 2: Fallback when result shape is unexpected**
- If the result is not a list or does not contain a numeric first element, log a warning and fall back to the original result (do not alter).

**Pattern 3: Guard against accidental date inclusion**
- Before finishing, ensure the output array length is exactly 1 (or 1 with `-1`). If length > 1, truncate to the first element.

## Example Application
**Task:** "Check patient S1796597's most recent potassium level."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597`
2. `recent_lab_observation_query` parses the bundle and returns `[4.7, "2023-11-12T18:06:00+00:00"]`.
3. `structured_lab_observation_answer` sees the list, extracts `4.7`.
4. Calls `FINISH([4.7])`.

**CORRECT output:** `FINISH([4.7])`
**WRONG output:** `FINISH([4.7, "2023-11-12T18:06:00+00:00"])`

## Success Indicators
- The final `FINISH` call contains a single‑element array with the numeric lab value (or `-1`).
- No timestamp appears in the answer for tasks that do not request it.
- Logs show "Extracted numeric sentinel from lab observation".

## Failure Indicators
- `FINISH` output still contains two elements (value and date).
- The skill logs a fallback warning for a correctly shaped result.
- Subsequent tasks that depend on the numeric value receive a list and fail.
