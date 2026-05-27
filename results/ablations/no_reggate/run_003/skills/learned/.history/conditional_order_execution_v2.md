---
description: Add handling for missing lab results and required ordering
name: conditional_order_execution
provenance:
  action: MODIFY
  epoch: 3
  fixes: 9
  parent_version: 1
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task9_5
  - task9_11
  - task10_20
  - task10_13
  - task10_17
  - task10_27
  - task9_22
  update_cycle: 0
tags: []
version: 2
---

# Conditional Lab Order Execution

## Pattern Description
You must detect tasks that request the most recent value of a lab observation **and** specify a conditional order (e.g., "if the result is older than 1 year, order a new test"). The skill extracts the observation, evaluates the date/value criteria, and **always** issues a ServiceRequest when the criteria are not met, instead of returning a placeholder like `[-1]`.

## When to Use This Skill
- When a task asks for the *last* value of a lab (e.g., HbA1c, potassium, magnesium) **and** includes a conditional ordering clause.
- When the GET request for the Observation returns `total = 0` (no recent result).
- When the returned Observation exists but its `effectiveDateTime` is older than the threshold defined in the task.

## Common Failure Patterns
- `FINISH([-1])` after an empty Observation bundle – the required order was never placed.
- Returning only the numeric value without checking the date threshold.
- Placing the order **after** calling `FINISH`, so the order is never executed.

## Recommended Patterns
**Pattern 1: Core detection and extraction**
1. Issue `GET {base}/Observation?code={LOINC}&patient={MRN}` (add `date=ge{threshold}` if the task limits the window).
2. Inspect the returned Bundle:
   - `total == 0` → no recent result.
   - `total > 0` → locate the entry with the most recent `effectiveDateTime`.
3. Extract `valueQuantity.value` (or `valueString` when appropriate) and `effectiveDateTime`.

**Pattern 2: Conditional ordering rule**
- **If** `total == 0` **or** `effectiveDateTime` is older than the allowed age (e.g., > 1 year), **then**:
  1. Build a `ServiceRequest` with the ordering LOINC code supplied in the task (e.g., `4548-4` for HbA1c).
  2. POST the `ServiceRequest` **before** any `FINISH` call.
  3. Include `authoredOn` = current time, `status` = "active", `intent` = "order", `priority` = "stat", and `subject.reference` = `Patient/{MRN}`.
- **Else** (result is recent and meets any value thresholds) skip the order.

**Pattern 3: Formatting the final answer**
- When a result exists and satisfies the date/value condition, output:
  `FINISH(["{value}", "{effectiveDateTime}"])`
- When an order is placed because the result is missing or stale, still provide the best available information (or `-1` if none) **and** confirm the order was sent:
  `FINISH(["-1", "order placed"] )`

## Example Application
**Task:** "What’s the last HbA1C value for patient S0789363 and when was it recorded? If the result is > 1 year old, order a new HbA1c test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0789363`
2. Response Bundle `total = 0` → no recent HbA1c.
3. Build ServiceRequest:
```json
{
  "resourceType": "ServiceRequest",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c" }] },
  "authoredOn": "2023-11-13T10:15:00+00:00",
  "status": "active",
  "intent": "order",
  "priority": "stat",
  "subject": { "reference": "Patient/S0789363" }
}
```
4. `POST` the ServiceRequest.
5. `FINISH(["-1", "order placed"])`

## Success Indicators
- A `POST` to `/ServiceRequest` is observed **before** any `FINISH`.
- `FINISH` never contains a raw placeholder array like `[-1]` without an accompanying order note.
- When a valid observation exists, the output includes both the value and the ISO‑8601 timestamp.

## Failure Indicators
- `FINISH` is called with only `[-1]` after an empty Observation bundle.
- No `POST /ServiceRequest` is made when the task explicitly requires ordering.
- The agent orders *after* calling `FINISH`, causing the order to be ignored.
