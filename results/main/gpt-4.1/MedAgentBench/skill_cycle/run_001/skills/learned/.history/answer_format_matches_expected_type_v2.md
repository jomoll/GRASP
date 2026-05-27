---
description: Ensures the answer format matches the expected output type for lab values,
  ages, and similar queries, except when the task is a multi-step workflow where an
  empty array is used to indicate completion of all requested actions.
name: answer_format_matches_expected_type
provenance:
  action: MODIFY
  epoch: 1
  fixes: 11
  parent_version: 1
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task10_27
  - task9_9
  - task10_10
  - task9_8
  - task10_8
  - task10_13
  update_cycle: 1
tags: []
version: 2
---

# Answer Format Matches Expected Type

## Pattern Description

When returning answers for structured queries (such as lab values, ages, or other numeric results), you must ensure the output matches the expected type and sentinel value conventions for the task. This includes returning the correct sentinel value (such as `-1` or `null`) or an empty array when no result is found, and never substituting with a placeholder or arbitrary value (such as `-1`) unless the task explicitly specifies it. This skill is critical for tasks where the absence of data must be signaled in a specific way, and for ensuring downstream consumers can reliably interpret the result.

## When to Use This Skill

- When a GET /Observation or similar search returns an empty entry array or total=0, and the task expects a value or a sentinel for missing data.
- When the task instructions specify a required sentinel value (e.g., `-1`, `null`, or `"Patient not found"`) for missing data.
- When the answer must be a specific type (e.g., number, string, or array) as described in the task.
- When the task expects both a value and a timestamp, and no result is found.

### Guard Clause: Multi-step Workflow Completion
- **Do NOT apply this rule to FINISH([]) when the empty array is used to indicate that all requested actions (e.g., ordering labs, medications) have been completed in a multi-step workflow, and not as a sentinel for missing data.**
- If the FINISH([]) is used as a workflow completion signal (i.e., after all actions are performed and not as a direct answer to a missing value query), it is acceptable and should not be replaced with another sentinel.

## Common Failure Patterns

- Returning `-1` as a placeholder when the task expects `null`, an empty array, or a string sentinel (e.g., `"Patient not found"`).
- Returning `-1` for missing lab values when the task expects an empty array or `null`.
- Returning a number when the task expects a string or vice versa.
- Returning a value with units or extra text when only a number is expected.
- Returning a value for a missing resource instead of the correct sentinel.

## Recommended Patterns

Pattern 1: Match the expected sentinel or empty value
- Inspect the task instructions for the required sentinel value or output format for missing data.
- If the task says "If not found, return -1", return `FINISH([-1])`.
- If the task says "If not found, return null", return `FINISH([null])`.
- If the task says "If not found, return an empty array", return `FINISH([])`.
- If the task says "If not found, return 'Patient not found'", return `FINISH(["Patient not found"])`.

Pattern 2: Verify the output type
- Ensure the output matches the expected type (number, string, array, etc.).
- Do not return a number when a string is expected, or vice versa.

Pattern 3: Multi-field answers
- If the task expects multiple fields (e.g., value and date), return both as `null` or the specified sentinel if missing.

Pattern 4: Multi-step workflow completion
- If the task involves multiple actions (e.g., check a value, order medication, order lab), and FINISH([]) is used at the end to indicate all actions are complete, this is correct and should not be replaced with another sentinel.

## Example Application

**Task:** "Check patient S6547257's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Issue GET with exact parameters:
   `GET /Observation?code=K&patient=S6547257`
2. If the response is a Bundle with `total: 0` or no entries, check the task for the required sentinel value.
3. If the task does not specify a sentinel, and the FINISH([]) is used as a workflow completion signal (after all actions are performed), FINISH([]) is correct.
4. If the task specifies `-1` for missing, return `FINISH([-1])`.

CORRECT output: `FINISH([])` (if task expects empty array for missing, or as workflow completion)
CORRECT output: `FINISH([null])` (if task expects null)
CORRECT output: `FINISH([-1])` (if task expects -1)
CORRECT output: `FINISH([])` (if used as workflow completion after all actions)
WRONG output:   `FINISH([-1])` (if task expects empty array or null)

## Success Indicators

- The output matches the type and sentinel value specified in the task instructions for missing data.
- No extraneous or arbitrary placeholder values are used.
- Downstream consumers can reliably interpret missing data.
- FINISH([]) is used appropriately as a workflow completion signal in multi-step tasks.

## Failure Indicators

- Returning `-1` when the task expects an empty array or `null`.
- Returning a value of the wrong type (e.g., number instead of string).
- Returning a value with units or extra text when only a number is expected.
- Returning a value for a missing resource instead of the correct sentinel.
- Replacing FINISH([]) used for workflow completion with another sentinel.
