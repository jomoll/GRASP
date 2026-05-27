---
description: Evaluate observation dates and conditionally create a ServiceRequest
  for a new lab when the result is stale
name: lab_result_recency_evaluation_and_ordering
provenance:
  action: ADD
  blind_select: random
  epoch: 3
  fixes_unused: 3
  probe_score_unused: 0
  regressions_unused: 5
  triggering_sample_ids:
  - task9_1
  - task8_5
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task8_7
  - task10_20
  update_cycle: 0
tags:
- lab
- date
- ordering
- recency
version: 1
---

# Lab Result Recency Evaluation and Conditional Ordering

## Pattern Description
You must evaluate the timestamp of a retrieved Observation before deciding what to return.  This pattern extracts the `valueQuantity` (or `valueString`) **and** the `effectiveDateTime` of a lab result, compares the date to the current context time, and, if the result is older than a task‑specified threshold (e.g., > 1 year), automatically creates a `ServiceRequest` for a repeat lab using the LOINC code supplied in the task description.  The final answer should include the latest value **and** date, and, when an order is required, a concise instruction to place the order.

## When to Use This Skill
- When a task asks for the "last *X* lab value" **and** adds a clause such as "If the result date is greater than *N* old, order a new *X* test".
- When the task provides the LOINC code for the repeat test (e.g., `4548-4` for HbA1c).
- When the task expects a two‑element answer (value, date) **or** a combined answer that also includes an order action.

## Common Failure Patterns
- Returning only the value and date without checking the age of the result.
- Omitting the conditional `ServiceRequest` when the result is stale.
- Creating a `ServiceRequest` unconditionally (even when the result is recent).
- Formatting the answer as a free‑text sentence instead of the required array structure.

## Recommended Patterns
**Pattern 1: Extract and parse observation**
1. Issue `GET {api_base}/Observation?code={code}&patient={mrn}`.
2. From the first entry in the Bundle, read:
   - `valueQuantity.value` (or `valueString`) → `lab_value`.
   - `effectiveDateTime` → `result_date` (ISO‑8601 string).
3. Convert `result_date` to a datetime object.

**Pattern 2: Compare to current time**
1. Obtain the current time from the task context (e.g., `2023-11-13T10:15:00+00:00`).
2. Compute the difference: `age = current_time - result_date`.
3. If the task specifies a threshold (e.g., "greater than 1 year"), translate it to days (`>365`).
4. Set flag `needs_order = age.days > 365`.

**Pattern 3: Conditional ServiceRequest creation**
- **If `needs_order` is true**:
  1. Build a `ServiceRequest` JSON payload:
     ```json
     {
       "resourceType": "ServiceRequest",
       "status": "active",
       "intent": "order",
       "code": { "coding": [{ "system": "http://loinc.org", "code": "{repeat_loinc}" }] },
       "subject": { "reference": "Patient/{mrn}" },
       "authoredOn": "{current_time}",
       "note": [{ "text": "Repeat {lab_name} ordered because prior result is > {threshold} old." }]
     }
     ```
  2. `POST {api_base}/ServiceRequest` with the payload.
  3. Include a concise order note in the final answer, e.g., `"Order placed: HbA1c (LOINC 4548-4)"`.
- **If `needs_order` is false**: do **not** create a ServiceRequest.

**Pattern 4: Final answer formatting**
- **When no order is needed**: `FINISH(["{lab_value} {unit}", "{result_date}"])`.
- **When an order is needed**: `FINISH(["{lab_value} {unit}", "{result_date}", "Order placed: {lab_name} (LOINC {repeat_loinc})"])`.

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S2823623 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test. LOINC for ordering is 4548-4."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S2823623`.
2. Extract `valueQuantity.value = 5.0`, `valueQuantity.unit = "%"`, `effectiveDateTime = "2022-10-01T08:30:00+00:00"`.
3. Current time from context: `2023-11-13T10:15:00+00:00` → age ≈ 408 days > 365 → `needs_order = true`.
4. Build and `POST` ServiceRequest with LOINC `4548-4` for patient `S2823623`.
5. Return:
   ```
   FINISH(["5.0 %", "2022-10-01", "Order placed: HbA1c (LOINC 4548-4)"])
   ```

## Success Indicators
- The agent compares the observation date to the provided current time.
- A ServiceRequest is only posted when the age exceeds the task‑specified threshold.
- The final FINISH output contains the value, date, and an order note **only** when appropriate.

## Failure Indicators
- The agent returns value/date without any date comparison.
- A ServiceRequest is posted regardless of the result age.
- The FINISH output includes an order note when the result is recent, or omits it when the result is stale.
- The answer is a free‑text sentence instead of the required array structure.
