---
description: Enforce correct 'no result found' value formatting for lab observation
  queries when no result is present.
name: no_result_found_value_format_for_lab_observations
provenance:
  action: ADD
  epoch: 1
  fixes: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task10_10
  - task4_28
  - task10_12
  - task10_16
  - task10_21
  update_cycle: 1
tags:
- lab
- observation
- formatting
- sentinel
- missing-data
version: 1
---

# No Result Found Value Format for Lab Observations

## Pattern Description
When querying for a specific lab observation (such as HbA1C or magnesium) and no result is found, you must return a standardized 'no result found' value in the required output format, rather than a generic scalar like `[-1]`. This ensures downstream consumers and evaluators can reliably interpret the absence of data, and prevents ambiguity or misinterpretation.

This pattern applies to any lab value query where the task explicitly specifies a required format for missing results (e.g., "return -1 if not available" or "return [] if no result found"). The agent must actively check for the absence of results and output the correct sentinel value.

## When to Use This Skill
- When a GET /Observation returns a Bundle with `total: 0` or an empty `entry` array.
- When the task instruction specifies a required output for missing lab values (e.g., "return -1 if not available", "return [] if no result found").
- When extracting the most recent value for labs like HbA1C, magnesium, potassium, etc., and no result is present.

## Common Failure Patterns
- Returning `[-1]` when the required output is `[]` or another sentinel value.
- Returning `["No result found"]` or a string instead of the required scalar or empty array.
- Failing to check the `total` field or `entry` array in the Bundle response.
- Returning a default value (e.g., `0`) not specified by the task.

## Recommended Patterns

**Pattern 1: core strategy or rule**
- After issuing a GET /Observation, inspect the Bundle response:
  - If `total` is 0 or `entry` is missing/empty, no result is found.
- Before calling FINISH, check the task instruction for the required output format for missing results.
- Output the exact sentinel value specified (e.g., `[]`, `[-1]`, or other), matching the task's requirements.

CORRECT: If task says "return [] if no result found" and Bundle is empty, output `FINISH([])`.
WRONG: Outputting `FINISH([-1])` or `FINISH(["No result found"])` when `[]` is required.

**Pattern 2: fallback or verification rule**
- If the task does not specify a required format, default to an empty array `[]` for missing lab values.
- If the task specifies a scalar (e.g., `-1`), use that exact value.

**Pattern 3: formatting or completion rule**
- Always wrap the output in the required array or scalar format.
- Do not add explanatory text unless the task explicitly requests it.

## Example Application

**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours? The answer should be a single number converted to a unit of mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step-by-step:**

1. Issue GET: `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0674240`
2. Inspect Bundle response:
   - If `total` is 0 or `entry` is empty, no result found.
3. Output: `FINISH([-1])` (since task specifies -1 for missing result)

CORRECT output: `FINISH([-1])`
WRONG output:   `FINISH([])` or `FINISH(["No result found"])`

**Task:** "What’s the last HbA1C value in the chart for patient S6488980 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test. The answer should be [] if no result is found."

**Step-by-step:**

1. Issue GET: `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6488980`
2. Inspect Bundle response:
   - If `total` is 0 or `entry` is empty, no result found.
3. Output: `FINISH([])`

CORRECT output: `FINISH([])`
WRONG output:   `FINISH([-1])` or `FINISH(["No result found"])`

## Success Indicators
- The agent outputs the exact sentinel value specified by the task for missing lab results.
- The output format matches the task requirements (array, scalar, etc.).
- No explanatory text or default values are present unless requested.

## Failure Indicators
- The agent returns `[-1]` when `[]` is required, or vice versa.
- The agent returns a string or text instead of the required format.
- The agent fails to check for missing results and outputs stale or default values.
