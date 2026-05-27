---
description: "Extract Observation quantities with unit checks and convert to the task\u2019\
  s requested output unit/format."
name: unit_aware_observation_value_extraction
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 9
  regressions: 1
  triggering_sample_ids:
  - task2_22
  - task10_10
  - task2_26
  - task2_1
  - task9_1
  - task2_17
  - task4_6
  - task10_17
  - task9_11
  - task9_3
  update_cycle: 1
tags:
- observation
- lab-results
- units
- formatting
- conversion
version: 1
---

# Skill Title

## Unit-Aware Observation Value Extraction

## Pattern Description

When I answer a lab-value question from a FHIR Observation, I must not treat `valueQuantity.value` as sufficient by itself. I need to read the measurement unit from `valueQuantity.unit` (or `valueQuantity.code` if needed), compare it to the unit requested in the task, and only then produce the final answer. The reusable lesson is: quantitative lab extraction is a two-part step — numeric magnitude plus unit interpretation.

This matters most when the instruction names a target unit such as `mg/dL`, or when different source units could exist across observations. My behavior should change from "return the latest numeric value" to "return the latest value after unit verification/conversion, in the exact output format requested by the task."

## When to Use This Skill

- When a task asks for the most recent lab value and explicitly says "converted to" a named unit such as `mg/dL`, `mmol/L`, or similar
- When extracting from `Observation.valueQuantity` and the response contains `valueQuantity.unit`, `valueQuantity.code`, or `valueQuantity.system`
- When multiple matching Observations are returned and I must choose the most recent one before answering
- When the required answer format is strict, such as a single number or a sentinel like `-1` if no recent result exists

## Common Failure Patterns

- Reading `valueQuantity.value` but ignoring `valueQuantity.unit`
- Returning the raw number from the latest Observation even though the task requires conversion to a different unit
- Returning a unit-bearing string when the instruction says "answer should be a single number"
- Returning a bare number when the instruction asks for the measurement together with its unit
- Choosing an older Observation without checking `effectiveDateTime` or `issued`
- Returning `"-1 mg/dL"` instead of plain `-1` when the task defines `-1` as the no-result sentinel

## Recommended Patterns

## Pattern 1: inspect the quantitative payload before answering

After I identify candidate Observations, I must select the most recent one using `effectiveDateTime` when present, otherwise `issued` as fallback. Then I must inspect:

- `resource.valueQuantity.value`
- `resource.valueQuantity.unit`
- `resource.valueQuantity.code`

CORRECT: verify `valueQuantity.value = 2.1` and `valueQuantity.unit = "mg/dL"` before answering
WRONG: return `2.1` immediately without checking the unit field

## Pattern 2: convert only if the task requires a target unit

If the task specifies a target unit, I must compare the source unit to that target. If they already match, use the numeric value unchanged. If they differ, convert before answering. Do not invent conversions unless the source and target units are clearly interpretable from the Observation.

For magnesium-style tasks: if the task says "single number converted to mg/dL," the final answer must be the converted numeric value only, not prose.

CORRECT: source `2.1 mg/dL` + task asks for `mg/dL` -> output `2.1`
WRONG: output `"2.1 mg/dL"` when the instruction says a single number only

## Pattern 3: obey the exact final output contract

I must match the requested answer shape exactly:

- If the task says "single number," return just the numeric string/number in the array
- If no qualifying Observation exists in the requested time window, return the exact sentinel requested, such as `-1`
- Do not add interpretation, ranges, or units unless explicitly requested

CORRECT: `FINISH([2.1])`
CORRECT: `FINISH([-1])`
WRONG: `FINISH(["2.1 mg/dL"])` when the task asked for a single number
WRONG: `FINISH(["Latest magnesium is 2.1"])`

## Example Application

**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours? The answer should be a single number converted to a unit of mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step-by-step:**

1. Issue GET with exact parameters: `/Observation?patient=S0674240&code=MG&date=ge2023-11-12T10:15:00Z`
2. From returned `entry[].resource`, sort/select the most recent by `effectiveDateTime`.
3. Extract `valueQuantity.value` and `valueQuantity.unit` from that latest Observation.
4. If `valueQuantity.unit` is already `mg/dL`, use the numeric value directly; otherwise convert to `mg/dL` if possible.
5. Return only the number because the task explicitly asked for a single number.

CORRECT output: `FINISH([2.1])`
WRONG output: `FINISH(["2.1 mg/dL"])`
WRONG output: `FINISH(["Magnesium 2.1, normal"])`

## Success Indicators

- I inspect `valueQuantity.unit` before finishing
- I select the latest Observation using its timestamp, not bundle order alone
- The final answer matches the task’s exact requested format: numeric-only vs value-with-unit vs sentinel
- No extra narration appears in the `FINISH` payload

## Failure Indicators

- I finish with the raw numeric value without ever checking unit fields
- I include units even though the task asked for a single number only
- I omit units when the task explicitly asked for the measurement with unit
- I return a non-sentinel string for no-result cases where the task required `-1`
- I use an older Observation because I failed to compare timestamps
