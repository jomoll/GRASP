---
description: Extract only the numeric lab value (with unit) from Observation resources
  and return it as a scalar
name: value_only_extraction
provenance:
  action: ADD
  epoch: 1
  no_gate: true
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task1_27
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_26
  - task4_6
  - task4_27
  update_cycle: 0
tags:
- extraction
- lab
- value_only
version: 1
---

# Value‑Only Extraction for Lab Observations

## Pattern Description
You must isolate the raw measurement from a FHIR Observation and return **only** that measurement (optionally with its unit) as a scalar string. The goal is to separate data extraction from any explanatory wording so downstream decision logic (e.g., conditional ordering) can operate on a clean value. This pattern applies to any laboratory Observation where the result is stored in `valueQuantity` (e.g., potassium, magnesium, HbA1c) and the task expects a single value rather than a narrative sentence.

## When to Use This Skill
- When a task asks for "the most recent potassium level", "the last magnesium level", or any similar lab value and the expected answer is a scalar (e.g., `4.7 mmol/L`).
- After you have performed a GET request to `/Observation` with the appropriate `code` and `patient` (and optional date range) and received a Bundle of results.
- Before any conditional logic that compares the lab value to a threshold.

## Common Failure Patterns
- Returning a full sentence such as `"No potassium replacement needed; level 4.7 mmol/L is above threshold."`
- Returning an array of strings instead of a single scalar (e.g., `FINISH(["4.7 mmol/L"])`).
- Concatenating the unit to the numeric value inside `valueQuantity.value` (e.g., storing `"4.7 mmol/L"` in `valueQuantity.value`).
- Using `valueString` or other free‑text fields instead of `valueQuantity` for numeric labs.

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. Identify the most recent Observation entry in the Bundle (largest `effectiveDateTime`).
2. Verify the entry contains `valueQuantity`.
3. Extract `valueQuantity.value` as a number.
4. Extract `valueQuantity.unit` (or `valueQuantity.code` if unit is coded).
5. Construct a scalar string `"{value} {unit}"` (e.g., `"4.7 mmol/L"`).
6. Call `FINISH("{value} {unit}")`.

**CORRECT**: `FINISH("4.7 mmol/L")`
**WRONG**: `FINISH("Potassium is 4.7 mmol/L, no replacement needed.")`

**Pattern 2: Fallback when no suitable Observation is found**
- If the Bundle `total` is 0 or none of the entries contain a valid `valueQuantity`, call `FINISH("-1")` (or the task‑specific placeholder) to signal missing data.

**Pattern 3: Formatting guard**
- Ensure the FINISH payload is a plain string, not an array or JSON object. Use the existing `verify_before_finish` skill to enforce scalar output after this step.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3228213`
2. Receive Bundle, locate the entry with the latest `effectiveDateTime`.
3. Extract `valueQuantity.value = 4.7` and `valueQuantity.unit = "mmol/L"`.
4. `FINISH("4.7 mmol/L")`.
5. Downstream `conditional_lab_result_ordering` will compare `4.7` to the low‑potassium threshold.

**CORRECT output:** `FINISH("4.7 mmol/L")`
**WRONG output:** `FINISH("No potassium replacement needed; level 4.7 mmol/L is above threshold.")`

## Success Indicators
- The FINISH call contains a single string matching the pattern `<number> <unit>` (e.g., `"3.5 mmol/L"`).
- No extra explanatory text, commas, or surrounding brackets are present.
- Subsequent conditional ordering logic receives a numeric value it can compare.

## Failure Indicators
- FINISH returns a sentence, list, or JSON object.
- The unit is missing or concatenated incorrectly (e.g., `"4.7mmol/L"` without a space when the task expects a space).
- The agent proceeds to ordering decisions based on a non‑numeric string, causing threshold checks to fail.

---
*Use this skill whenever a lab‑value answer is required; combine it with `lab_observation_query_before_finish` and `conditional_lab_result_ordering` for full end‑to‑end handling.*
