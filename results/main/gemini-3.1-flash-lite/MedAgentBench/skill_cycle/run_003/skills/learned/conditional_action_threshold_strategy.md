---
description: Enforce strict conditional logic to prevent redundant GET requests and
  unnecessary POST actions when thresholds are not met.
name: conditional_action_threshold_strategy
provenance:
  action: MODIFY
  epoch: 7
  fixes: 5
  parent_version: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task5_7
  - task10_8
  - task3_1
  - task10_10
  - task9_9
  - task9_8
  - task10_15
  - task9_20
  - task10_16
  - task5_17
  update_cycle: 0
tags:
- fhir
- conditional-logic
- api-optimization
version: 2
---

## Skill Title
Conditional Action Threshold Strategy

## Pattern Description
Prevent unnecessary API actions (GET or POST) when the clinical data does not meet the criteria for intervention. If a search for a specific code or condition returns data that fails the threshold check, you must immediately terminate the task with a FINISH call. Do not perform secondary searches or follow-up orders if the primary data indicates no action is required.

## When to Use This Skill
- When a task requires checking a lab value (e.g., Potassium, Magnesium, HbA1C) against a threshold.
- When a task involves a conditional sequence: "If X is low/old, then do Y".
- When you have already performed a search for a clinical code and the result is sufficient to determine that no further action is needed.

## Common Failure Patterns
- Performing a second GET request for a synonymous code (e.g., 'K' after '2823-3') when the first search already provided the necessary value.
- Proceeding to POST a ServiceRequest or MedicationRequest when the clinical data (e.g., lab value or date) does not meet the specified criteria.
- Failing to stop after a negative result, leading to redundant API calls.

## Recommended Patterns

**Pattern 1: Early Termination**
If the retrieved data confirms the condition for action is not met (e.g., lab value is within normal range, or date is within the allowed window), call `FINISH` immediately with a clear explanation. Do not perform any further GET or POST requests.

**Pattern 2: Redundancy Check**
Before issuing a GET request, check if you have already retrieved the necessary information from a previous search. If the previous search for a synonymous code (e.g., LOINC vs common name) returned the required data, do not issue a second search.

**Pattern 3: Threshold Verification**
Explicitly compare the retrieved value against the threshold provided in the task description before constructing any POST body. If the value is not low/high/old, do not construct the POST request.

## Example Application

**Task:** "Check potassium. If low, order replacement. Also pair with morning lab."

**Step-by-step:**
1. GET `.../Observation?code=2823-3`.
2. If the result is 3.8 mmol/L (threshold 3.5), do not search for 'K'.
3. Call `FINISH(["Potassium is 3.8 mmol/L, no action required."])`.

## Success Indicators
- No redundant GET requests in the trace.
- No POST requests issued when the clinical threshold is not met.
- Task terminates immediately after the first sufficient data retrieval.

## Failure Indicators
- Multiple GET requests for the same clinical concept.
- POST requests appearing in the trace when the lab value is normal or the date is recent.
