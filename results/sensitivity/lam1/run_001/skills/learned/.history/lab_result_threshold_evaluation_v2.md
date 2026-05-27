---
description: "Add recency check for lab results and trigger ordering when result is\
  \ older than 1\u202Fyear"
name: lab_result_threshold_evaluation
provenance:
  action: MODIFY
  epoch: 1
  fixes: 9
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task5_7
  - task9_27
  - task9_14
  - task9_20
  update_cycle: 0
tags: []
version: 2
---

# Lab Result Recency Evaluation and Ordering

## Pattern Description
You must evaluate not only the numeric value of a lab result but also its age. For any task that asks for the *last* value of a lab (e.g., HbA1c, potassium, magnesium) and includes a conditional ordering clause based on the result date, first determine whether the most recent observation is newer than the allowed freshness window (default = 1 year). If the observation is missing **or** older than the window, automatically create a `ServiceRequest` for the appropriate LOINC test before finishing.

## When to Use This Skill
- The task description references a lab code (e.g., "HbA1c", "potassium", "magnesium") and asks for the *last* value.
- The description contains a conditional phrase such as "if the result is older than X" or "if no recent result, order a new test".
- A current timestamp is provided in the task context (e.g., `2023-11-13T10:15:00+00:00`).

## Common Failure Patterns
- Using only the numeric value to decide ordering, ignoring the observation's `effectiveDateTime`.
- Treating an empty result set as "no ordering needed" instead of triggering a new test.
- Comparing dates as strings rather than proper ISO‑8601 date arithmetic, leading to false‑negative recency checks.

## Recommended Patterns
**Pattern 1: Retrieve the most recent observation**
1. Issue `GET {api_base}/Observation?code={LOINC_CODE}&patient=Patient/{MRN}&_sort=-date&_count=1`.
2. Verify the response is a `Bundle` with `total >= 1`.
3. Extract `effectiveDateTime` (ISO‑8601) and the numeric value (`valueQuantity.value`).

**Pattern 2: Compute recency**
1. Parse the `effectiveDateTime` and the current time supplied in the task context.
2. Compute the difference in days (or years). Use a threshold of **365 days** (1 year) unless the task specifies otherwise.
3. Set a boolean `is_recent = (current_time - effectiveDateTime) <= 365 days`.

**Pattern 3: Conditional ordering**
- **If `total == 0` OR `is_recent == false`**:
  1. Build a `ServiceRequest` with:
     ```json
     {
       "resourceType": "ServiceRequest",
       "code": { "coding": [{ "system": "http://loinc.org", "code": "{ORDER_LOINC}", "display": "{ORDER_DISPLAY}" }] },
       "authoredOn": "{CURRENT_TIME}",
       "status": "active",
       "intent": "order",
       "priority": "stat",
       "subject": { "reference": "Patient/{MRN}" },
       "note": { "text": "Order new {ORDER_DISPLAY} test as no recent result is available." }
     }
     ```
  2. `POST {api_base}/ServiceRequest` with the body above.
- **Otherwise** (result is recent): skip ordering.

**Pattern 4: Finish output**
- If a recent result exists, return `FINISH([value, "recorded on", effectiveDateTime])` (numeric value and ISO timestamp).
- If a new order was placed, return `FINISH([-1])` or a message indicating the order.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6550627 and when was it recorded? If the result is older than 1 year, order a new HbA1c test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=Patient/S6550627&_sort=-date&_count=1`
2. Response `total = 0` → no recent observation.
3. Build and `POST` a `ServiceRequest` with LOINC `4548-4` (Hemoglobin A1c).
4. `FINISH([-1])`.

**Correct output:** `FINISH([-1])` (order placed, no recent value).
**Incorrect output:** `FINISH(["Last HbA1C value is 5.7% recorded on 2023-07-07T11:27:00+00:00. No new test ordered."])` – missed the recency rule.

## Success Indicators
- A `GET` to the Observation endpoint includes sorting (`_sort=-date`) and a count limit.
- The agent computes the date difference and creates a `ServiceRequest` whenever the observation is missing or older than 1 year.
- The final `FINISH` payload matches the pattern described above.

## Failure Indicators
- The agent finishes with a recent value without checking its age.
- No `ServiceRequest` is posted when the observation is absent or stale.
- Date comparison is performed as string equality rather than arithmetic, causing false positives.
