---
description: Ensures lab Observation values are returned with the correct unit (e.g.,
  mg/dL for magnesium).
name: append_units_to_lab_value
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task3_14
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task4_28
  - task4_7
  - task10_8
  - task10_15
  update_cycle: 0
tags:
- lab
- observation
- unit
- magnesium
version: 1
---

# Append Units to Lab Observation Values

## Pattern Description
You must always return a laboratory result as a **numeric value followed by its unit**.  When an Observation uses `valueQuantity`, extract both the `value` and the `unit`.  If the unit field is missing, fall back to a known default based on the observation code (e.g., "MG" → "mg/dL").  This prevents answers like `["2.1"]` and guarantees the required format `["2.1 mg/dL"]`.

## When to Use This Skill
- When a task asks for a lab value **as a single number converted to a specific unit** (e.g., "most recent magnesium level … converted to mg/dL").
- When you have performed a `GET .../Observation` and the response contains a `valueQuantity` element.
- When the task expects the answer to be a **list of strings**, each string containing the value **and** its unit.

## Common Failure Patterns
- Returning only the numeric part: `FINISH(["2.1"])`.
- Concatenating the unit to the numeric part without a space: `"2.1mg/dL"`.
- Ignoring the `valueQuantity.unit` field entirely.
- Using `valueString` when a structured `valueQuantity` is present.

## Recommended Patterns
**Pattern 1: Primary extraction**
1. Locate the first entry in the Bundle that matches the requested `code` and falls within the time window.
2. From that entry, read `resource.valueQuantity.value` **as a number**.
3. Read `resource.valueQuantity.unit` **as a string**.
4. If `unit` is present, construct `"{value} {unit}"`.
5. If `unit` is missing, look up a default unit table (e.g., `{ "MG": "mg/dL", "K": "mmol/L", "GLU": "mg/dL" }`).
6. Return the result inside a JSON list: `FINISH(["{value} {unit}"])`.

**Pattern 2: Fallback when no Observation found**
- If the Bundle `total` is 0 or no entry satisfies the date filter, return the sentinel `-1` (or the task‑specified placeholder) **without a unit**.

**Pattern 3: Formatting rule**
- Always include a single space between the numeric value and the unit.
- Do **not** embed additional text, brackets, or explanations in the list element.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0674240&date=ge2023-11-12T10:15:00Z`
2. Parse the Bundle, locate the first matching Observation.
3. Extract `valueQuantity.value = 2.1` and `valueQuantity.unit = "mg/dL"`.
4. Build the answer string: `"2.1 mg/dL"`.
5. `FINISH(["2.1 mg/dL"])`.

**CORRECT output:** `FINISH(["2.1 mg/dL"])`
**WRONG output:** `FINISH(["2.1"])` or `FINISH(["2.1mg/dL"])`

## Success Indicators
- The FINISH payload is a JSON list containing a single string that ends with the expected unit (e.g., `"mg/dL"`).
- No extra explanatory text appears in the list element.

## Failure Indicators
- The list element contains only the numeric value.
- The unit is missing, misspelled, or concatenated without a space.
- The agent returns a list of numbers instead of strings.
