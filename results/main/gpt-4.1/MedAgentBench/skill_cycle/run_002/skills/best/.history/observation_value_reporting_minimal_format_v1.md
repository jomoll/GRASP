---
description: Ensure FINISH returns only the potassium value and date in an array,
  omitting explanations when not low.
name: observation_value_reporting_minimal_format
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 10
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task4_20
  - task4_6
  - task2_28
  - task4_26
  - task9_3
  - task10_18
  - task2_26
  - task2_14
  - task4_15
  update_cycle: 0
tags:
- observation
- lab
- formatting
- potassium
- minimal_output
version: 1
---

# Observation Value Reporting Minimal Format

## Pattern Description

When reporting the result of a laboratory observation (such as potassium) in response to a conditional action (e.g., "If low, then order replacement"), you must return only the essential data (value and date) in the FINISH array if no further action is required. Do not include explanations, restatements, or justifications when the value is not low and no follow-up is needed. This ensures the output is concise and machine-readable, and avoids unnecessary narrative or redundant statements.

This pattern is especially important for tasks where the primary goal is to check a lab value and only act if a threshold is crossed. If the value is not low (or not abnormal), the agent should simply return the value and date, not a full sentence or rationale.

## When to Use This Skill

- When a task asks to check a lab value (e.g., potassium) and only take further action if the value is low/abnormal.
- When the result is normal and no follow-up orders or actions are required.
- When the FINISH output is expected to be an array containing only the value and date.

## Common Failure Patterns

- FINISH includes explanations such as "which is not low" or "No potassium replacement is needed."
- FINISH includes redundant statements like "No further orders are required."
- FINISH returns a full sentence or justification instead of just the value and date.
- FINISH returns an array of multiple narrative strings instead of a single array with the value and date.

## Recommended Patterns

Pattern 1: Minimal Value Reporting
- Extract the most recent value and its date from the Observation resource (e.g., `valueQuantity.value` and `effectiveDateTime`).
- If the value is not low (per task definition), return only `[value, date]` in the FINISH array.
- Do not include any explanation, justification, or restatement of the normality.

CORRECT: `FINISH([4.0, "2023-11-11T09:44:00+00:00"])`
WRONG:   `FINISH(["Most recent potassium level is 4.0 mmol/L (2023-11-11T09:44:00+00:00), which is not low. No potassium replacement or additional orders are needed."])`

Pattern 2: Conditional Action
- If the value is low, proceed with the specified follow-up actions (e.g., order replacement, schedule follow-up lab) and report those actions as required by the task.
- If no action is needed, do not add any narrative or explanation.

Pattern 3: Output Structure
- The FINISH array should contain only the value and date, in that order, as separate elements.
- Do not wrap the value and date in a single string or add units unless explicitly required.

## Example Application

**Task:** "Check patient S3236936's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Issue GET: `GET /fhir/Observation?code=K&patient=S3236936`
2. Extract the most recent potassium value and its date: `valueQuantity.value = 4.0`, `effectiveDateTime = "2023-11-11T09:44:00+00:00"`
3. Determine that 4.0 is not low (per task definition).
4. Construct the output:

CORRECT output: `FINISH([4.0, "2023-11-11T09:44:00+00:00"])`
WRONG output:   `FINISH(["Most recent potassium level for patient S3236936 is 4.0 mmol/L (2023-11-11T09:44:00+00:00), which is not low. No potassium replacement or additional orders are needed."])`

## Success Indicators

- FINISH returns an array with only the value and date, no explanation or narrative.
- No redundant or explanatory statements are present when no action is needed.
- Output is concise and machine-readable.

## Failure Indicators

- FINISH includes explanations, justifications, or restatements of normality.
- FINISH includes multiple narrative strings or redundant statements.
- Output is not a simple array of value and date.
