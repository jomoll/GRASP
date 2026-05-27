---
description: Enforce 'if low' action condition before reporting or ordering for potassium/magnesium
  labs.
name: observation_value_reporting_minimal_format
provenance:
  action: MODIFY
  epoch: 0
  fixes: 14
  parent_version: 1
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - task9_11
  - task9_22
  - task10_16
  - task10_21
  - task9_5
  - task5_16
  - task4_28
  - task5_19
  - task9_27
  - task4_23
  update_cycle: 1
tags:
- observation
- conditional-action
- lab
- potassium
- magnesium
- threshold
- order
version: 2
---

# Observation Value Reporting with Conditional Action

## Pattern Description

When a task requests the most recent potassium or magnesium value and specifies an action only if the value is low (e.g., "If low, then order replacement"), you must not report the value or take any action unless you have checked whether the value meets the 'low' threshold. This pattern applies to both reporting and ordering logic: the agent must actively check the value against the clinical threshold before proceeding with any replacement orders or reporting the value as an answer.

This skill ensures that the agent does not order unnecessary replacement or report values in a way that implies action was taken without justification. It also prevents reporting a value in the output array when the instruction expects action only if the value is low.

## When to Use This Skill

- When the task includes a conditional action: "If low, then order replacement..."
- When extracting potassium or magnesium lab values for decision-making.
- When the instruction requires reporting a value only if it triggers a downstream action (e.g., replacement order).
- When the instruction says to do nothing if the value is not low or not present.

## Common Failure Patterns

- Reporting the value and date in the output array even when the value is not low and no action is required.
- Ordering replacement potassium or magnesium without checking if the value is below the low threshold.
- Omitting the threshold check and always reporting the value regardless of the instruction's conditional logic.
- Returning FINISH([value, date]) for normal values when the task expects no output or action unless low.

## Recommended Patterns

Pattern 1: Check the 'if low' condition before any reporting or ordering

1. Extract the most recent potassium or magnesium value and its date.
2. Compare the value to the clinical low threshold (e.g., potassium < 3.5 mmol/L, magnesium < 1.8 mg/dL unless otherwise specified).
3. Only if the value is below the threshold, proceed to order replacement and/or report the value as required by the task.
4. If the value is not low, do not order replacement and do not report the value in the output array unless the task explicitly requests it.

CORRECT: (for potassium 3.9 mmol/L, threshold 3.5)
- No replacement order, no value reported: `FINISH([])`

WRONG:
- Reporting value when not low: `FINISH([3.9, "2023-11-12T13:52:00+00:00"])`
- Ordering replacement for normal value.

Pattern 2: Fallback for missing or outdated values

- If no value is found within the required time window, do not order replacement and return an empty array or -1 as specified by the task.

Pattern 3: Output formatting

- Only include the value and date in the output array if the value is low and action is required.
- Otherwise, return an empty array or the sentinel value as specified.

## Example Application

**Task:** "Check patient S3213957's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Issue GET: `GET /Observation?code=K&patient=S3213957`
2. Extract the most recent value and date: e.g., 3.9 mmol/L on 2023-11-12T13:52:00+00:00
3. Compare to threshold: 3.9 >= 3.5 (not low)
4. Do not order replacement, do not order follow-up, do not report value
5. Output: `FINISH([])`

CORRECT output: `FINISH([])`
WRONG output:   `FINISH([3.9, "2023-11-12T13:52:00+00:00"])` or any replacement order

## Success Indicators

- No replacement order or follow-up is placed for normal potassium/magnesium values.
- The output array is empty (or as specified) when the value is not low and no action is required.
- Replacement is only ordered when the value is below the clinical threshold.

## Failure Indicators

- Replacement orders are placed for normal values.
- The value and date are reported in the output array when the value is not low and the task expects no action.
- The agent omits the threshold check and always reports the value or takes action regardless of the instruction's conditional logic.
