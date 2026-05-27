---
description: "Apply date\u2011based conditional logic to order a lab test when the\
  \ latest result is older than a given threshold."
name: conditional_lab_result_age_order
provenance:
  action: ADD
  epoch: 1
  fixes: 9
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task2_17
  - task9_28
  - task4_15
  - task9_22
  - task8_15
  - task4_23
  - task2_25
  - task2_9
  update_cycle: 0
tags:
- conditional_logic
- lab_ordering
- observation_age
version: 1
---

# Conditional Lab Result Age Evaluation and Ordering

## Pattern Description
You must evaluate the timestamp of the most recent Observation you have just extracted and decide whether a follow‑up ServiceRequest is required. This pattern is reusable for any lab result where the task specifies a maximum acceptable age (e.g., "order a new HbA1c if the last result is > 1 year old"). The skill isolates the decision step from the raw value extraction so that downstream logic is never skipped.

## When to Use This Skill
- When a task asks for the *latest* value of a lab Observation **and** adds a conditional clause based on the result’s `effectiveDateTime` (or `issued`).
- When the task provides a time threshold such as "greater than 1 year old", "older than 30 days", etc.
- When the agent has already performed the Observation lookup and extracted the raw numeric value (via `observation_lookup_and_value_extraction`).

## Common Failure Patterns
- The agent finishes with the extracted value and never evaluates the date condition, resulting in missing ServiceRequest creation.
- The agent compares the wrong field (`issued` vs `effectiveDateTime`) or treats the date string as a plain string instead of a datetime.
- The threshold is mis‑interpreted (e.g., using days instead of years) causing premature or omitted orders.
- The agent returns a human‑readable summary instead of a pure numeric payload, breaking downstream numeric checks.

## Recommended Patterns
**Pattern 1: Extract and parse the result date**
1. After `observation_lookup_and_value_extraction` returns `[value, dateString]`, store `dateString`.
2. Parse `dateString` into an ISO‑8601 datetime object (e.g., using `datetime.fromisoformat`).
3. Retrieve the current task context time (`now`) supplied in the prompt.
4. Compute the age: `age = now - resultDate`.

**Pattern 2: Compare against the supplied threshold**
- Identify the threshold unit in the instruction ("1 year", "30 days", etc.).
- Convert the threshold to a `timedelta` (`years → 365 days`).
- If `age > threshold` → **order required**.
- Else → **no order**.

**Pattern 3: Create the ServiceRequest only when needed**
- Build a minimal `ServiceRequest` JSON with:
  ```json
  {
    "resourceType": "ServiceRequest",
    "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC>", "display": "<Lab Name>" }] },
    "authoredOn": "<now>",
    "status": "active",
    "intent": "order",
    "priority": "stat",
    "subject": { "reference": "Patient/<MRN>" },
    "note": { "text": "Order new <Lab Name> as previous result is older than <threshold>." }
  }
  ```
- POST to `/fhir/ServiceRequest` and then `FINISH` with the appropriate payload (e.g., `[-1]` for "no recent result", or the numeric value and date when the result is recent).

## Example Application
**Task:** "What’s the last HbA1C value for patient S2823623 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET /Patient?identifier=S2823623` (ensured by `ensure_fhir_call_for_patient_and_observation`).
2. `GET /Observation?code=A1C&patient=S2823623`.
3. `observation_lookup_and_value_extraction` returns `["5.0%", "2022-10-01T09:00:00+00:00"]`.
4. Parse the date (`2022‑10‑01`). Current time from context: `2023‑11‑13T10:15:00+00:00`.
5. Compute age ≈ 1 year + 1 month → exceeds 1 year threshold.
6. Build ServiceRequest with LOINC `4548-4` (HbA1c) and POST.
7. `FINISH([-1])` (or a custom payload indicating the order was placed).

**Correct output:**
```json
FINISH([-1])
```
**Wrong output (missing conditional logic):**
```json
FINISH(["5.0%", "2022-10-01T09:00:00+00:00"])
```

## Success Indicators
- The agent posts a `ServiceRequest` **only** when the result age exceeds the threshold.
- The final `FINISH` payload matches the task’s expected format (e.g., `[-1]` for "order placed" or the raw value/date when no order is needed).
- Log entries show the date parsing and threshold comparison steps.

## Failure Indicators
- No `ServiceRequest` POST appears despite the result being older than the threshold.
- The agent finishes with the raw value/date without evaluating the age condition.
- The posted `ServiceRequest` uses the wrong LOINC code or omits required fields (`status`, `intent`, `subject`).
- The agent compares the wrong timestamp field or treats the date string as a plain string, leading to incorrect age calculation.
