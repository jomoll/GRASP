---
description: Return lab results with timestamp when the task asks for a date, using
  the correct array format
name: concise_lab_value_output
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 5
  triggering_sample_ids:
  - task1_12
  - task1_20
  - task1_11
  - task1_16
  - task1_13
  - task10_10
  - task10_12
  - task10_13
  - task9_1
  - task1_26
  update_cycle: 1
tags: []
version: 6
---

# concise_lab_value_output

## Pattern Description
You must extract the numeric result of a lab Observation and, **only when the task wording explicitly requests a date or timestamp**, also return the observation’s `effectiveDateTime`.  This skill centralises the rule for when to augment a scalar lab value with its recording time, preventing answers that omit required date information.

## When to Use This Skill
- When a task asks for a lab value **and** includes phrasing such as "when was it recorded", "date", "timestamp", or "when did it occur".
- When the task expects the answer to be either a plain scalar (e.g., `4.5`) **or** a two‑element array `[value, "2023-11-12T06:19:00+00:00"]` depending on the wording.
- Applicable to any Observation code (e.g., potassium, magnesium, HbA1c) where the FHIR response contains `valueQuantity` (or `valueString`) and `effectiveDateTime`.

## Common Failure Patterns
- Returning only the numeric value even though the task asked for the date, resulting in `FINISH([4.5])` instead of `FINISH([4.5, "2023-11-12T06:19:00+00:00"])`.
- Providing the timestamp in the wrong position or as a stringified array (e.g., `FINISH(["4.5", "2023-11-12T06:19:00+00:00"])`).
- Omitting the timestamp when the Observation lacks `effectiveDateTime` and not supplying a placeholder.

## Recommended Patterns
**Pattern 1: Core extraction and conditional timestamp inclusion**
1. After the GET request, locate the first entry in the Bundle’s `entry` array.
2. Extract the numeric result:
   - Prefer `valueQuantity.value` (number).
   - If only `valueString` exists, use it as‑is.
3. Extract the observation time from `effectiveDateTime` (ISO‑8601 string).
4. Scan the original task description for any of the keywords: `date`, `when`, `recorded`, `timestamp`.
5. If a keyword is found **and** `effectiveDateTime` is present, construct the answer as an array `[value, effectiveDateTime]`.
6. If no keyword is found, return the scalar `value` alone.
7. If a keyword is found but `effectiveDateTime` is missing, use the placeholder string `"unknown"` for the timestamp.

**Pattern 2: Fallback when extraction fails**
- If the Observation bundle is empty or the expected fields are absent, return the placeholder array `[ -1, "unknown" ]` (or just `-1` if no date is required).

**Pattern 3: Formatting for FINISH**
- Ensure the final FINISH call uses JSON‑compatible syntax:
  - Correct: `FINISH([4.5, "2023-11-12T06:19:00+00:00"])`
  - Wrong: `FINISH(["4.5", "2023-11-12T06:19:00+00:00"])` (value should be a number, not a string).

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S1311412 and when was it recorded?"

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=A1C&patient=S1311412`.
2. From the first entry, read `valueQuantity.value` → `5.9` and `effectiveDateTime` → `2023-11-12T06:19:00+00:00`.
3. The task contains the phrase "when was it recorded", so include the timestamp.
4. Construct the output array `[5.9, "2023-11-12T06:19:00+00:00"]`.
5. Call `FINISH([5.9, "2023-11-12T06:19:00+00:00"])`.

**Correct output:** `FINISH([5.9, "2023-11-12T06:19:00+00:00"])`
**Wrong output:** `FINISH([5.9])` (timestamp omitted).

## Success Indicators
- The FINISH payload contains a two‑element array when the task wording requests a date.
- The first element is a numeric lab value; the second is a valid ISO‑8601 timestamp string.
- No extra quotation marks around the numeric value.

## Failure Indicators
- FINISH returns only a scalar despite date‑related wording.
- Timestamp appears but the value is quoted as a string.
- The array order is reversed or contains additional fields.
- Placeholder `"unknown"` is used when a timestamp is actually present in the Observation.
