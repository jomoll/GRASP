---
description: Enforce strict machine-readable list or tuple format for all final answers
  to prevent conversational text.
name: structured_final_output_strategy
provenance:
  action: MODIFY
  epoch: 7
  fixes: 3
  parent_version: 2
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task5_16
  - task9_6
  - task5_3
  - task9_1
  - task9_5
  - task5_19
  - task10_17
  - task9_22
  - task10_21
  - task9_27
  update_cycle: 1
tags:
- formatting
- output-control
version: 3
---

## Skill Title
Structured Final Output Strategy

## Pattern Description
When providing a final answer to a task, you must always return a machine-readable format (a list or tuple) containing only the requested data points. Do not include conversational filler, explanations, or natural language sentences in the `FINISH` call. If the task asks for multiple values, provide them as a list of values in the order requested.

## When to Use This Skill
- When the task asks for specific data points (e.g., lab values, dates, MRNs, ages).
- When the task requires a final answer after performing data retrieval or calculations.
- When the previous attempt included conversational text instead of just the requested data.

## Common Failure Patterns
- Returning `FINISH(["The value is 5.0%"])` instead of `FINISH(["5.0%"])`.
- Returning `FINISH(["Potassium is 3.5 mmol/L"])` instead of `FINISH([3.5])`.
- Including units inside the list when the task asks for a numeric value.
- Providing conversational explanations in the `FINISH` argument.

## Recommended Patterns

**Pattern 1: Numeric Extraction**
If the task asks for a measurement, extract only the numeric value and return it as a single-element list.
CORRECT: `FINISH([3.5])`
WRONG: `FINISH(["3.5 mmol/L"])`

**Pattern 2: Multi-value Extraction**
If the task asks for multiple fields (e.g., value and date), return them as a list in the order specified by the prompt.
CORRECT: `FINISH([5.0, "2023-11-09T10:06:00+00:00"])`
WRONG: `FINISH(["The value is 5.0 and the date is 2023-11-09"])`

## Example Application

**Task:** "What is the last HbA1C value and when was it recorded?"

**Step-by-step:**
1. Retrieve the observation.
2. Extract the value (e.g., 5.0) and the effective date (e.g., 2023-11-09T10:06:00+00:00).
3. Format as a list: `[5.0, "2023-11-09T10:06:00+00:00"]`.
4. Call `FINISH([5.0, "2023-11-09T10:06:00+00:00"])`.

## Success Indicators
- The `FINISH` call contains only the raw data requested.
- No conversational text is present in the final output.

## Failure Indicators
- The `FINISH` call contains strings like "The value is..." or "recorded on...".
- Units are included in the numeric output when not requested.
