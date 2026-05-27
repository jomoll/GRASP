---
description: "Query the Immunization resource for any vaccine\u2011related status\
  \ check instead of Procedure"
name: use_immunization_resource_for_vaccines
provenance:
  action: ADD
  epoch: 1
  fixes: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task3_10
  - task4_10
  - task3_30
  - task1_13
  - task8_29
  - task6_23
  - task3_16
  - task10_12
  - task6_26
  - task3_29
  update_cycle: 0
tags: []
version: 1
---

# Use Immunization Resource for Vaccine Queries

## Pattern Description
You must treat vaccine status checks as a distinct reusable pattern.  Vaccines are recorded in the **Immunization** resource, not in Procedure or MedicationRequest (except for rare legacy data).  By always querying Immunization first you avoid the common mistake of searching the wrong resource type, which leads to false‑negative results and unnecessary orders.

## When to Use This Skill
- When a task asks to *review*, *verify*, or *determine* the status of any vaccine (e.g., COVID‑19, influenza, pneumococcal, hepatitis B).
- When the instruction includes a vaccine code, name, or text hint (e.g., `COVIDVACCINE`, `influenza vaccine`, `COVID‑19 VAC`).
- When the task requires a decision based on the *date of the most recent dose* (e.g., “if last dose > 12 months, order booster”).

## Common Failure Patterns
- Querying `GET /Procedure?...code=COVIDVACCINE` instead of `GET /Immunization?...vaccine-code=...`.
- Receiving an empty Procedure bundle and concluding the patient is unvaccinated.
- Mixing MedicationRequest and Procedure results, causing duplicate or contradictory orders.
- Using a generic code that exists in multiple resources without confirming the resource type.

## Recommended Patterns
**Pattern 1: Primary vaccine lookup**
1. Identify the vaccine of interest from the task description.
2. Construct a GET request to the Immunization endpoint using the appropriate vaccine code or text search.
   - Example (COVID‑19): `GET http://localhost:8080/fhir/Immunization?patient={patient_id}&vaccine-code=COVIDVACCINE`
   - Example (influenza CPT 90686): `GET http://localhost:8080/fhir/Immunization?patient={patient_id}&vaccine-code=90686`
3. Inspect the returned Bundle:
   - If `total > 0`, extract the most recent `occurrenceDateTime` from the entry with the highest date.
   - If `total == 0`, treat as *no prior vaccination*.

**Pattern 2: Fallback verification**
- If the Immunization query returns an error or empty bundle, optionally query MedicationRequest for vaccine‑related orders as a secondary check (e.g., `GET /MedicationRequest?patient={id}&text=COVID`).
- Do **not** fall back to Procedure unless the system explicitly documents vaccines as procedures.

**Pattern 3: Decision & ordering**
- Compare the extracted date (or lack thereof) to the required interval (e.g., 12 months).
- If a booster is needed, create a **MedicationRequest** or **ServiceRequest** for the booster CPT code (e.g., `91320` for COVID‑19 booster) with:
  ```json
  {
    "resourceType": "MedicationRequest",
    "medicationCodeableConcept": { "coding": [{ "system": "http://www.ama-assn.org/go/cpt", "code": "91320", "display": "COVID‑19 vaccine booster" }] },
    "authoredOn": "{today_iso}",
    "status": "active",
    "intent": "order",
    "subject": { "reference": "Patient/{patient_id}" }
  }
  ```
- If no booster is needed, FINISH with a concise statement that includes the last vaccination date.

## Example Application
**Task:** "Review COVID‑19 vaccination status for patient S0547588. Find the most recent COVID‑19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Immunization?patient=S0547588&vaccine-code=COVIDVACCINE`
2. Response Bundle has `total = 0` → no prior COVID‑19 immunization.
3. Since no record, a booster is required.
4. POST a MedicationRequest for CPT 91320 with `authoredOn` set to today’s date.
5. FINISH: `FINISH(["No COVID‑19 vaccination record found for patient S0547588. A COVID‑19 booster (CPT 91320) was ordered today."])`

## Success Indicators
- The agent issues a GET to `/Immunization` (or `/Immunization?...vaccine-code=`) before any FINISH.
- The extracted date comes from the `occurrenceDateTime` field of an Immunization resource.
- Booster orders are created only when the interval condition is met or when no prior record exists.
- FINISH output mentions the vaccine type and, if applicable, the date of the last dose.

## Failure Indicators
- The agent queries `/Procedure` for a vaccine code and proceeds to FINISH without checking Immunization.
- The agent extracts dates from `Procedure.performedDateTime` for vaccines.
- A booster is ordered despite a recent Immunization record within the required interval.
- FINISH output contains vague language like “no record found” without confirming the resource type used.
