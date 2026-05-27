---
description: Extract numeric lab result and its recording date, output them as separate
  fields
name: lab_observation_value_and_timestamp
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task8_26
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  update_cycle: 1
tags:
- lab
- observation
- formatting
- value_extraction
version: 1
---

# Lab Observation Value and Timestamp Extraction

## Pattern Description
You must reliably pull the quantitative result and the exact recording timestamp from a FHIR Observation and present them as distinct elements rather than a combined narrative string. This pattern applies to any lab or measurement where the task explicitly asks for "value" and "when it was recorded" (e.g., HbA1c, serum magnesium, potassium). By separating the two pieces, downstream logic such as age‑based re‑ordering or threshold checks can operate on clean data.

## When to Use This Skill
- When a task asks for the *last* lab value **and** the date it was recorded (e.g., "What’s the last HbA1c value and when was it recorded?").
- When the expected answer format is a JSON‑compatible array or separate arguments, not a free‑text sentence.
- When the Observation may contain multiple entries; you need the most recent one.
- When the Observation uses `valueQuantity` (numeric) or a percent string in `valueString`.

## Common Failure Patterns
- Returning a single narrative string like `"6.1% on 2023-10-13"` instead of separate fields.
- Omitting the timestamp entirely.
- Concatenating the unit with the value (e.g., `"6.1%"` without extracting the numeric `6.1`).
- Using the wrong field (`issued` instead of `effectiveDateTime`).

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. **Issue the GET** for the Observation using the appropriate code and patient identifier.
2. **Parse the Bundle** and locate the `entry` array.
3. **Select the most recent Observation** by comparing `effectiveDateTime` (or `issued` if `effectiveDateTime` missing).
4. **Extract the numeric value**:
   - If `valueQuantity` exists, use `valueQuantity.value` (a number).
   - If only `valueString` exists and contains a percent, strip non‑numeric characters to obtain a float.
5. **Extract the timestamp** from `effectiveDateTime` (ISO‑8601 string).
6. **Output** exactly as:
   ```
   FINISH([<numeric_value>, "<effectiveDateTime>"])
   ```
   *Example:* `FINISH([6.1, "2023-10-13"])`

**Pattern 2: Fallback / placeholder**
- If the Bundle has `total: 0` or no entries contain a usable value, output a human‑readable placeholder using the existing `missing_observation_placeholder` skill, e.g., `FINISH(["No recent HbA1c result found"])`.

**Pattern 3: Decision hook for re‑ordering**
- After extraction, compare the extracted timestamp to the task’s current time (available in the task context). If the difference exceeds 1 year, automatically issue a POST `ServiceRequest` for the appropriate LOINC code (e.g., `4548-4` for HbA1c) before calling FINISH.

## Example Application
**Task:** "What’s the last HbA1c (hemoglobin A1C) value in the chart for patient S3114648 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1c lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S3114648`
2. Parse the returned Bundle, pick the Observation with the greatest `effectiveDateTime`.
3. Extract `valueQuantity.value` → `6.1` and `effectiveDateTime` → `2023-10-13`.
4. Compare `2023-10-13` to the current context (`2023-11-13`). Difference < 1 year → **no** new order.
5. Return:
   ```
   FINISH([6.1, "2023-10-13"])
   ```

**If the date were older than 1 year**, step 4 would also include:
```json
POST http://localhost:8080/fhir/ServiceRequest {"resourceType":"ServiceRequest","code":{"coding":[{"system":"http://loinc.org","code":"4548-4","display":"HbA1c"}]},"subject":{"reference":"Patient/S3114648"},"status":"active","intent":"order","authoredOn":"2023-11-13T10:15:00+00:00"}
```
followed by the same FINISH output.

## Success Indicators
- FINISH output is an array with a numeric first element and an ISO‑8601 date string as the second element.
- No free‑text narrative appears in the FINISH payload.
- If the date is > 1 year old, a POST `ServiceRequest` is observed before FINISH.

## Failure Indicators
- FINISH contains a single string like `"6.1% on 2023-10-13"`.
- The numeric value is missing or still includes the unit symbol.
- The timestamp is omitted or incorrectly taken from `issued` when `effectiveDateTime` is present.
- No ordering request is made when the date exceeds the 1‑year threshold.
