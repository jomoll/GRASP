---
description: Detect empty Observation bundles and return a numeric -1 placeholder
  instead of a string.
name: handle_missing_observation
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - task4_26
  - task9_28
  - task2_9
  - task5_17
  - task9_3
  - task8_21
  - task4_23
  - task9_27
  - task2_15
  - task2_6
  update_cycle: 1
tags: []
version: 1
---

# handle_missing_observation

## Pattern Description
You must treat a missing laboratory Observation as a special case rather than trying to extract a value that does not exist. When a GET request for an Observation returns a Bundle with `total = 0`, the correct answer is the numeric placeholder **-1** (not the string "-1"). This skill centralises the check for an empty result set, ensures the placeholder is emitted as a number, and falls back to normal value extraction when data is present.

## When to Use This Skill
- When a task asks for the most recent value of a lab (e.g., magnesium, potassium, HbA1c) within a time window and the specification says to return **-1** if no measurement exists.
- Immediately after issuing a `GET {base}/Observation?...` request and receiving the Bundle response.
- When the Bundle `total` field is **0** or the `entry` array is missing/empty.

## Common Failure Patterns
- Returning `FINISH(["-1"])` (string inside array) instead of `FINISH([-1])`.
- Skipping the empty‑bundle check and attempting to read `valueQuantity` from a non‑existent entry, causing runtime errors.
- Providing a free‑text explanation rather than the required numeric placeholder.

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. Inspect the JSON response from the Observation GET request.
2. If `response.total == 0` **or** `!response.entry`:
   - Set `result = -1` (numeric).
   - Call `FINISH([result])` and **stop** further processing.

**Pattern 2: Normal extraction when data exists**
1. Locate the most recent entry (usually the first in `response.entry`).
2. Extract `valueQuantity.value` as a number.
3. If a unit conversion is required, invoke the `append_units_to_lab_value` skill.
4. Call `FINISH([extracted_number])`.

**Pattern 3: Fallback verification**
- After extracting a value, verify that the result is a number (e.g., `typeof result === "number"`).
- If verification fails, log a warning and fall back to `FINISH([-1])`.

## Example Application
**Task:** "What’s the most recent magnesium level of patient S1754095 within last 24 hours? Return -1 if not available."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1754095&date=ge2023-11-12T10:15:00Z`
2. Receive Bundle response.
3. Check `response.total`:
   - If `0` → `FINISH([-1])`.
   - Else extract `response.entry[0].resource.valueQuantity.value` → `mag_value`.
4. (Optional) Call `append_units_to_lab_value` to ensure unit is mg/dL.
5. `FINISH([mag_value])`.

**Correct output:** `FINISH([-1])` (numeric placeholder) when no observation exists.
**Incorrect output:** `FINISH(["-1"])` (string) or a free‑text sentence.

## Success Indicators
- The agent returns `FINISH([-1])` (numeric) for tasks where the Observation bundle is empty.
- No attempt is made to read `valueQuantity` from a missing entry.
- When data exists, the agent returns a plain number (e.g., `FINISH([2.1])`).

## Failure Indicators
- The FINISH payload contains a quoted "-1" or any explanatory text.
- The agent throws an error trying to access `response.entry[0]` when `total` is 0.
- The output includes additional fields or JSON objects instead of a single‑element array.
