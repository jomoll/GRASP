---
description: Enforce strict conditional logic for ServiceRequest creation based on
  data availability and threshold checks.
name: conditional_service_request_logic
provenance:
  action: ADD
  epoch: 0
  fixes: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_26
  - task10_20
  - task9_9
  - task2_22
  - task4_28
  - task10_8
  - task10_15
  - task4_15
  - task2_28
  - task2_17
  update_cycle: 0
tags:
- service_request
- conditional_logic
- lab_orders
version: 1
---

# Conditional ServiceRequest Logic

## Pattern Description
When a task requires an action (like ordering a lab test) based on the presence or age of a previous result, you must first perform a search to retrieve the relevant data. You must then evaluate the retrieved data against the specific criteria provided in the task (e.g., "if > 1 year old" or "if no result exists"). Do not create a `ServiceRequest` unless the data explicitly confirms the condition for the order is met.

## When to Use This Skill
- When the task instruction includes a conditional trigger for a `ServiceRequest` (e.g., "If the lab value is > 1 year old, order a new test").
- When the task specifies that no action should be taken if a recent result exists or if no result is found.
- When you are tempted to create a `ServiceRequest` without first verifying the existence or age of the most recent relevant `Observation`.

## Common Failure Patterns
- Creating a `ServiceRequest` automatically without checking if a recent result already exists.
- Misinterpreting the absence of a result as a trigger to order, when the task implies only ordering if a *stale* result exists or if the patient needs a new one.
- Failing to calculate the time difference between the current date and the `effectiveDateTime` of the retrieved `Observation`.

## Recommended Patterns

**Pattern 1: Data Retrieval and Verification**
1. Perform a `GET` request for the relevant `Observation`.
2. If the `Bundle` returns `total: 0`, check the task instructions: does "no result" mean you should order, or do nothing? If the task is silent, do not order.
3. If results exist, extract the most recent `effectiveDateTime`.
4. Compare the `effectiveDateTime` with the current date provided in the context.

**Pattern 2: Conditional Execution**
- If the condition (e.g., `age > 1 year`) is met, proceed with the `POST` request.
- If the condition is NOT met, do not create the `ServiceRequest`. Instead, report the findings in your `FINISH` call.

## Example Application
**Task:** "If the HbA1C result is > 1 year old, order a new test."

**Step-by-step:**
1. `GET` the `Observation` for the patient.
2. If the most recent `effectiveDateTime` is "2022-03-08" and today is "2023-11-13", the difference is > 1 year.
3. Proceed to `POST` the `ServiceRequest`.
4. If the date was "2023-10-13", do not `POST`. Call `FINISH` stating the result is recent and no order is needed.

## Success Indicators
- No `ServiceRequest` is created when the existing data is within the required threshold.
- `ServiceRequest` is only created when the specific criteria (e.g., age, absence) are explicitly satisfied.

## Failure Indicators
- `ServiceRequest` created despite a recent, valid lab result being present in the chart.
