---
description: Match FINISH output exactly to the task schema and omit explanatory narration,
  especially for no-action results.
name: task_constrained_finish_minimal_output
provenance:
  action: ADD
  epoch: 2
  fixes: 7
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - task9_8
  - task9_14
  - task10_20
  - task3_19
  - task10_24
  - task9_5
  - task10_10
  - task9_22
  - task10_8
  - task9_1
  update_cycle: 1
tags:
- formatting
- finalization
- conditional_orders
- potassium
version: 1
---

# Task-Constrained Minimal FINISH Output

## Pattern Description

When a task specifies an answer shape implicitly or explicitly, you must make `FINISH(...)` contain only the required data or confirmation text, not your reasoning. This is especially important in clinical decision tasks where you may be tempted to explain that a lab is normal or that no orders were placed. If the benchmark expects a terse structured result, extra narrative text can make an otherwise correct decision score as wrong.

You should separate internal clinical reasoning from final output formatting. First determine whether any action is needed; then emit only the minimal allowed payload. For no-action branches, this often means returning an empty list `[]` rather than a sentence explaining why nothing was ordered.

## When to Use This Skill

- When the instruction says to check a lab and only order something if a condition is met
- When the task includes phrasing like "if low, then order..." or "if not available, don't order anything"
- When prior tasks of the same family use `FINISH([])` for no-action outcomes
- When you have already gathered the needed result and are about to call `FINISH(...)`
- When you notice yourself drafting prose such as "not low, so no replacement ordered"

## Common Failure Patterns

- Returning explanatory prose in `FINISH`, such as `FINISH(["Most recent potassium 4.7 mmol/L ... not low, so no potassium replacement ordered."])`
- Including both findings and interpretation when the task expects only orders or only scalar values
- Emitting a textual no-action summary instead of `FINISH([])`
- Mixing answer types across branches, such as numeric arrays for one branch and English sentences for another
- Adding date/unit commentary to a branch where no order is required

## Recommended Patterns

## Pattern 1: infer the output contract from the task family

Before answering, identify what kind of artifact the task expects:

- Retrieval task asking for a value/date pair: return only those fields
- Conditional order task: return created orders if action is indicated
- Conditional order task with no indicated action: return `[]`

CORRECT: `FINISH([])`
WRONG:   `FINISH(["Potassium 4.7 mmol/L, not low, so no replacement or repeat lab ordered."])`

## Pattern 2: for no-action branches, emit an empty result unless the prompt explicitly asks for text

If you determine the threshold for treatment is not met, do not narrate the normal result unless the user explicitly requested the value be reported in the final answer. In order-only workflows, the absence of orders should be represented as an empty list.

CORRECT: potassium not low -> `FINISH([])`
WRONG:   potassium not low -> `FINISH(["Most recent potassium 4.3 mmol/L on 2023-11-12... not low..."])`

If the prompt explicitly names a fallback text like `"Patient not found"`, use that exact text and nothing extra.

## Pattern 3: keep reasoning out of GET URLs and out of FINISH

Complete all GET/POST actions first. Then issue exactly one clean `FINISH(...)` payload. Do not append `FINISH(...)` text onto a URL, and do not place status commentary inside the URL or request body.

CORRECT: `GET /Observation?...` then `FINISH([])`
WRONG:   `GET /Observation?...FINISH([])`

## Example Application

## Task: "Check patient S1796597's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

## Step-by-step:

1. Issue GET with exact parameters: `GET /Observation?patient=S1796597&code=K`
2. Extract the most recent potassium from `entry[].resource.valueQuantity.value` and its timestamp from `effectiveDateTime` or equivalent result time field used by the task.
3. Apply the low-potassium threshold from the task instructions.
4. If the value is not low, create no orders and return the empty result only.

CORRECT output: `FINISH([])`
WRONG output:   `FINISH(["Most recent potassium 4.7 mmol/L on 2023-11-12T18:06:00+00:00; not low, so no potassium replacement or follow-up potassium lab ordered."])`

## Success Indicators

- `FINISH(...)` contains only the task-required payload shape
- No explanatory sentences appear in no-action branches
- Conditional order tasks return `[]` when no treatment/order is indicated
- Final output type stays consistent with the task family

## Failure Indicators

- `FINISH(...)` includes phrases like "not low, so no order..."
- The answer contains normal-value commentary when the task expected orders or an empty list
- Different branches return different output schemas without explicit instruction
- A correct clinical decision is marked wrong because of extra narration rather than wrong data
