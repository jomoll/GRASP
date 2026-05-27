---
description: Force structured scalar output for lab value queries and handle ordering
  when result is stale
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task1_27
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_26
  - task4_6
  - task4_27
  update_cycle: 0
tags: []
version: 2
---

# Lab Observation Query Before Finish

## Pattern Description
You must always query a FHIR Observation bundle for the requested lab code before producing any answer. Extract the **numeric value**, its **unit**, and the **effectiveDateTime** of the most recent observation. Return the result in a strict scalar array format so downstream logic can reliably parse it. If the most recent result is older than the task‑specified freshness threshold (e.g., > 1 year), place a ServiceRequest for the appropriate LOINC test **before** calling FINISH. The FINISH payload should be:
- `[value, "YYYY-MM-DD"]` when a recent result exists, **or**
- `[-1]` when no result meets the freshness criteria (after ordering if required).

## When to Use This Skill
- When the user asks for the *last* value of a lab (e.g., HbA1c, potassium, magnesium) and optionally provides a freshness rule.
- When the task description mentions a date comparison ("if older than X, order a new test").
- When the agent has just performed a `GET …/Observation?code=...&patient=...` request.

## Common Failure Patterns
- Returning a free‑form string such as `"5.9% on 2023-11-12"` instead of a scalar array.
- Returning a JSON **array** of strings (e.g., `FINISH(["5.9%","2023-11-12"])`) – the value must be a **number**, not a quoted string.
- Omitting the unit or returning the unit together with the number (e.g., `"5.9%"`).
- Failing to place a ServiceRequest when the result is stale, or placing it after FINISH.
- Returning `FINISH([-1])` without first checking the freshness rule.

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Inspect the Bundle `entry` array for the Observation with the highest `effectiveDateTime`.
2. From that Observation, read:
   - `valueQuantity.value` → numeric value
   - `valueQuantity.unit` → unit (verify it matches the expected unit for the lab)
   - `effectiveDateTime` → ISO‑8601 date string (e.g., `2023-11-12`)
3. If the value is present and the date satisfies the task’s freshness condition, call:
   ```
   FINISH([valueQuantity.value, effectiveDateTime.split('T')[0]])
   ```
   *Do not* wrap the number in quotes.

**Pattern 2: Stale result handling**
1. Compute the age of the result: `now - effectiveDateTime`.
2. If the age exceeds the threshold (e.g., 1 year), construct a ServiceRequest using the LOINC code supplied in the task context.
3. POST the ServiceRequest **before** any FINISH call.
4. After posting, call `FINISH([-1])` to indicate that no recent result is available.

**Pattern 3: No result found**
1. If the Bundle `total` is 0 or no Observation matches the code, skip ordering unless the task explicitly says to order when *no* result exists.
2. Call `FINISH([-1])` directly.

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S1311412 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S1311412`
2. Parse the returned Bundle. Suppose the most recent entry contains:
   ```json
   "valueQuantity": { "value": 5.9, "unit": "%" },
   "effectiveDateTime": "2022-10-05T08:30:00+00:00"
   ```
3. Compute age: now (2023‑11‑13) – 2022‑10‑05 ≈ 1 year + 1 month → exceeds 1 year.
4. Build ServiceRequest:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "4548-4", "display": "Hemoglobin A1c" }] },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/S1311412" },
     "note": [{ "text": "Result older than 1 year; ordering repeat test." }]
   }
   ```
5. `POST` the ServiceRequest.
6. Finally, `FINISH([-1])` because the existing result is stale.

**Correct output:** `FINISH([-1])`
**Incorrect output examples:**
- `FINISH("5.9% on 2022-10-05")`
- `FINISH(["5.9%","2022-10-05"])`
- Ordering the ServiceRequest *after* the FINISH call.

## Success Indicators
- FINISH payload is a scalar array with a numeric first element and a date string second element, or `[-1]`.
- The ServiceRequest (when required) is POSTed **before** FINISH.
- No extra explanatory text appears in the FINISH payload.

## Failure Indicators
- FINISH contains free‑form sentences or quoted numbers.
- The ServiceRequest is missing, posted after FINISH, or uses the wrong LOINC code.
- The date part of the array is missing or not in `YYYY‑MM‑DD` format.
- The agent returns an array of strings instead of a number and a date.
