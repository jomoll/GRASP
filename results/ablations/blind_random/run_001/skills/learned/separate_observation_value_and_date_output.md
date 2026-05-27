---
description: Return observation result and its timestamp as two distinct answer elements
  instead of a combined string.
name: separate_observation_value_and_date_output
provenance:
  action: ADD
  blind_select: random
  epoch: 0
  fixes_unused: 4
  probe_score_unused: 1
  regressions_unused: 2
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  - task5_16
  update_cycle: 1
tags: []
version: 1
---

# Separate Observation Value and Date Output

## Pattern Description
You must present the numeric result of an Observation (including its unit) **and** the date it was recorded as two separate items in the FINISH array.  This prevents downstream logic from having to parse a combined "value on date" string and makes it easy to apply date‑based rules (e.g., ordering a new test if the result is > 1 year old).  The pattern applies to any task that explicitly asks for "the last X value and when it was recorded" or similar phrasing.

## When to Use This Skill
- When the task asks for the most recent lab or vital sign **value** **and** the **date** it was taken (e.g., "What’s the last HbA1c value and when was it recorded?").
- After you have performed a GET on an Observation bundle and identified the relevant entry.
- Even if you subsequently need to place an order based on the date, the answer must still be split.

## Common Failure Patterns
- Returning a single combined string such as `"6.1 % on 2023-10-13"`.
- Omitting the unit (e.g., returning just `6.1`).
- Placing the date in a human‑readable sentence instead of a plain ISO‑8601 date.
- Using the wrong date field (`effectivePeriod.start` instead of `effectiveDateTime` or `issued`).

## Recommended Patterns
**Pattern 1: Extract numeric value with unit**
1. Locate the Observation entry with the highest `effectiveDateTime` (or `issued` if `effectiveDateTime` missing).
2. If the Observation uses `valueQuantity`, read:
   - `valueQuantity.value` → numeric part
   - `valueQuantity.unit` → unit string (e.g., "%", "mmol/L")
   - Combine as `"{value} {unit}"` (e.g., `"6.1 %"`).
3. If the Observation uses `valueString` (common for percentages), use the string directly (it already contains the unit).

**Pattern 2: Extract the recording date**
1. Prefer `effectiveDateTime` if present.
2. If missing, fall back to `issued`.
3. Return the date in **ISO‑8601** format (e.g., `2023-10-13`).

**Pattern 3: Build the FINISH response**
```json
FINISH(["6.1 %", "2023-10-13"])
```
Do **not** embed any extra wording, commas, or sentences inside the array elements.

**Pattern 4: Fallback when date missing**
- If no date field can be found, return the value and the string `"date_unknown"` as the second element.

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S3114648 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S3114648`
2. From the returned Bundle, pick the entry with the most recent `effectiveDateTime`.
3. Extract:
   - `valueQuantity.value = 6.1`
   - `valueQuantity.unit = "%"`
   - `effectiveDateTime = 2023-10-13`
4. Build the answer:
   ```
   FINISH(["6.1 %", "2023-10-13"])
   ```
5. Compare the date to the current time; if older than 1 year, issue the ServiceRequest for a new HbA1c test (this part is handled by other skills).

**Correct output:** `FINISH(["6.1 %", "2023-10-13"])`
**Incorrect output:** `FINISH(["6.1 % on 2023-10-13"])`

## Success Indicators
- The FINISH array contains exactly two elements.
- The first element is a string of the numeric value **plus** its unit.
- The second element is a plain ISO‑8601 date string.
- Subsequent decision logic (e.g., date comparison) can access the date element directly.

## Failure Indicators
- FINISH contains a single combined string.
- The unit is missing or duplicated (e.g., `"6.1 % %"`).
- The date is formatted with extra text or in a non‑ISO format.
- The array has more than two elements or includes empty strings.
