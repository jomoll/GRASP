---
description: "Require non\u2011empty FINISH with lab value/date after ordering when\
  \ task asks for last lab result"
name: order_creation_confirmation
provenance:
  action: MODIFY
  epoch: 4
  fixes: 11
  parent_version: 1
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - task8_23
  - task8_5
  - task10_24
  - task10_21
  - task10_20
  - task10_16
  - task8_29
  - task8_15
  update_cycle: 0
tags:
- order
- confirmation
- lab_lookup
- value_timestamp
version: 2
---

# Order Creation Confirmation with Required Answer Payload

## Pattern Description
You must ensure that any `FINISH` response after creating a FHIR order (e.g., `ServiceRequest`, `MedicationRequest`) is not only non‑empty but also contains the answer the user asked for.  This is especially important for tasks that request the *most recent lab value* together with the *date it was recorded* and conditionally order a new test if the result is missing or stale.  The skill forces the agent to return the required value‑timestamp payload (or the appropriate sentinel) even when an order is placed.

## When to Use This Skill
- When the task description includes phrases like "last **[lab]** value", "when was it recorded", "if the result is older than", or "order a new **[lab]** test".
- After a `POST` of a `ServiceRequest` (or other order resource) within the same task.
- For any lab‑lookup query where the answer is a numeric value and an ISO‑8601 timestamp (or sentinel `-1` when unavailable).

## Common Failure Patterns
- `FINISH([])` after a successful order creation.
- `FINISH(["ServiceRequest created"])` – only a confirmation string, no lab answer.
- Returning the value but omitting the timestamp, or vice‑versa.
- Using the wrong sentinel format (e.g., `"-1"` as a string).

## Recommended Patterns
**Pattern 1: Detect a value‑timestamp query**
1. Scan the task description for keywords: `last`, `value`, `recorded`, `date`, `older than`, `order new`.
2. If any are present, set `requires_answer = true`.

**Pattern 2: After a POST order, construct the FINISH payload**
- If `requires_answer` is true:
  - If the prior GET returned a recent observation, extract:
    - `valueQuantity.value` (numeric) → `lab_value`
    - `effectiveDateTime` (ISO‑8601) → `lab_date`
    - `FINISH([lab_value, lab_date])`
  - If no observation or it is older than the threshold:
    - Place the order (POST).
    - Return sentinel: `FINISH([-1, null])` (or `FINISH([-1])` if the spec expects a single‑element array).
- If `requires_answer` is false, any non‑empty FINISH (e.g., `FINISH(["ServiceRequest created"])`) is acceptable.

**Pattern 3: Validation before finishing**
- Verify the FINISH array length matches the expected answer shape (2 for value‑timestamp, 1 for simple confirmations).
- Ensure numeric elements are numbers, not strings, and dates are valid ISO‑8601 strings.

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S0789363 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0789363`
2. No recent observation (`total = 0`).
3. Detect value‑timestamp query → `requires_answer = true`.
4. `POST` a `ServiceRequest` for LOINC `4548-4`.
5. Because no result exists, return sentinel: `FINISH([-1, null])`.

**Correct output:** `FINISH([-1, null])`
**Wrong output:** `FINISH([])` or `FINISH(["ServiceRequest created"])`

## Success Indicators
- `FINISH` contains an array with the expected number of elements (value and date) after an order.
- Numeric value is a number, date is a valid ISO‑8601 string, or sentinel `-1`/`null` when appropriate.
- No empty array is returned for value‑timestamp tasks.

## Failure Indicators
- `FINISH([])` after a POST when the task asked for a lab value/date.
- `FINISH` contains only a textual confirmation without the required answer.
- Incorrect data types (e.g., value as a string) or malformed dates.
