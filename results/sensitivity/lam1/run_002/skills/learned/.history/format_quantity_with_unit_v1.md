---
description: Extract a lab value, convert it to the required unit (e.g., mg/dL), and
  return the numeric result.
name: format_quantity_with_unit
provenance:
  action: ADD
  epoch: 1
  fixes: 10
  probe_score: 10
  regressions: 0
  triggering_sample_ids:
  - task9_27
  - task10_20
  - task4_15
  - task2_1
  - task8_21
  - task5_17
  - task4_27
  - task2_25
  - task10_17
  - task2_6
  update_cycle: 0
tags:
- quantity
- unit_conversion
- observation
- formatting
version: 1
---

# Format Quantity With Unit

## Pattern Description
You must reliably extract a numeric measurement from a FHIR Observation, ensure it is expressed in the unit required by the task, and return only the converted number (or -1 if no recent measurement exists). This pattern is reusable for any lab or vital‑sign observation where the source unit may differ from the target unit (e.g., mmol/L → mg/dL for magnesium, µmol/L → mg/dL for calcium, etc.). By handling unit conversion centrally, you avoid the common *quantity_unit_mismatch* failure where the agent returns the raw value without conversion.

## When to Use This Skill
- When a task asks for "a single number converted to a unit of mg/dL" (or any other explicit target unit) for a lab Observation.
- When the Observation’s `valueQuantity.unit` differs from the target unit.
- When the task expects `-1` if no recent Observation is found within the specified time window.
- Example triggers:
  - `GET .../Observation?code=MG&patient=Patient/...&date=ge...` and the task description mentions mg/dL.
  - Any similar query for potassium, calcium, etc., where the source unit may be mmol/L.

## Common Failure Patterns
- Returning only the raw numeric value without conversion (e.g., `2.2` mmol/L instead of `4.5` mg/dL).
- Including the unit string in the FINISH payload (e.g., `FINISH(["2.2 mg/dL"])`).
- Using the wrong field (`valueString` or `valueCodeableConcept`) instead of `valueQuantity`.
- Omitting the `-1` fallback when no Observation is present.

## Recommended Patterns
**Pattern 1: Core extraction & conversion**
1. Identify the most recent Observation entry (usually the first entry in the Bundle).
2. Read `valueQuantity.value` and `valueQuantity.unit`.
3. If `unit` matches the required target unit, keep the value unchanged.
4. If `unit` differs, apply the appropriate conversion factor:
   - `mmol/L → mg/dL` : multiply by **2.042** (rounded to two decimals).
   - `µmol/L → mg/dL` : multiply by **0.0001** (example, adjust per substance).
   - Add other conversion tables as needed.
5. Round the final number to a sensible precision (typically two decimal places).
6. Return the result with `FINISH([<number>])`.

**Pattern 2: Fallback when no Observation**
- If the Observation Bundle `total` is `0` or the entry list is empty, immediately `FINISH([-1])`.

**Pattern 3: Output formatting rule**
- Do **not** include any unit string in the FINISH array; the task expects a bare number.
- Ensure the FINISH payload is a JSON array containing a single numeric element (e.g., `FINISH([3.27])`).

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1876702 within last 24 hours? The answer should be a single number converted to a unit of mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S1876702&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Parse the Bundle; assume the first entry contains:
   ```json
   "valueQuantity": { "value": 1.6, "unit": "mmol/L" }
   ```
3. Convert: `1.6 * 2.042 = 3.2672 → 3.27` (round to two decimals).
4. `FINISH([3.27])`

**CORRECT output:** `FINISH([3.27])`
**WRONG output examples:**
- `FINISH(["1.6"])` (no conversion)
- `FINISH(["1.6 mmol/L"])` (unit included)
- `FINISH([-1])` when a valid Observation exists.

## Success Indicators
- The FINISH payload contains a single numeric element.
- The number reflects the correct conversion from the source unit to the target unit.
- When no Observation is found, the output is exactly `FINISH([-1])`.

## Failure Indicators
- The output includes a string or unit (e.g., `"3.27 mg/dL"`).
- The numeric value matches the raw source value without conversion.
- The agent returns an empty array or a placeholder like `""`.
- The agent returns `-1` despite a valid recent Observation.
