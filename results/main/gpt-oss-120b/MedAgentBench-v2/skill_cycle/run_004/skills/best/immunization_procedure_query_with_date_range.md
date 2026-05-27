---
description: Query Procedure for vaccines using CPT code and date range before ordering
name: immunization_procedure_query_with_date_range
provenance:
  action: ADD
  epoch: 0
  fixes: 8
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task6_3
  - task3_14
  - task4_11
  - task9_14
  - task3_7
  - task4_23
  - task2_30
  - task6_26
  - task6_2
  - task2_1
  update_cycle: 0
tags:
- immunization
- procedure_query
- date_range
- vaccine_order
version: 1
---

# Immunization Procedure Query with Date Range

## Pattern Description
You must retrieve a patient’s vaccination history by searching the **Procedure** endpoint with the vaccine’s CPT code and an explicit date range.  Using a date filter satisfies the required `date` parameter and limits results to a relevant window (e.g., the past year).  After obtaining the most recent procedure, decide whether a new vaccine order is needed based on the elapsed time.

## When to Use This Skill
- When a task asks to *determine the date of the last* influenza, COVID‑19, or any other vaccine and possibly order a new dose.
- When the instruction mentions a CPT code for the vaccine (e.g., `90686` for influenza, `91320` for COVID‑19 booster).
- When the task requires a comparison against a time threshold (e.g., 365 days).

## Common Failure Patterns
- **Missing GET request** – the agent proceeds directly to ordering without first querying the Procedure resource.
- **Using the wrong resource** – querying `MedicationRequest` or `Observation` instead of `Procedure` for CPT‑coded vaccines.
- **Omitting the required `date` parameter** – the API rejects the request or returns an empty bundle.
- **Providing a single date instead of a range** – e.g., `date=2023-01-01` returns only procedures on that exact day.
- **Parsing the wrong field** – extracting `authoredOn` instead of the procedure’s `performedDateTime` or `occurrenceDateTime`.

## Recommended Patterns
**Pattern 1: Core query and extraction**
1. Compute the start of the look‑back window:
   ```
   start_date = today - 365 days   # or the interval required by the task
   ```
2. Issue the GET request:
   ```
   GET {api_base}/Procedure?code={CPT_CODE}&patient={PATIENT_ID}&date=ge{start_date}&date=le{today}
   ```
   - `code` = vaccine CPT (e.g., `90686`).
   - `patient` = patient identifier (e.g., `S3114648`).
   - `date=ge…` and `date=le…` create an inclusive range.
3. Inspect the returned Bundle:
   - If `total == 0`, no vaccine in the window.
   - Otherwise, locate the entry with the **most recent** `performedDateTime` (or `occurrenceDateTime`).
   - Extract that date as `last_vax_date`.

**Pattern 2: Decision & ordering fallback**
1. If `last_vax_date` is missing **or** `today - last_vax_date > threshold` (e.g., 365 days), prepare an order.
2. Choose the appropriate resource type:
   - **MedicationRequest** for vaccines that are medication‑coded.
   - **ServiceRequest** when the protocol prefers a service request.
3. Populate the order body:
   ```json
   {
     "resourceType": "MedicationRequest",
     "medicationCodeableConcept": {
       "coding": [{"system": "http://www.ama-assn.org/go/cpt", "code": "{CPT_CODE}", "display": "{Vaccine Display}"}],
       "text": "{Vaccine Text}"
     },
     "authoredOn": "{today_iso}",
     "status": "active",
     "intent": "order",
     "subject": {"reference": "Patient/{PATIENT_ID}"},
     "dosageInstruction": [{"route": {"text": "IM"}}]
   }
   ```
4. POST the order and then `FINISH` with a concise statement.

**Pattern 3: Formatting of the final answer**
- **Correct**: `FINISH(["Last influenza vaccine was administered on 2022-12-30. New vaccine ordered for 2024-01-09."])`
- **Wrong**: `FINISH(["Patient received flu shot on 2022‑12‑30, which is >365 days ago, so we ordered a new one."])` (contains explanatory text instead of a concise result).

## Example Application
**Task**: "Determine the date of the last influenza vaccine for patient S3114648. If it was administered more than 365 days ago, order a new influenza vaccine for today."

**Step‑by‑step**:
1. `today = 2024-01-09T00:00:00Z`; `start_date = 2023-01-09`.
2. GET request:
   ```
   GET http://localhost:8080/fhir/Procedure?code=90686&patient=S3114648&date=ge2023-01-09&date=le2024-01-09
   ```
3. Response Bundle has `total = 0` → no recent flu vaccine.
4. Build MedicationRequest (see Pattern 2) with `authoredOn = 2024-01-09` and CPT `90686`.
5. POST the request.
6. FINISH:
   ```
   FINISH(["No prior influenza vaccine (CPT 90686) found for patient S3114648. A new influenza vaccine was ordered for 2024-01-09."])
   ```

## Success Indicators
- The agent issues a GET to `/Procedure` with both `code` and a `date` range before any ordering.
- The GET response is parsed and the most recent `performedDateTime` is extracted.
- An order is only created when the date check fails (or when no record exists).
- The final `FINISH` output contains only the concise result string.

## Failure Indicators
- The agent proceeds to POST without a preceding Procedure GET.
- The GET request lacks a `date` parameter or uses only a single date value.
- The agent extracts the wrong field (e.g., `authoredOn` from the order) instead of the procedure date.
- The final output includes extraneous explanation or repeats the entire order payload.
