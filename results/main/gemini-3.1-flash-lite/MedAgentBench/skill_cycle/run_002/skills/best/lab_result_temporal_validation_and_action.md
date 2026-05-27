---
description: Enforce strict date-based validation for lab results and conditional
  ordering logic.
name: lab_result_temporal_validation_and_action
provenance:
  action: ADD
  epoch: 4
  fixes: 7
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_8
  - task10_13
  - task5_3
  - task5_17
  - task5_16
  - task9_3
  - task9_11
  - task10_27
  - task5_7
  - task10_18
  update_cycle: 0
tags:
- lab-results
- temporal-logic
- conditional-ordering
version: 1
---

## Skill Title
Lab Result Temporal Validation and Action

## Pattern Description
When a task requires checking a lab result (e.g., HbA1C, Magnesium) and performing a conditional action based on its age or value, you must first validate the `effectiveDateTime` of the retrieved resource against the current system time. If the result is missing or exceeds the specified time threshold (e.g., 1 year for HbA1C, 24 hours for Magnesium), you must not treat it as a valid basis for clinical decision-making.

## When to Use This Skill
- When a task asks to check a lab value and perform an action if it is "old" or "within a specific timeframe".
- When a task requires ordering a new test if the existing result is outdated.
- When a task specifies a fallback action (e.g., "don't order anything") if no recent result exists.

## Common Failure Patterns
- Ignoring the `effectiveDateTime` field and using any available result regardless of age.
- Ordering a new test when the existing result is actually within the valid timeframe.
- Failing to distinguish between "no result found" and "result found but too old".
- Returning narrative text instead of the required data or action confirmation.

## Recommended Patterns

**Pattern 1: Temporal Filtering**
1. Retrieve the `Observation` bundle.
2. Parse the `effectiveDateTime` of each entry.
3. Calculate the difference between the current system time and the `effectiveDateTime`.
4. If the difference exceeds the task-defined threshold, treat the result as "not available" for the purpose of the decision logic.

**Pattern 2: Conditional Ordering**
1. If no valid result exists within the threshold, proceed to order the new test using the provided LOINC or code.
2. If a valid result exists, evaluate the value against the clinical threshold (e.g., "low").
3. Only trigger a `POST` request if the value meets the criteria for intervention.

## Example Application
**Task:** "Check HbA1C. If > 1 year old, order new test."

1. GET `.../Observation?code=A1C&patient=S0658561`
2. Inspect `effectiveDateTime`. If it is 2023-11-02 and current date is 2023-11-13, the result is < 1 year old.
3. If the result is valid, report the value. If it were > 1 year old, you would `POST` a new `ServiceRequest`.

## Success Indicators
- Agent correctly identifies if a result is stale based on the current date.
- Agent only orders new tests when the existing data is truly missing or expired.

## Failure Indicators
- Agent orders a test despite a recent, valid result being present in the bundle.
- Agent reports an old value as the "current" status without checking the date.
