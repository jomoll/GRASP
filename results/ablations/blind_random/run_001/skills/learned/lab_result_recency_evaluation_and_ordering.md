---
description: Add explicit date comparison and conditional ServiceRequest creation
  for stale lab results
name: lab_result_recency_evaluation_and_ordering
provenance:
  action: MODIFY
  blind_select: random
  epoch: 3
  fixes_unused: 2
  parent_version: 1
  probe_score_unused: 0
  regressions_unused: 1
  triggering_sample_ids:
  - task9_9
  - task10_15
  - task8_23
  - task8_3
  - task8_19
  - task9_28
  - task8_14
  - task5_17
  - task8_9
  - task9_3
  update_cycle: 1
tags: []
version: 2
---

# Lab Result Recency Evaluation and Conditional Ordering

## Pattern Description
You must evaluate the freshness of a lab Observation before deciding whether to simply report its value or to order a repeat test. The core capability is to extract the most recent `effectiveDateTime` (or `issued`) from the Observation bundle, compare it to the current time supplied in the task context, and trigger a ServiceRequest only when the result is older than a defined threshold (e.g., 1 year). This pattern prevents the agent from ignoring the date condition and always returning the last value.

## When to Use This Skill
- When a task asks for the *last* value of a lab (e.g., HbA1c, potassium, magnesium) **and** includes a conditional ordering clause based on the result date.
- When the task provides the current timestamp (e.g., "It's 2023-11-13T10:15:00+00:00 now") and a LOINC code for ordering a repeat test.
- When the Observation search may return zero, one, or many entries.

## Common Failure Patterns
- Ignoring the `effectiveDateTime` field and always returning the value regardless of age.
- Using the wrong date field (`issued` vs `effectiveDateTime`).
- Failing to create a ServiceRequest when the result is older than the threshold.
- Returning a placeholder `[-1]` without ordering when the result is stale.

## Recommended Patterns
**Pattern 1: Core recency evaluation**
1. After a `GET /Observation?...` call, locate the entry with the most recent `effectiveDateTime` (or `issued`).
2. Extract:
   - `valueString` or `valueQuantity.value` as `lab_value`.
   - `effectiveDateTime` as `lab_date` (ISO‑8601 string).
3. Parse `lab_date` and the `current_time` supplied in the task context.
4. Compute the difference in days. If `current_time - lab_date > 365` days, mark the result **stale**.
5. If the bundle `total` is 0, treat as stale.

**Pattern 2: Conditional ordering fallback**
- If the result is stale **or** missing, construct a `POST /ServiceRequest` with:
  ```json
  {
    "resourceType": "ServiceRequest",
    "status": "active",
    "intent": "order",
    "priority": "stat",
    "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC_ORDER_CODE>", "display": "<Display>" }] },
    "subject": { "reference": "Patient/<MRN>" },
    "authoredOn": "<CURRENT_TIME>",
    "note": [{ "text": "Order placed: repeat test due to missing or outdated result" }]
  }
  ```
- Replace `<LOINC_ORDER_CODE>` with the ordering LOINC supplied in the task (e.g., `4548-4` for HbA1c).
- After a successful POST, call `FINISH([-1])` to indicate that a new order was placed.

**Pattern 3: Formatting the normal answer**
- If the result is **fresh**, call `FINISH([lab_value, lab_date])` where both elements are plain strings (no extra explanatory text).
- Do **not** wrap the answer in additional sentences or JSON objects.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6545016 and when was it recorded? If the result is > 1 year old, order a new HbA1c test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6545016`
2. Parse the bundle. Suppose the most recent entry has:
   - `valueString`: `"5.7 %"`
   - `effectiveDateTime`: `"2022-06-01T09:00:00+00:00"`
3. Current time from context: `"2023-11-13T10:15:00+00:00"` → difference ≈ 531 days → **stale**.
4. Build and `POST` a ServiceRequest using the ordering LOINC `4548-4`.
5. After POST succeeds, `FINISH([-1])`.

If the observation had `effectiveDateTime` of `"2023-07-07T00:00:00+00:00"` (less than 365 days), the agent would:
- `FINISH(["5.7 %", "2023-07-07"])`.

## Success Indicators
- The agent extracts both `lab_value` and `lab_date` when the result is fresh.
- The agent creates a ServiceRequest **only** when the result is stale or missing.
- The final `FINISH` payload matches the exact format described (array of two strings or `[-1]`).

## Failure Indicators
- The agent returns a value without checking the date, even when the result is > 1 year old.
- The agent posts a ServiceRequest but still includes the stale value in the `FINISH` array.
- The `FINISH` output contains extra explanatory text or is wrapped in an object.
