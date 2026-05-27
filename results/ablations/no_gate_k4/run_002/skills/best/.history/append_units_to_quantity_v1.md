---
description: Append the correct unit to numeric lab values extracted from Observation
  resources
name: append_units_to_quantity
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
  - task1_15
  - task3_14
  update_cycle: 0
tags: []
version: 1
---

# Append Units to Quantity Values in Observation Results

## Pattern Description
You must always return a lab value together with its proper unit when the task description explicitly asks for a value "converted to a unit of …" or when the clinical context expects a unit (e.g., mg/dL for serum magnesium, mmol/L for potassium). The agent should extract the numeric part from `Observation.valueQuantity.value` and the unit from `Observation.valueQuantity.unit`. If the unit field is empty, fall back to a hard‑coded mapping based on the observation code (e.g., `MG` → `mg/dL`, `K` → `mmol/L`). The final answer must be a single string that combines the number and unit separated by a space.

## When to Use This Skill
- When a task asks for the most recent value of a lab test (e.g., magnesium, potassium, calcium) and explicitly mentions the desired unit.
- When the instruction says "answer should be a single number converted to a unit of …".
- When constructing a list output for a scalar lab value (e.g., `FINISH(["2.0 mg/dL"])`).

## Common Failure Patterns
- Returning only the numeric value without the unit (e.g., `FINISH(["2.0"])`).
- Using the wrong field such as `valueString` or concatenating the unit incorrectly (e.g., `"2.0mg/dL"` without a space).
- Ignoring an empty `valueQuantity.unit` and failing to apply the fallback mapping, resulting in a missing unit.

## Recommended Patterns
**Pattern 1: Primary extraction with unit**
1. Locate the most recent `Observation` entry that matches the requested `code` and time window.
2. Read `valueQuantity.value` → numeric part.
3. Read `valueQuantity.unit` → unit string.
4. If `unit` is non‑empty, format `"{value} {unit}"`.
5. Return the formatted string inside a JSON list.

**CORRECT**: `valueQuantity.value = 2.0`, `valueQuantity.unit = "mg/dL"` → `FINISH(["2.0 mg/dL"])`
**WRONG**: `FINISH(["2.0"])` or `FINISH(["2.0mg/dL"])`

**Pattern 2: Fallback mapping when unit is missing**
1. If `valueQuantity.unit` is empty or null, look up the observation `code` (e.g., `MG`, `K`, `CA`).
2. Use a predefined map:
   - `MG` → `mg/dL`
   - `K` → `mmol/L`
   - `CA` → `mg/dL`
   - *(extend as needed)*
3. Apply the same formatting as in Pattern 1.

**Pattern 3: Validation before finishing**
1. Verify that the final string contains a space separating a numeric token and a known unit.
2. If validation fails, raise a fallback error or request a re‑query.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0636132 within last 24 hours?"

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`
2. From the returned bundle, pick the entry with the latest `effectiveDateTime`.
3. Extract `valueQuantity.value = 2.0` and `valueQuantity.unit = "mg/dL"`.
4. Format as `"2.0 mg/dL"`.
5. `FINISH(["2.0 mg/dL"])`.

**If the unit field were empty:**
- Use the fallback map: `code "MG"` → `"mg/dL"`.
- Produce the same formatted output.

## Success Indicators
- The FINISH payload contains a single string with a numeric value followed by a space and the correct unit (e.g., `"1.8 mg/dL"`).
- The unit matches the clinical expectation for the requested lab (magnesium → mg/dL, potassium → mmol/L, etc.).

## Failure Indicators
- The output list contains only the number without a unit.
- The unit is misspelled, missing, or concatenated without a space.
- The wrong unit is attached (e.g., mg/L for magnesium).

---

**Tags:** ["unit_handling","observation_extraction","lab_results"]
