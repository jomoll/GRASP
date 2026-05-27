---
description: Extract numeric Observation values correctly and convert to the unit
  required by the task before FINISH.
name: observation_quantity_extraction_with_unit_conversion
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task5_19
  - task5_3
  - task10_10
  - task10_12
  - task9_1
  - task2_26
  - task9_20
  - task4_23
  update_cycle: 1
tags:
- observation
- labs
- quantity-extraction
- unit-conversion
version: 1
---

# Observation Quantity Extraction With Unit Conversion

## Pattern Description

When a task asks for a lab or vital result as a single number, you must read the Observation's quantitative fields carefully and return the numeric value in the unit the task explicitly requests. The reusable pattern is: query the Observation, identify the most recent matching entry, extract `valueQuantity.value` and `valueQuantity.unit`, then convert if needed before answering.

This skill matters when the task wording includes a target unit such as "convert to mg/dL" or when the charted Observation may be stored in a different unit than the requested output. The behavior change is: do not stop after finding a plausible number; verify the unit, perform conversion if necessary, and return only the converted numeric result.

## When to Use This Skill

- When a lab-result question says the answer should be a single number in a specific unit
- When a GET `/Observation?...` returns entries with `valueQuantity`
- When the task says "most recent" or "last" result and there may be multiple matching Observations
- When returning `-1` depends on result availability, not on inability to interpret the unit
- When magnesium, potassium, HbA1C, or other lab tasks ask for a numeric result without narrative text

## Common Failure Patterns

- Returning `valueQuantity.value` without checking `valueQuantity.unit`
- Returning the charted number in the wrong unit when the task requested conversion to another unit
- Using `valueString` or display text when `valueQuantity.value` is available
- Returning `"1.6"` or `"1.6 mg/dL"` instead of a numeric output like `[1.6]`
- Choosing an arbitrary matching Observation instead of the most recent by `effectiveDateTime` or equivalent timing field
- Returning `-1` just because the unit differs from the requested unit

## Recommended Patterns

**Pattern 1: extract the quantitative result from the right field**

After you retrieve candidate Observations, inspect the chosen resource in this order:
1. `valueQuantity.value`
2. `valueQuantity.unit`
3. timing field used to determine recency: typically `effectiveDateTime` (or the task-specific equivalent if present)

CORRECT: extract `1.6` from `valueQuantity.value`
WRONG:   extract `"1.6 mg/dL"` by concatenating value and unit

If `valueQuantity` is absent and only `valueString` exists, only use it if the task truly expects free text. For single-number lab tasks, prefer `valueQuantity`.

**Pattern 2: convert to the requested unit before answering**

If the task names a required unit, compare it against `valueQuantity.unit`. If they differ, convert before FINISH. Do not assume the stored value is already in the requested unit.

For magnesium tasks requesting mg/dL:
- If `valueQuantity.unit` is `mg/dL`, return `valueQuantity.value` directly.
- If `valueQuantity.unit` is `mmol/L`, convert using magnesium's molar mass: `mg/dL = mmol/L × 2.43`.
- Round reasonably to match chart precision if needed, but keep the answer numeric.

**Pattern 3: output only the final numeric answer**

Return the final value as a number inside the expected output array.

CORRECT: `FINISH([1.6])`
WRONG:   `FINISH(["1.6"])`
WRONG:   `FINISH(["Magnesium is 1.6 mg/dL"])`
WRONG:   `FINISH([-1])` when an Observation exists but only unit conversion was needed

## Example Application

**Task:** "What's the most recent magnesium level of the patient S1876702 within last 24 hours? The answer should be a single number converted to mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step-by-step:**

1. Issue GET with exact parameters:
   `GET /Observation?patient=S1876702&code=MG&date=ge2023-11-12T10:15:00Z`
2. From the returned Bundle, identify the most recent matching entry by `effectiveDateTime`.
3. Extract `valueQuantity.value` and `valueQuantity.unit` from that Observation.
4. If unit is already `mg/dL`, use the number directly. If unit is `mmol/L`, compute `value * 2.43`.
5. Return only the numeric result.

CORRECT output: `FINISH([1.6])`
WRONG output:   `FINISH(["1.6"])`
WRONG output:   `FINISH(["1.6 mg/dL"])`
WRONG output:   `FINISH([-1])` when a recent magnesium Observation exists

## Success Indicators

- The agent inspects both `valueQuantity.value` and `valueQuantity.unit`
- The final answer matches the unit explicitly requested in the task
- The final output is a bare number, not text with units
- `-1` is used only when no qualifying Observation exists in the requested time window

## Failure Indicators

- The answer is numerically plausible but reflects the wrong unit
- The output includes units or explanatory prose instead of a number
- The agent ignores `valueQuantity.unit`
- The agent returns `-1` despite a recent Observation being present
- The chosen Observation is not the most recent matching result
