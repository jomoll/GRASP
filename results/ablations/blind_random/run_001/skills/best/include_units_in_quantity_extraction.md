---
description: Make quantity extraction return a plain string instead of a JSON array
name: include_units_in_quantity_extraction
provenance:
  action: MODIFY
  blind_select: random
  epoch: 2
  fixes_unused: 7
  parent_version: 1
  probe_score_unused: -6
  regressions_unused: 7
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task4_27
  - task8_26
  - task5_19
  - task5_3
  - task4_20
  - task10_10
  - task4_15
  - task10_13
  update_cycle: 1
tags: []
version: 2
---

# include_units_in_quantity_extraction

## Pattern Description
You must extract a numeric value and its unit from an Observation and return the result as a plain string (e.g. `"1.8 mg/dL"`).  The surrounding FINISH call should contain the string directly, not an array wrapper.  This keeps answer formatting consistent across all numeric‑unit queries.

## When to Use This Skill
- When a task asks for the most recent value of a lab/observation (e.g., magnesium, potassium, glucose) **and** explicitly requests the value with its unit.
- When the task expects a single string answer (no surrounding JSON array) such as `FINISH("1.8 mg/dL")`.
- When the Observation resource contains the value in `valueQuantity` (or `valueString` that can be parsed) and the unit is either in `valueQuantity.unit` or must be appended from a known conversion.

## Common Failure Patterns
- Returning `FINISH(["1.8 mg/dL"])` – the answer is wrapped in an array.
- Concatenating the unit to the numeric value **inside** the array (e.g., `FINISH(["1.8 mg/dL"])`).
- Omitting the unit or returning the raw `valueQuantity` object instead of a formatted string.

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Perform the GET request for the Observation with the appropriate code and date filter.
2. From the first entry in the Bundle, locate `resource.valueQuantity`.
   - `value = resource.valueQuantity.value`
   - `unit = resource.valueQuantity.unit`
3. If the task specifies a different target unit, convert `value` accordingly (use a conversion table).
4. Build the answer string: `answer = f"{value} {unit}"`.
5. Call `FINISH(answer)` **without** surrounding brackets.

**CORRECT**: `FINISH("1.8 mg/dL")`
**WRONG**: `FINISH(["1.8 mg/dL"])`

**Pattern 2: Fallback when `valueQuantity` missing**
- If the Observation uses `valueString` (e.g., "118/77 mmHg"), return that string directly via `FINISH(valueString)`.
- If no suitable value is found, return the sentinel `-1` (numeric) via `FINISH(-1)`.

**Pattern 3: Validation before finishing**
- Verify that `answer` is a string containing at least one digit and a unit.
- If validation fails, log a warning and fall back to `FINISH(-1)`.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S6227720 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S6227720&date=ge2023-11-12T10:15:00+00:00`
2. Parse the Bundle, take the first entry's `resource.valueQuantity` → `{ "value": 1.8, "unit": "mg/dL" }`.
3. `answer = f"{value} {unit}"` → `"1.8 mg/dL"`.
4. `FINISH(answer)` → `FINISH("1.8 mg/dL")`.

**CORRECT output:** `FINISH("1.8 mg/dL")`
**WRONG output:** `FINISH(["1.8 mg/dL"])`

## Success Indicators
- The FINISH call contains a plain string (e.g., `"2.0 mg/dL"`) with no surrounding brackets.
- The string includes both a numeric component and the expected unit.
- No array structures appear in the final answer payload.

## Failure Indicators
- FINISH is called with an array containing the string.
- The unit is missing or the answer is returned as a raw JSON object.
- Validation step logs a unit‑missing warning but still returns an array.
