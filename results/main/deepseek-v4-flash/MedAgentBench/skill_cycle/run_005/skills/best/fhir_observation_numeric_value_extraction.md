---
description: Extract numeric value from FHIR Observation valueQuantity.value
name: fhir_observation_numeric_value_extraction
provenance:
  action: ADD
  epoch: 1
  fixes: 7
  probe_score: 8
  regressions: 0
  triggering_sample_ids:
  - task3_14
  - task10_20
  - task10_13
  - task4_26
  - task4_20
  - task10_16
  - task5_17
  - task10_15
  - task2_25
  - task9_3
  update_cycle: 0
tags: []
version: 1
---

# FHIR Observation Numeric Value Extraction

## Pattern Description

When a FHIR Observation search returns results, the numeric lab value is stored in `valueQuantity.value` as a JSON number, not in `valueString` or as a concatenated string with units. You must extract this numeric value directly and return it as a number (not a string) in the FINISH call. Do not include units, reference ranges, or explanatory text in the value output unless the task explicitly asks for them.

This skill applies to all lab value extraction tasks (magnesium, potassium, HbA1C, etc.) where the expected answer is a single numeric value. The agent must parse the FHIR response JSON correctly, locate the most recent observation by `effectiveDateTime`, and extract the `valueQuantity.value` field.

## When to Use This Skill

- When a GET /Observation returns a bundle with one or more entries and the task asks for a numeric lab value
- When constructing a FINISH call that should contain only a number (e.g., `FINISH([2.0])`) not a string (e.g., `FINISH(["2.0"])`)
- When the task specifies the answer should be a single number, possibly with a fallback value like -1
- When the task asks for a lab value and a decision (e.g., "if low, order replacement") — extract the numeric value first, then apply the decision logic

## Common Failure Patterns

- Returning `["2.0"]` (string) instead of `[2.0]` (number) — the FINISH array must contain a number, not a string
- Returning `["2.0 mg/dL"]` — units concatenated with the value
- Returning verbose sentences like `["The patient's magnesium level is 2.0 mg/dL"]` when only the number is expected
- Extracting `valueString` or `valueQuantity.unit` instead of `valueQuantity.value`
- Failing to sort observations by `effectiveDateTime` to get the most recent one when multiple entries exist

## Recommended Patterns

**Pattern 1: Extract numeric value from the most recent observation**
1. Parse the FHIR bundle JSON response
2. Access the `entry` array; if empty, return the fallback value (e.g., -1)
3. Sort entries by `resource.effectiveDateTime` descending to get the most recent
4. Access `resource.valueQuantity.value` — this is the numeric value
5. Return the number directly in the FINISH array: `FINISH([value])`

CORRECT: `FINISH([2.0])`
WRONG:   `FINISH(["2.0"])`
WRONG:   `FINISH(["2.0 mg/dL"])`

**Pattern 2: Handle no results**
If `total` is 0 or `entry` is empty/undefined, return the fallback value specified in the task (often -1).

CORRECT: `FINISH([-1])`
WRONG:   `FINISH(["No results found"])`

**Pattern 3: When task requires both value and decision**
Extract the numeric value first, then apply the threshold check. Return the value and decision in the format specified by the task (e.g., `"3.8, no replacement needed"`).

## Example Application

**Task:** "What's the most recent magnesium level of the patient S0636132 within last 24 hours? The answer should be a single number converted to a unit of mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step-by-step:**

1. Issue GET with exact parameters:
   `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`

2. Parse the response bundle. The `entry` array contains observations. Sort by `resource.effectiveDateTime` descending.

3. For the most recent entry, extract:
   - `resource.valueQuantity.value` → `2.0` (number)
   - Do NOT use `resource.valueQuantity.unit` or `resource.valueString`

4. Construct the FINISH call:
   CORRECT output: `FINISH([2.0])`
   WRONG output:   `FINISH(["2.0"])`
   WRONG output:   `FINISH(["2.0 mg/dL"])`

## Success Indicators

- FINISH array contains a bare number (e.g., `[2.0]`) not a string
- The number matches the `valueQuantity.value` from the most recent observation
- When no results, FINISH contains the fallback value (e.g., `[-1]`)
- When task requires both value and decision, the output contains the numeric value followed by the decision in the expected format

## Failure Indicators

- FINISH array contains a string like `["2.0"]` instead of a number
- FINISH contains units or explanatory text when only the number is expected
- The wrong observation is selected (not the most recent by `effectiveDateTime`)
- The agent returns a verbose sentence instead of the requested format
- The agent returns `null` or `undefined` because it accessed the wrong field
