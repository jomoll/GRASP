---
description: Prevents unnecessary HbA1C lab orders by enforcing a recency check before
  ordering.
name: lab_recency_check_before_hba1c_order
provenance:
  action: ADD
  epoch: 2
  fixes: 7
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task9_8
  - task10_16
  - task9_5
  - task10_21
  - task10_10
  - task9_20
  - task10_13
  - task9_22
  - task10_12
  update_cycle: 0
tags:
- lab
- order
- recency
- HbA1C
- threshold
- decision-logic
version: 1
---

# Lab Recency Check Before HbA1C Order

## Pattern Description

When a clinical task requests the most recent HbA1C (hemoglobin A1C) value and instructs to order a new HbA1C lab only if the last result is older than a specified recency threshold (commonly 1 year), you must always check the date of the latest available result before placing a new order. This prevents unnecessary or duplicate lab orders and ensures that only clinically indicated tests are requested.

This pattern applies to any lab or measurement where the task specifies a recency threshold for reordering, but is especially common for HbA1C monitoring in diabetes care. The agent must extract the date of the most recent result, compare it to the current time, and only proceed with a new order if the threshold is exceeded.

## When to Use This Skill

- When the task requests the most recent HbA1C value and specifies to order a new test only if the last result is older than a given threshold (e.g., 1 year).
- When the agent retrieves a list of past HbA1C Observations and must decide whether to POST a new ServiceRequest for HbA1C.
- When the instruction includes conditional ordering based on lab result recency.

## Common Failure Patterns

- Placing a new HbA1C order without checking the date of the last result.
- Ordering a new HbA1C even when a recent (within threshold) result is available.
- Comparing the wrong date field (e.g., using `issued` instead of `effectiveDateTime`).
- Failing to extract the most recent result when multiple are present.
- Using a hardcoded or incorrect threshold (e.g., not matching the task's specified interval).

## Recommended Patterns

Pattern 1: Extract and Compare Recency
1. Issue a GET request for HbA1C Observations for the patient (e.g., `GET /Observation?code=A1C&patient={id}`).
2. Extract all entries and identify the most recent result by comparing the `effectiveDateTime` fields.
3. Compare the most recent `effectiveDateTime` to the current time. Calculate the interval (e.g., days or years).
4. If the most recent result is within the specified threshold (e.g., less than 1 year old), do NOT place a new order. Only return the value and date.
5. If the most recent result is older than the threshold, proceed to POST a new ServiceRequest for HbA1C.

Pattern 2: Fallback for No Results
- If no HbA1C Observations are found, treat as "no recent result" and proceed to order a new HbA1C.

Pattern 3: Output Formatting
- When returning the result, output the value and date in the required format (e.g., `[value, date]`).
- If a new order is placed, ensure the POST body uses the correct LOINC code and patient reference.

## Example Application

**Task:** "What’s the last HbA1C value in the chart for patient S6521727 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step-by-step:**

1. GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6521727
2. Extract all entries, find the one with the latest `effectiveDateTime` (e.g., "2022-09-09T15:33:00+00:00").
3. Compare to current time (e.g., "2023-11-13T10:15:00+00:00"). The result is ~14 months old (>1 year).
4. Since the result is older than 1 year, POST a new ServiceRequest for HbA1C (LOINC 4548-4).
5. Return the last value and date in the required format.

CORRECT:
- If last result is within 1 year: `FINISH([5.4, "2023-11-02T06:53:00+00:00"])` (no new order)
- If last result is >1 year old: POST ServiceRequest, then `FINISH([5.8, "2022-09-09T15:33:00+00:00"])`

WRONG:
- POSTing a new ServiceRequest when a recent result is available.
- Failing to POST when no recent result exists.

## Success Indicators

- No new HbA1C order is placed if a recent result is available within the specified threshold.
- A new HbA1C order is placed only when the last result is older than the threshold or missing.
- The returned answer includes both the value and the date in the required format.

## Failure Indicators

- Unnecessary POST ServiceRequest for HbA1C when a recent result is present.
- Missing or incorrect comparison of result date to current time.
- Returning only the value or only the date, not both.
- Using the wrong date field or threshold interval.
