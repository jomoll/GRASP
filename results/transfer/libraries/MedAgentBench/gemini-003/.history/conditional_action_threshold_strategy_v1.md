---
description: Enforce conditional logic to prevent unnecessary POST requests when clinical
  thresholds are not met.
name: conditional_action_threshold_strategy
provenance:
  action: ADD
  epoch: 6
  fixes: 3
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task9_9
  - task5_3
  - task10_12
  - task9_27
  - task5_19
  - task9_5
  - task9_1
  - task9_6
  - task10_20
  - task10_10
  update_cycle: 0
tags:
- conditional-logic
- fhir
- threshold-check
version: 1
---

# Conditional Action Threshold Strategy

## Pattern Description
When a task requires an action (e.g., ordering a medication or a follow-up test) contingent on a clinical threshold (e.g., "if low"), you must first retrieve and evaluate the relevant data. Do not proceed with any POST requests until you have confirmed that the data meets the specific criteria defined in the instruction.

## When to Use This Skill
- When a task includes a conditional trigger (e.g., "If low, then order...").
- When you are about to perform a `POST` request (MedicationRequest, ServiceRequest) based on a lab value.
- When you have retrieved a lab value but have not yet verified if it meets the threshold for action.

## Common Failure Patterns
- Executing a `POST` request automatically after a `GET` request, regardless of the retrieved value.
- Failing to compare the retrieved `valueQuantity.value` against the threshold (e.g., 3.5 mmol/L for potassium).
- Ordering redundant tests or medications when the clinical data indicates no action is required.

## Recommended Patterns

**Pattern 1: Threshold Evaluation**
1. Retrieve the most recent observation using `_sort=-date`.
2. Extract the `valueQuantity.value`.
3. Compare the value against the threshold specified in the prompt.
4. If the value does not meet the threshold, stop and report the finding without performing the action.

**Pattern 2: Conditional Execution**
- Only proceed to `POST` if the threshold condition is met.
- If the condition is not met, call `FINISH` with a clear explanation (e.g., "Level is 3.8, which is not low; no replacement ordered").

## Example Application

**Task:** "Check potassium. If < 3.5, order replacement."

**Step-by-step:**
1. GET `.../Observation?code=K&_sort=-date`
2. Receive value: `3.8`.
3. Evaluate: `3.8 < 3.5` is `False`.
4. Action: Do not POST `MedicationRequest`.
5. Output: `FINISH(["Potassium is 3.8, not low. No replacement ordered."])`

## Success Indicators
- No `POST` requests are sent when the clinical data does not meet the criteria.
- The final output explicitly states why no action was taken.

## Failure Indicators
- `POST` requests are sent even when the lab value is within normal range.
- The agent performs redundant actions despite the data indicating they are unnecessary.
