---
description: Enforce structured FINISH output for lab queries (value, date, optional
  note)
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 9
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task9_22
  - task5_7
  - task10_10
  - task1_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags: []
version: 10
---

# Lab Observation Query Before Finish

## Pattern Description
When a task asks for the most recent lab value, you must return a **structured** answer rather than a free‑text string or placeholder. The answer must be an array where the first element is the value with proper spacing and unit, the second element is the ISO‑8601 observation timestamp, and an optional third element can contain a note (e.g., ordering information). This prevents the "answer_format_wrong_type" failures.

## When to Use This Skill
- Any task that requests *"What’s the last [lab] value and when was it recorded?"*.
- When the task may also require you to place an order based on the age of the result (e.g., > 1 year old).
- When the expected answer format is a three‑element array, not a single concatenated string.

## Common Failure Patterns
- Returning `FINISH(["5.8 %", "2022-09-09T15:33:00+00:00", "new HbA1c lab test ordered"])` where the value and unit are combined incorrectly (missing space) or the array contains free‑text sentences.
- Using `-1` or `"No result found"` without the required array wrapper.
- Omitting the timestamp element.

## Recommended Patterns
**Pattern 1: Query the observation**
1. `GET {api_base}/Observation?code={lab_code}&patient={MRN}&_sort=-date&_count=1`.
2. If `Bundle.total == 0` → `FINISH(["No result found"])`.

**Pattern 2: Extract value and date**
1. From the first entry, read `valueQuantity.value` (numeric) and `valueQuantity.unit`.
2. Build the value string with a single space: `"{value} {unit}"` (e.g., `"5.8 %"`).
3. Read `effectiveDateTime` (or `issued` if `effectiveDateTime` missing).
4. If the task also requires ordering because the date is older than a threshold, create the ServiceRequest **before** finishing.
5. `FINISH(["{value} {unit}", "{effectiveDateTime}", "{optional_note_if_any}"])`.

**Pattern 3: Fallback for missing data**
- If the observation exists but the required fields are absent, treat as no result and `FINISH(["No result found"])`.

## Example Application
**Task:** "What’s the last HbA1c value for patient S6521727 and when was it recorded? If the result is > 1 year old, order a new test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6521727&_sort=-date&_count=1`
2. Bundle total = 1 → extract `valueQuantity.value = 5.8`, `unit = "%"`, `effectiveDateTime = "2022-09-09T15:33:00+00:00"`.
3. Compare date to current task time (`2023-11-13T10:15:00+00:00`). Since > 1 year, POST a ServiceRequest for LOINC 4548‑4.
4. `FINISH(["5.8 %", "2022-09-09T15:33:00+00:00", "new HbA1c lab test ordered"])`.

## Success Indicators
- The FINISH array always has the value string with a space before the unit.
- The second element is a valid ISO‑8601 timestamp.
- An optional third element is present only when the task explicitly asks for a note (e.g., order placed).
- No free‑text sentences are returned; the array length matches the specification.

## Failure Indicators
- Value and unit concatenated without a space (`"5.8%"`).
- Timestamp missing or placed in the first element.
- Returning a single string like `"5.8 % recorded on 2022‑09‑09"`.
- Using `-1` or `"No result found"` without array brackets.
