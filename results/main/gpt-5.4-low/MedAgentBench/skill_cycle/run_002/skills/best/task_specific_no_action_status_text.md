---
description: Use explicit task-matched no-action wording instead of generic status
  text in lab-and-order workflows.
name: task_specific_no_action_status_text
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - task9_27
  - task9_28
  - task9_20
  - task5_3
  - task10_24
  - task9_1
  - task9_11
  - task10_20
  - task5_19
  - task5_17
  update_cycle: 1
tags:
- output-format
- status-text
- orders
- conditional-workflow
version: 1
---

# Task-Specific No-Action Status Text

## Pattern Description

When a task asks you to both assess a clinical result and decide whether to place an order, you must make the final status text match the specific action named in the prompt. Do not fall back to generic phrases like "No order placed" when the benchmark expects the status to explicitly mention the medication, test, or intervention that was not ordered.

This matters most in conditional workflows where the lab is normal or not low enough to trigger treatment. In those cases, you should still return the measured value and time, but the status string must say that the specific treatment was not ordered, such as "No IV magnesium ordered," rather than a generic no-op phrase.

## When to Use This Skill

- When the task says "If low, order X; otherwise don't order anything"
- When the expected answer format includes a status/message field alongside a lab value or timestamp
- When you are about to write a final string like "No order placed" after evaluating an Observation
- When the prompt names a specific intervention such as IV magnesium replacement, potassium replacement, or a repeat lab order

## Common Failure Patterns

- Returning `"No order placed"` instead of a task-specific string like `"No IV magnesium ordered"`
- Using a generic status string that omits the intervention named in the prompt
- Splitting status across multiple extra fields instead of keeping one status field in the expected array position
- Mixing interpretation text into the status field, such as `"Magnesium normal; no order placed"`, when the task expects a short canonical no-action phrase
- Using the same no-action text for both "no recent result exists" and "result reviewed but treatment not indicated" without checking the prompt's expected distinction

## Recommended Patterns

**Pattern 1: derive the no-action phrase from the requested intervention**
Before calling `FINISH`, identify the exact intervention in the task text.

- If the task says to order IV magnesium if low, the non-order status should explicitly mention IV magnesium.
- If the task says to order potassium replacement if low, the non-order status should explicitly mention potassium replacement.

CORRECT: `"No IV magnesium ordered"`
WRONG:   `"No order placed"`

**Pattern 2: distinguish no-result from no-treatment-needed**
If `Bundle.entry` is empty after the required time filter, report the missing-result condition separately if the task asks for it, and use the no-order status only for the order decision.

Example pattern:
- No recent lab: `FINISH(["No magnesium level recorded in the last 24 hours","No order placed"])` if that is the task's required structure
- Recent normal lab: `FINISH([2.2,"2023-11-12T23:31:00+00:00","No IV magnesium ordered"])`

Do not reuse the missing-result wording when a valid recent result exists.

**Pattern 3: keep the final output structure exact**
Preserve the required array shape from the task type.

- If the task expects `[value, timestamp, status]`, keep exactly three elements.
- Put the task-specific no-action phrase in the status slot only.
- Do not add extra explanation fields.

CORRECT: `FINISH([2.3,"2023-11-12T14:18:00+00:00","No IV magnesium ordered"])`
WRONG:   `FINISH([2.3,"2023-11-12T14:18:00+00:00","magnesium normal","No order placed"])`

## Example Application

**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET with exact parameters: `GET /Observation?code=MG&patient=S3057899&date=ge2023-11-12T10:15:00%2B00:00`
2. From the returned `Bundle.entry`, select the most recent Observation within the window.
3. Extract `valueQuantity.value = 2.2` and the result time from the Observation date field used by the task.
4. Compare against the low threshold from the task instructions. Since 2.2 is not low, do not place a medication order.
5. Construct the final output with a task-specific no-action phrase naming the withheld intervention.

CORRECT output: `FINISH([2.2,"2023-11-12T23:31:00+00:00","No IV magnesium ordered"])`
WRONG output:   `FINISH([2.2,"2023-11-12T23:31:00+00:00","No order placed"])`

## Success Indicators

- The final status string explicitly names the intervention from the prompt
- Normal/non-low results return value and timestamp plus a specific no-action status
- Missing-result cases remain distinct from reviewed-but-no-treatment-needed cases
- The output array has the exact expected number and order of fields

## Failure Indicators

- Final answer uses generic phrases like `"No order placed"` despite a named intervention in the prompt
- The status text fails to mention the specific medication/test/referral that was not ordered
- The answer adds an extra explanation field and shifts the expected output shape
- The same wording is used for both "no recent lab found" and "lab found but treatment not indicated" when the task distinguishes them
