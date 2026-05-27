---
description: Return extracted lab values as plain numbers (or sentinel) instead of
  descriptive sentences
name: answer_numeric_format
provenance:
  action: ADD
  epoch: 0
  fixes: 6
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_5
  - task8_23
  - task9_8
  - task8_3
  - task9_14
  - task10_20
  - task10_8
  - task9_3
  - task9_9
  - task10_24
  update_cycle: 0
tags:
- numeric_extraction
- lab_result_format
version: 1
---

# Answer Numeric Format

## Pattern Description
You must extract quantitative lab results (e.g., magnesium, potassium, HbA1c) from a FHIR Observation bundle and return the value **as a raw number** (or a predefined sentinel such as `-1`) inside a JSON array. The task description often specifies the required unit (e.g., mg/dL) and may require a simple threshold check before ordering medication. Embedding the number in a sentence causes the `answer_format_wrong_type` failure.

## When to Use This Skill
- When a task asks for "the most recent magnesium level" or "last HbA1c value" and expects a numeric answer.
- When the instruction says "return -1 if no recent measurement is available".
- When the task includes a conditional order based on a numeric threshold (e.g., "if magnesium < 1.5 mg/dL, order replacement").

## Common Failure Patterns
- Returning `FINISH(["Magnesium level 2.2 mg/dL is within normal range."])` instead of `FINISH([2.2])`.
- Including units or explanatory text inside the array element.
- Using a string sentinel like `"none"` when the spec requires `-1`.
- Extracting `valueString` or `valueQuantity.unit` together with the numeric value.

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. Identify the Observation bundle returned by the GET request.
2. Filter entries where `resource.resourceType == "Observation"` and `code.coding` contains the requested LOINC/code (e.g., `MG`).
3. If a date range is required, keep only observations whose `effectiveDateTime` falls within the window.
4. Sort the remaining observations by `effectiveDateTime` descending and pick the first (most recent).
5. Extract the numeric value:
   - Prefer `valueQuantity.value` (already a number).
   - If the observation uses `valueQuantity.unit` different from the required unit, convert using a simple factor (e.g., `mmol/L` → `mg/dL` for magnesium: multiply by 2.0).
6. Return the number inside a JSON array: `FINISH([<number>])`.

**Pattern 2: Sentinel fallback**
- If no observation satisfies the filter (no recent result), return the sentinel defined by the task (commonly `-1`): `FINISH([-1])`.

**Pattern 3: Formatting rule**
- Do **not** wrap the number in quotes, do not append units, and do not add explanatory text.
- The final output must be a JSON array with a single numeric element.

## Example Application
**Task:** "What’s the most recent magnesium level of patient S1876702 within last 24 hours? Return -1 if unavailable."

**Step‑by‑step:**
1. GET `.../Observation?code=MG&patient=S1876702&date=ge2023-11-12T10:15:00`.
2. Parse the bundle, keep entries with `effectiveDateTime >= 2023-11-12T10:15:00`.
3. Sort by `effectiveDateTime` descending; the first entry has `valueQuantity.value = 1.6` and `unit = "mg/dL"`.
4. No conversion needed; output `FINISH([1.6])`.

**Correct output:** `FINISH([1.6])`
**Wrong output:** `FINISH(["Magnesium 1.6 mg/dL"] )`

## Success Indicators
- The FINISH call contains a JSON array with a single numeric element (e.g., `[2.2]` or `[-1]`).
- No surrounding quotation marks or text are present.
- The number matches the most recent observation value after any required unit conversion.

## Failure Indicators
- The FINISH payload includes a string or sentence.
- Units are concatenated to the number (e.g., `"2.2 mg/dL"`).
- The sentinel is missing or of the wrong type (e.g., `"-1"`).
- The agent selects an older observation outside the required time window.
