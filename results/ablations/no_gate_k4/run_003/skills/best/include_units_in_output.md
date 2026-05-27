---
description: Append the correct unit to extracted observation values and perform required
  unit conversion
name: include_units_in_output
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Include Units In Output

## Pattern Description
You must always return laboratory observation results with an explicit unit. After locating the most recent Observation that matches the requested code and time window, extract both `valueQuantity.value` and `valueQuantity.unit`. If the unit in the source data differs from the unit required by the task, convert the numeric value accordingly and replace the unit with the required one. This prevents downstream consumers from having to guess the measurement scale and eliminates the common *quantity_unit_missing* failure.

## When to Use This Skill
- When a task asks for a lab value (e.g., magnesium, potassium, creatinine) and the expected answer format includes a unit (e.g., "mg/dL").
- When the FHIR Observation uses `valueQuantity` with a unit that is not the one requested by the user.
- When the task explicitly states that the answer should be a single number **converted to** a specific unit.

## Common Failure Patterns
- Returning only the numeric value (e.g., `FINISH(["2.0"])`) without the unit.
- Returning the raw unit from the source (e.g., `mmol/L`) when the task expects `mg/dL`.
- Concatenating the unit to the value inside a JSON array as a single string instead of returning a structured "value unit" string.

## Recommended Patterns
**Pattern 1: Extract and Convert**
1. Perform the GET request for the Observation with the appropriate `code`, `patient`, and date range.
2. From the first entry in the Bundle, read:
   - `valueQuantity.value` → `raw_value`
   - `valueQuantity.unit` → `raw_unit`
3. Determine the target unit required by the task (e.g., `mg/dL`).
4. If `raw_unit` differs from the target unit, apply the correct conversion:
   - Magnesium: `mg/dL = raw_value * 2.43` when `raw_unit` is `mmol/L`.
   - Potassium: `mg/dL = raw_value * 39.1` when `raw_unit` is `mmol/L`.
   - (Add other common conversions as needed.)
5. Round the converted value to one decimal place unless the task specifies otherwise.
6. Construct the output string as `"{value} {unit}"` (e.g., `"2.0 mg/dL"`).
7. Return with `FINISH(["{value} {unit}"])`.

**Pattern 2: Fallback When No Observation Found**
- If the Bundle `total` is `0` or the entry list is empty, return the sentinel value defined by the task (e.g., `-1` or a descriptive message) **with the unit if the task expects one**.

**Pattern 3: Validation Before Finish**
- Verify that the final string matches the regex `^\d+(\.\d+)?\s+[a-zA-Z/]+$`.
- If the check fails, log a warning and fall back to returning only the numeric value with a comment for debugging.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0636132 within last 24 hours? The answer should be a single number converted to a unit of mg/dL."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Bundle contains an entry with:
   - `valueQuantity.value = 0.82`
   - `valueQuantity.unit = "mmol/L"`
3. Convert: `0.82 * 2.43 = 1.99` → round to `2.0`.
4. Build output string: `"2.0 mg/dL"`.
5. FINISH(["2.0 mg/dL"]).

**Correct output:** `FINISH(["2.0 mg/dL"])`
**Wrong output:** `FINISH(["2.0"])`

## Success Indicators
- The FINISH payload contains a string that ends with the expected unit (e.g., `mg/dL`).
- Numeric value matches the converted value when a conversion was required.
- No extra surrounding text or JSON objects are present.

## Failure Indicators
- FINISH returns only a number without a unit.
- The unit in the output does not match the unit requested by the task.
- The conversion factor was not applied when the source unit differs from the target.
- The output string fails the validation regex.
