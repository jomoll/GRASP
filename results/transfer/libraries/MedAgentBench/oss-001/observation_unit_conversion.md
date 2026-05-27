---
description: Convert observation values to the unit requested by the task before FINISH
name: observation_unit_conversion
provenance:
  action: ADD
  epoch: 6
  fixes: 7
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task3_12
  - task4_20
  - task8_29
  - task10_12
  - task3_10
  update_cycle: 1
tags:
- unit_conversion
- observation
- lab_values
version: 1
---

# Observation Unit Conversion for Lab Values

## Pattern Description
You must ensure that any numeric lab or observation result you return matches the unit explicitly requested in the task description. Many lab results are stored in FHIR with a `valueQuantity.unit` that differs from the unit the clinician expects (e.g., mmol/L vs mg/dL). This skill extracts the original value and unit, determines whether a conversion is needed, applies the correct factor, and returns the converted number together with the original timestamp.

## When to Use This Skill
- When a task asks for a lab value **and specifies a target unit** (e.g., "convert to mg/dL", "in mg/dL", "as mg/dL").
- When the Observation resource contains `valueQuantity.value` **and** `valueQuantity.unit` that is *different* from the requested unit.
- Applies to any numeric Observation (e.g., magnesium, potassium, calcium, glucose, creatinine, etc.).

## Common Failure Patterns
- Returning the raw `valueQuantity.value` without checking `valueQuantity.unit`.
- Concatenating the numeric value with its original unit (e.g., `"2.0 mmol/L"`).
- Ignoring the unit conversion factor, leading to clinically incorrect numbers.
- Omitting the unit entirely and returning a plain number that is in the wrong scale.

## Recommended Patterns
**Pattern 1: Detect required unit and perform conversion**
1. Parse the task description for a unit keyword (e.g., `mg/dL`, `mmol/L`).
2. From the Observation bundle, locate the first entry with `resourceType":"Observation"` that matches the requested `code`.
3. Extract `valueQuantity.value` **as a number** and `valueQuantity.unit` **as a string**.
4. If the extracted unit matches the required unit, use the value unchanged.
5. If the units differ, look up the conversion factor in the table below and compute:
   ```
   converted = original_value * factor
   ```
6. Return `FINISH([converted, "<effectiveDateTime>"])` where the datetime is taken from `effectiveDateTime` or `issued`.

**Conversion table (common labs)**
| From → To | Factor (multiply) |
|-----------|-------------------|
| mmol/L → mg/dL (Mg) | 2.43 |
| mmol/L → mg/dL (K)  | 39.1 |
| mmol/L → mg/dL (Ca) | 4.0 |
| mg/dL → mmol/L (Mg) | 0.411 |
| mg/dL → mmol/L (K)  | 0.0256 |
| mg/dL → mmol/L (Ca) | 0.25 |
| µmol/L → mg/dL (Cr) | 0.0113 |
| mg/dL → µmol/L (Cr) | 88.4 |
*Add additional rows as needed for other analytes.*

**Pattern 2: Fallback when unit cannot be determined**
- If the Observation lacks `valueQuantity.unit`, assume the unit is the one requested **only if** the task explicitly says "as a plain number"; otherwise, return `FINISH([-1])` to signal missing data.

**Pattern 3: Formatting the final output**
- Always output a JSON‑compatible list: `[numeric_value, "ISO‑8601 datetime"]`.
- Do **not** include the unit string in the list; the conversion already aligns the number with the requested unit.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0636132 within last 24 hours? Return the value in **mg/dL**."

**Step‑by‑step:**
1. Issue GET: `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00+00:00`.
2. Find the Observation entry; suppose it contains:
   ```json
   "valueQuantity": { "value": 1.0, "unit": "mmol/L" },
   "effectiveDateTime": "2023-11-13T00:36:00+00:00"
   ```
3. Required unit = `mg/dL`. Convert: `1.0 * 2.43 = 2.43`.
4. Return: `FINISH([2.43, "2023-11-13T00:36:00+00:00"])`.

## Success Indicators
- The FINISH payload contains a numeric value that matches the unit requested in the task.
- The datetime is a valid ISO‑8601 string from the Observation.
- No unit suffix appears in the numeric element.

## Failure Indicators
- FINISH returns a string like `"2.0 mmol/L"` or includes the unit in the list.
- The numeric value is unchanged despite a unit mismatch.
- The output list is missing the datetime or contains `-1` when a valid observation exists.
