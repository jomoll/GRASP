---
description: "Check CT abdomen recency and order a new study with IV contrast if the\
  \ last exam is >12\u202Fmonths old or missing."
name: ct_abdomen_stale_check_and_order
provenance:
  action: ADD
  epoch: 0
  fixes: 8
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task8_26
  - task1_20
  - task8_23
  - task9_1
  - task8_29
  - task3_10
  - task3_16
  - task2_14
  - task1_16
  - task2_6
  update_cycle: 1
tags:
- ct
- staleness
- order
- radiology
version: 1
---

# CT Abdomen Staleness Check and Order

## Pattern Description
You must verify that a patient has a recent CT Abdomen (CPT codes **IMGCT0491** or **IMGIL0001**). If the most recent study is older than 12 months, or no study exists, you must create a **ServiceRequest** (or **Procedure**) for a new CT Abdomen with IV contrast (CPT **74177**) and include the clinical indication "Renal mass follow‑up". This pattern prevents the agent from simply returning the old date without taking the required ordering action.

## When to Use This Skill
- When the task asks: *"Find the date of the most recent CT Abdomen procedure for patient X. If the study was performed more than 12 months ago, order a new CT Abdomen with IV contrast indication 'Renal mass follow‑up'."*
- When the agent has already performed a GET on `/Procedure` with `code=IMGCT0491,IMGIL0001` for the target patient.
- When the response bundle contains zero entries **or** entries whose `performedDateTime` (or `performedPeriod.end`) is >12 months before the reference date supplied in the task context.

## Common Failure Patterns
- Returning only the historic date (e.g., `FINISH(["2023-06-14"])`) without evaluating freshness.
- Using the wrong date field (`effectiveDateTime` on Observation instead of `performedDateTime` on Procedure).
- Ignoring the case where the bundle `total` is 0 (no prior study) and still not ordering.
- Comparing dates as strings without converting to a date object, causing lexical rather than chronological comparison.
- Ordering a new CT but using the wrong CPT code (e.g., 74178) or omitting the indication note.

## Recommended Patterns
**Pattern 1: Core freshness check**
1. Inspect the GET response bundle.
   - If `total == 0`, treat as *no recent study*.
   - Otherwise, extract the **most recent** `performedDateTime` (or `performedPeriod.end`) from all entries.
2. Parse the extracted date and the reference date supplied in the task (often the current date or a date string like `2023-11-07`).
3. Compute the difference in months (or days) between the reference date and the study date.
4. If the difference > 365 days **or** there was no prior study, proceed to step 5. Otherwise, skip ordering.

**Pattern 2: Ordering the new CT**
1. Build a `ServiceRequest` (or `Procedure`) JSON payload:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {
       "coding": [{
         "system": "http://www.ama-assn.org/go/cpt",
         "code": "74177",
         "display": "CT Abdomen with IV contrast"
       }]
     },
     "authoredOn": "<reference_date_time>",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/<patient_id>" },
     "note": [{ "text": "Renal mass follow‑up" }]
   }
   ```
2. POST the payload to `/fhir/ServiceRequest` (or `/fhir/Procedure` if the environment expects a Procedure).
3. After a successful POST, call `FINISH` with two messages:
   - A statement about the prior study (or lack thereof).
   - Confirmation that the new CT was ordered.

**Pattern 3: Formatting the final answer**
- Always return a **list of strings** via `FINISH([...])`.
- Example of correct output:
  ```
  FINISH([
    "No CT Abdomen (CPT IMGCT0491 or IMGIL0001) performed for patient S0658561 within the past 12 months.",
    "A new CT Abdomen with IV contrast (CPT 74177) has been ordered for renal mass follow‑up."
  ])
  ```
- Do **not** embed raw dates inside the message when the study is stale; the decision to order must be explicit.

## Example Application
**Task:** "Find the date of the most recent CT Abdomen procedure for patient **S2111822**. If the study was performed more than 12 months ago, order a new CT Abdomen with IV contrast indication 'Renal mass follow‑up'."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Procedure?patient=S2111822&code=IMGCT0491,IMGIL0001`
2. Response bundle `total = 0` → no prior study.
3. Build the ServiceRequest payload (using reference date `2023-11-07T22:47:00+00:00`).
4. `POST http://localhost:8080/fhir/ServiceRequest` with the payload.
5. `FINISH(["No CT Abdomen (CPT IMGCT0491 or IMGIL0001) performed for patient S2111822 within the past 12 months.", "A new CT Abdomen with IV contrast (CPT 74177) has been ordered for renal mass follow‑up."])`

## Success Indicators
- The agent issues a POST to `/fhir/ServiceRequest` (or `/fhir/Procedure`) **only when** the prior CT is >12 months old or missing.
- The POST payload contains CPT **74177** and the note "Renal mass follow‑up".
- The final `FINISH` output includes both the historic‑study statement **and** the order‑confirmation statement.

## Failure Indicators
- The agent finishes with only the historic date and does **not** issue a POST when the study is stale.
- The POST uses an incorrect CPT code or omits the indication note.
- Date comparison is performed incorrectly, leading to a missed order for a study that is actually >12 months old.
- The agent returns a single concatenated string instead of a list of separate messages.
