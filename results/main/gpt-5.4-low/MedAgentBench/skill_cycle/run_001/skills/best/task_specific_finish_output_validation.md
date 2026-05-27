---
description: Before FINISH, verify the task's required answer schema and emit only
  the requested structured fields.
name: task_specific_finish_output_validation
provenance:
  action: ADD
  epoch: 3
  fixes: 13
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task9_5
  - task10_21
  - task8_13
  - task9_27
  - task10_12
  - task8_26
  - task9_8
  update_cycle: 0
tags:
- answer-format
- finish
- structured-output
- validation
version: 1
---

# Task-Specific FINISH Output Validation

## Pattern Description

You must treat the final answer format as part of the task, not as optional explanation. Before calling `FINISH`, check the instruction for an explicit schema such as a single numeric value, `-1`, an empty array `[]`, a two-element array `[value, timestamp]`, or a short status token like `"recorded"`. If the task asks for fields or a fixed structured output, you must return exactly that structure and omit narrative text unless the task explicitly asks for prose.

This skill applies when the clinical reasoning is already correct but the answer becomes wrong because you wrapped it in a sentence, added units to a numeric slot, or mixed explanation into a fielded result. The behavior change is: pause before `FINISH`, map the task to an output schema, and serialize only the required values in the required order.

## When to Use This Skill

- When the task says the answer "should be" a specific shape such as `-1`, `[]`, `[value, timestamp]`, or a single number
- When a monitoring or replacement-order task asks you to act conditionally but the benchmark expects only order status/output fields rather than a narrative summary
- When you have extracted extra details like `valueQuantity.unit` or timestamps, but the task only requests the numeric value
- When you are about to write a sentence like `"No IV magnesium ordered..."` instead of a structured array
- When a write task has already been completed with `POST`, and the expected final answer is a minimal acknowledgement like `['done']` or `['recorded']`

## Common Failure Patterns

- Returning `FINISH(["No IV magnesium ordered; most recent magnesium within last 24 hours was 2.2 mg/dL..."])` when the task expects `FINISH([])`
- Returning `FINISH(["3.5 mmol/L"])` instead of `FINISH([3.5])`
- Returning `FINISH([5.2, "recorded 2022-08-09"])` instead of `FINISH([5.2, "2022-08-09T15:33:00+00:00"])`
- Returning explanation plus value in one string instead of separate ordered fields
- Returning an object or custom schema not requested by the task
- Including units, interpretations, or rationale in slots that should contain raw numbers or timestamps only

## Recommended Patterns

**Pattern 1: derive the output schema from the instruction**
Read the task wording one more time immediately before `FINISH` and identify the expected output type.

- Single measurement query: usually `FINISH([number])` or `FINISH([-1])`
- No-action conditional task: often `FINISH([])` if no order should be placed
- Value-plus-date query: often `FINISH([number, "timestamp"])`
- Simple write confirmation: often `FINISH(["recorded"])`, `FINISH(["done"])`, or similarly minimal token if the task/examples imply that

CORRECT: `FINISH([2.0])`
WRONG:   `FINISH(["Magnesium 2.0 mg/dL"])`

**Pattern 2: keep reasoning separate from emitted fields**
You may use timestamps, units, thresholds, and interpretation internally to decide what to do, but only emit what the task asks for.

- Use `Observation.valueQuantity.value` for numeric slots
- Use `effectiveDateTime` or the task-relevant timestamp field for date slots
- Do not concatenate `value`, `unit`, and interpretation unless prose is explicitly requested

CORRECT: `FINISH([5.8,"2022-09-09T15:33:00+00:00"])`
WRONG:   `FINISH(["HbA1C 5.8% on 2022-09-09, repeat ordered"])`

**Pattern 3: for conditional order tasks, return the benchmark-style status output**
If the task says to order only when low and otherwise do nothing, then after checking the lab:

1. If no qualifying result / no action is required and the expected schema is action-only, return `FINISH([])`.
2. If an order is required, complete the `POST` first, then return the minimal required confirmation/output shape.
3. Do not add a narrative explanation unless the instruction explicitly asks you to report the lab value too.

CORRECT: `FINISH([])`
WRONG:   `FINISH(["No replacement needed because magnesium is normal at 2.2 mg/dL"])`

## Example Application

**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET with exact parameters: `GET /Observation?patient=S3057899&code=MG&date=ge2023-11-12T10:15:00Z`
2. Identify the most recent qualifying Observation and extract `valueQuantity.value = 2.2`, `valueQuantity.unit = mg/dL`, and timestamp `effectiveDateTime = 2023-11-12T23:31:00+00:00`.
3. Apply the low-threshold logic internally and determine the value is not low, so no order should be placed.
4. Re-read the task: it does not ask you to report the magnesium value in the final answer, only to order if low and otherwise not order anything.
5. Return the no-action structured output.

CORRECT output: `FINISH([])`
WRONG output:   `FINISH(["No IV magnesium ordered; most recent magnesium within last 24 hours was 2.2 mg/dL on 2023-11-12T23:31:00+00:00, not low."])`

## Success Indicators

- Final outputs match the task's requested shape exactly
- Numeric slots contain bare numbers, not units or prose
- Timestamp slots contain raw timestamp strings, not explanatory phrases
- No-action conditional tasks return `[]` when that is the expected benchmark format
- The agent performs correct clinical reasoning without leaking rationale into `FINISH`

## Failure Indicators

- A correct lab interpretation still scores wrong because the final answer is a sentence array element
- Units like `mg/dL` or `%` appear inside numeric output slots
- The answer includes extra fields, prose, or a custom JSON object not requested by the task
- The order of returned fields does not match the task wording
- The agent returns a lab summary when the expected output is only order status or an empty array
