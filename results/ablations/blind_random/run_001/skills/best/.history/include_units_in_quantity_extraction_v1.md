---
description: Extract Observation quantities, convert to requested unit, and append
  the unit in the answer
name: include_units_in_quantity_extraction
provenance:
  action: ADD
  blind_select: random
  epoch: 0
  fixes_unused: 3
  probe_score_unused: 4
  regressions_unused: 2
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task5_20
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  update_cycle: 0
tags: []
version: 1
---

# Include Units in Quantity Extraction

## Pattern Description
You must always treat a numeric laboratory result as a *quantity* that includes both a value and a unit.  When a task asks for a lab value (e.g., magnesium, potassium, creatinine) and either mentions a target unit or expects the unit to be part of the answer, extract `valueQuantity.value` **and** `valueQuantity.unit` from the Observation.  If the unit in the resource differs from the unit requested by the task, apply the appropriate conversion before returning the result.  This prevents the common `quantity_unit_mismatch` failure where the agent returns only a raw number.

## When to Use This Skill
- The task asks for a lab or vital‑sign value and mentions a unit (e.g., "converted to mg/dL").
- The task expects the answer to be a single number **with** its unit (e.g., `"2.0 mg/dL"`).
- The Observation resource contains a `valueQuantity` element.
- The task does **not** request a free‑text description of the result.

## Common Failure Patterns
- Returning only `valueQuantity.value` without the unit.
- Using `valueString` instead of `valueQuantity` and losing the unit.
- Ignoring a required conversion (e.g., returning mmol/L when mg/dL is requested).
- Concatenating the unit incorrectly (e.g., `"2.0mg/dL"` without a space).

## Recommended Patterns
**Pattern 1: Core extraction and conversion**
1. Identify the most recent Observation that matches the requested `code` and optional `date` filter.
2. Verify the entry contains `valueQuantity`.
3. Read `valueQuantity.value` (numeric) and `valueQuantity.unit` (string).
4. If the unit matches the task’s requested unit, keep the value unchanged.
5. If the unit differs, look up a conversion table (e.g., `{"MG": {"mmol/L": 2.0, "mg/dL": 1.0}}`).
6. Multiply the numeric value by the conversion factor to obtain the value in the requested unit.
7. Format the answer as a **string**: `<converted_number> <requested_unit>` (single space).

**Pattern 2: Fallback when `valueQuantity` missing**
- If `valueQuantity` is absent but `valueString` exists, attempt to parse a number and unit from the string (regex `([0-9.]+)\s*([a-zA-Z/]+)`).
- Apply conversion as in Pattern 1.
- If parsing fails, treat the observation as unavailable and return `-1` (or the task‑specific sentinel).

**Pattern 3: Formatting the final FINISH call**
- The FINISH payload must be a JSON array containing a **single string** with the number and unit, e.g., `FINISH(["2.0 mg/dL"])`.
- Do **not** wrap the number in additional explanatory text.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0636132 within last 24 hours? The answer should be a single number converted to a unit of mg/dL."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00`.
2. From the returned Bundle, pick the entry with the latest `effectiveDateTime`.
3. Extract `valueQuantity.value = 0.5` and `valueQuantity.unit = "mmol/L"`.
4. Convert: `0.5 mmol/L * 2.0 = 1.0 mg/dL` (magnesium conversion factor 2.0).
5. Build the answer string: `"1.0 mg/dL"`.
6. FINISH(["1.0 mg/dL"]).

**Correct output:** `FINISH(["1.0 mg/dL"])`
**Wrong output:** `FINISH(["1.0"])` (unit missing) or `FINISH(["1.0mm/dL"])` (format wrong).

## Success Indicators
- The FINISH array contains exactly one string.
- The string matches the pattern `<number> <unit>` where the unit is exactly the one requested by the task.
- The numeric value reflects any required conversion.

## Failure Indicators
- The answer string lacks a space before the unit.
- The unit does not match the requested unit (e.g., "mmol/L" instead of "mg/dL").
- The numeric value is unchanged when a conversion was required.
- The FINISH payload contains extra explanatory text or a JSON number instead of a string.

---
*Tags:* ["quantity", "unit", "observation", "conversion", "lab"]
