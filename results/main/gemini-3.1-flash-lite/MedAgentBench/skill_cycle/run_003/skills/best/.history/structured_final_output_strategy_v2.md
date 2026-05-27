---
description: Enforce strict machine-readable list or tuple format for all final answers
  to prevent conversational text.
name: structured_final_output_strategy
provenance:
  action: MODIFY
  epoch: 6
  fixes: 1
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_8
  - task5_16
  - task9_22
  - task5_7
  - task9_3
  - task10_8
  - task10_24
  - task9_20
  - task10_17
  - task9_28
  update_cycle: 1
tags:
- formatting
- output-control
version: 2
---

# Structured Final Output Strategy

## Pattern Description

When providing a final answer to a task, you must output only a machine-readable format (a list or tuple). Do not include conversational filler, explanations, or natural language summaries. The goal is to ensure that downstream systems or evaluators can parse your output programmatically without needing to strip away text.

## When to Use This Skill

- Always, when calling the `FINISH` function.
- When the task asks for a specific value, a list of values, or a confirmation of an action.
- When the task involves checking clinical thresholds or lab values.

## Common Failure Patterns

- Including conversational text like "The value is..." or "No replacement was ordered."
- Returning a string instead of a list or tuple (e.g., `FINISH("3.5")` instead of `FINISH([3.5])`).
- Providing a mix of data and explanation in the same list element.

## Recommended Patterns

**Pattern 1: Single Value Output**
If the task asks for a single number or result, return it as a single-element list.
CORRECT: `FINISH([3.5])`
WRONG:   `FINISH(["The value is 3.5"])`

**Pattern 2: Multiple Data Points**
If the task asks for multiple pieces of information (e.g., a value and a date), return them as a tuple or list.
CORRECT: `FINISH([5.8, "2022-09-09T15:33:00+00:00"])

**Pattern 3: Action Confirmation**
If the task asks to perform an action and report the result, return a status code or a minimal confirmation string in a list.
CORRECT: `FINISH(["SUCCESS"])
WRONG:   `FINISH(["The order was placed successfully."])

## Example Application

**Task:** "Check patient S1023381's last serum magnesium level."

**Step-by-step:**
1. Retrieve the value (e.g., 2.0).
2. Format the output as a list containing only the value.
3. Call `FINISH([2.0])`.

## Success Indicators

- The `FINISH` call contains only raw data structures (lists, numbers, strings) without conversational prose.

## Failure Indicators

- The `FINISH` call contains sentences or paragraphs.
- The output is not parsable as a standard JSON list.
