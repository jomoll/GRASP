---
description: "Normalize lab result units and enforce required string\u2011array output\
  \ format"
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 7
  triggering_sample_ids:
  - task4_27
  - task9_9
  - task5_16
  - task9_27
  - task2_26
  - task5_19
  - task2_16
  - task10_24
  - task9_14
  - task10_21
  update_cycle: 0
tags: []
version: 8
---

# Lab Result Unit Normalization and Formatting

## Pattern Description
Whenever you query a lab Observation, you must return the result as a **single‑element string array** that includes the numeric value **and** the correct clinical unit (e.g., `"3.2 mmol/L"` for potassium, `"1.4 mg/dL"` for magnesium). The unit must match the standard unit for the specific analyte; if the source uses a different unit, convert it before formatting.

## When to Use This Skill
- After any `GET …/Observation` that retrieves a lab value (potassium, magnesium, calcium, etc.).
- When the task expects the answer to be a JSON array of strings (e.g., `FINISH(["3.2 mmol/L"])`).
- When the Observation uses `valueQuantity` (preferred) or `valueString` (fallback).

## Common Failure Patterns
- Returning only the numeric value without a unit (`FINISH(["3.2"])`).
- Returning the unit in a separate field or as part of a nested array.
- Using the wrong unit (e.g., `mmol/L` for magnesium, which should be `mg/dL`).
- Forgetting to wrap the formatted string in an array, resulting in a plain string output.

## Recommended Patterns
**Pattern 1: Extract and normalize the value**
1. From the first entry, read `valueQuantity.value` (number) and `valueQuantity.unit` (string).
2. Identify the analyte by the Observation `code.coding.code` (e.g., `K` for potassium, `MG` for magnesium).
3. If the unit differs from the standard, convert:
   - Potassium: if unit is `mmol/L` keep as‑is; if `mEq/L`, treat as equivalent.
   - Magnesium: if unit is `mmol/L`, convert to `mg/dL` using factor 2.43.
4. Build the formatted string: `"{value} {standardUnit}"` (e.g., `"3.2 mmol/L"`).
5. Return as a JSON array: `FINISH(["3.2 mmol/L"])`.

**Pattern 2: Fallback when valueQuantity is missing**
- If the Observation only provides `valueString`, use it directly **provided it already contains the unit**; otherwise append the standard unit.

## Example Application
**Task:** "What’s the most recent magnesium level of patient S1876702 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1876702&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00&_sort=-date&_count=1`
2. Extract `valueQuantity.value = 0.65` and `valueQuantity.unit = "mmol/L"`.
3. Convert: `0.65 mmol/L × 2.43 = 1.58 mg/dL` → round as needed.
4. Format: `"1.58 mg/dL"`.
5. Return: `FINISH(["1.58 mg/dL"])`.

**CORRECT output:** `FINISH(["1.58 mg/dL"])`
**WRONG output:** `FINISH(["0.65"])` or `FINISH(["0.65 mmol/L"])` for magnesium.

## Success Indicators
- The FINISH array contains exactly one string.
- The string includes both the numeric value and the correct standard unit.
- Unit conversion has been applied when the source unit differs from the standard.

## Failure Indicators
- FINISH output lacks a unit or uses the wrong unit.
- Output is not an array (e.g., plain string).
- The numeric value is unchanged when a conversion was required.
