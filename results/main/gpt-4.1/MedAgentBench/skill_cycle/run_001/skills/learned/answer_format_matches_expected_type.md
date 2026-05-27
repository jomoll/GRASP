---
description: Ensures the answer format matches the expected output type for lab values,
  ages, and similar queries, including correct handling of multi-step workflows.
name: answer_format_matches_expected_type
provenance:
  action: MODIFY
  epoch: 2
  fixes: 5
  parent_version: 2
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_9
  - task10_10
  - task10_12
  - task9_1
  - task9_22
  update_cycle: 1
tags:
- format
- lab
- multistep
- workflow
- output
version: 3
---

# Answer Format Matches Expected Type

## Pattern Description

When a task requires both multi-step actions (such as ordering labs or medications) and a final answer (such as reporting a lab value or timestamp), you must ensure the FINISH output matches the expected answer format. This includes returning the requested lab value(s) and/or timestamp(s) in the correct structure, not just an empty array, even after all actions are completed. The skill applies to tasks where the user expects a structured answer (e.g., `[value, timestamp]` or `[value]`) after workflow steps, not just confirmation of action completion.

This pattern prevents the agent from omitting the required answer in the final FINISH output after performing all requested actions, especially in multi-step workflows where the answer is not simply an empty array.

## When to Use This Skill

- When the task requests both an action (e.g., order medication/lab) and a final answer (e.g., "what is the most recent potassium level?").
- When the instruction specifies to check a value, act if abnormal, and report the value or timestamp.
- When the expected output is a structured value (e.g., `[number]`, `[number, timestamp]`), not just confirmation of action completion.
- When the task is not a pure workflow ("just order X"), but a hybrid ("check and act, then report").

## Common Failure Patterns

- Returning `FINISH([])` after completing all actions, omitting the required answer value(s).
- Returning only confirmation of orders placed, without reporting the checked lab value or timestamp.
- Returning a narrative string instead of a structured array (e.g., `FINISH(["Potassium is 3.5 mmol/L, within normal range."])`).
- Returning only the action result (e.g., order placed) when the task also expects a value.

## Recommended Patterns

**Pattern 1: Extract and Report Value After Actions**
1. After performing all required actions (e.g., ordering medication/lab), extract the relevant value(s) from the initial GET response (e.g., most recent potassium level and timestamp).
2. Structure the FINISH output as specified in the task (e.g., `[potassium_value]`, `[potassium_value, timestamp]`).
3. Do not return an empty array unless the task explicitly expects it for "no action needed" or "no value found" cases.

CORRECT: `FINISH([3.2])` or `FINISH([3.2, "2023-11-13T08:00:00+00:00"])`
WRONG:   `FINISH([])`

**Pattern 2: Multi-Step Workflow with Final Value**
- If the task is "check value, act if abnormal, and report value", always include the checked value in the final FINISH output, even after all actions are completed.
- Only use `FINISH([])` if the task is a pure workflow ("order X" with no value reporting) or if the instructions specify empty output for "no value found".

**Pattern 3: Verification Rule**
- Before FINISH, review the task instructions for expected output format and ensure the output matches (e.g., array of numbers, array with timestamp, etc.).
- If unsure, prefer to include the checked value(s) in the output rather than omitting them.

## Example Application

**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. GET the most recent potassium Observation: `GET /Observation?code=K&patient=S6474456`
2. Extract the most recent potassium value (e.g., 3.2) and timestamp.
3. If low, POST MedicationRequest and ServiceRequest as instructed.
4. FINISH with the potassium value (and optionally timestamp if requested):

CORRECT output: `FINISH([3.2])` or `FINISH([3.2, "2023-11-13T08:00:00+00:00"])`
WRONG output:   `FINISH([])`

## Success Indicators

- The final FINISH output includes the requested value(s) in the correct structure, even after all actions are completed.
- The output matches the format specified in the task (e.g., `[number]`, `[number, timestamp]`).
- No empty arrays are returned unless explicitly required by the task.

## Failure Indicators

- FINISH output is an empty array when a value is expected.
- The agent omits the checked value(s) after performing all actions.
- The output is a narrative string or confirmation only, not a structured value.
