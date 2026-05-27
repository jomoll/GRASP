---
description: Return lab results as scalar or [value, timestamp] array depending on
  task wording
name: concise_lab_value_output
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 3
  triggering_sample_ids:
  - task1_27
  - task8_14
  - task10_20
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task5_16
  - task9_11
  update_cycle: 0
tags:
- lab
- formatting
version: 4
---

# Concise Lab Value Output

## Pattern Description
You must format the answer for any lab‑value query in the most compact representation that satisfies the task.  When the instruction only asks for the numeric result (e.g. "What is the potassium level?"), return a single scalar.  When the instruction explicitly requests the value **and** the time it was recorded (e.g. "What’s the last HbA1C value and when was it recorded?"), return a two‑element array `[value, "timestamp"]`.  This keeps the output machine‑readable while still honoring the request for a timestamp.

## When to Use This Skill
- Any task that includes a GET /Observation (or similar) and the wording mentions **value** *and* **date/time**.
- Tasks that only ask for the numeric result without a date.
- When the task later uses the timestamp for a conditional decision (e.g., order a repeat test if older than 1 year).

## Common Failure Patterns
- Returning a single string that concatenates value and timestamp (e.g. `"6.5% recorded on 2022‑03‑08"`).
- Returning an array that contains the unit together with the value (e.g. `["6.5%", "2022‑03‑08"]`).
- Omitting the timestamp when the task explicitly asks for it.

## Recommended Patterns
**Pattern 1: Decide output shape**
1. Parse the task description for keywords `"when was it recorded"`, `"date"`, `"time"`, or similar.
2. If such keywords are present, plan to output an array `[value, iso_timestamp]`.
3. Otherwise, plan to output the scalar `value` (optionally with unit if the task asks for it).

**Pattern 2: Extract the numeric value**
- Locate `valueQuantity.value` (or `valueString` for non‑numeric labs) in the Observation resource.
- Convert to the requested unit if needed (e.g., `%` for HbA1c, mg/dL for electrolytes).

**Pattern 3: Extract the timestamp**
- Use `effectiveDateTime` if present; fall back to `issued`.
- Ensure the timestamp is an ISO‑8601 string with timezone (e.g., `2023-11-02T06:53:00+00:00`).

**Pattern 4: Build the FINISH payload**
- For scalar output: `FINISH([value])` or `FINISH([value, "unit"])` if unit is required.
- For value + timestamp: `FINISH([value, "timestamp"])`.

## Example Application
**Task:** "What’s the last HbA1C value in the chart for patient S0658561 and when was it recorded?"

**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S0658561`.
2. From the returned Observation, read `valueQuantity.value` → `5.4` and `effectiveDateTime` → `2023-11-02T06:53:00+00:00`.
3. Because the task asks for the date, format as an array.
4. `FINISH([5.4, "2023-11-02T06:53:00+00:00"])`.

**CORRECT output:** `FINISH([5.4, "2023-11-02T06:53:00+00:00"])`
**WRONG output:** `FINISH(["5.4% recorded on 2023-11-02T06:53:00+00:00"])`

## Success Indicators
- The FINISH payload is either a single number (or number + unit) **or** a two‑element array when a timestamp is requested.
- No free‑text narrative is present in the FINISH result.

## Failure Indicators
- FINISH contains a concatenated string mixing value and date.
- The timestamp is missing or not ISO‑8601.
- The array contains the unit as a separate string when the task did not ask for it.
