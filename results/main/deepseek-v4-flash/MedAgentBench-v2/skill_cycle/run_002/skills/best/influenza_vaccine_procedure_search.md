---
description: Search Procedure resource for vaccine records with fallback to MedicationRequest
name: influenza_vaccine_procedure_search
provenance:
  action: MODIFY
  epoch: 3
  fixes: 5
  parent_version: 2
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task3_16
  - task10_8
  - task8_14
  - task10_18
  - task2_17
  - task3_27
  - task2_14
  - task9_11
  - task1_20
  - task1_15
  update_cycle: 0
tags: []
version: 3
---

# Vaccine Procedure Search with MedicationRequest Fallback

## Pattern Description

This skill provides a systematic approach to searching for vaccine administration records in FHIR. The primary search targets the Procedure resource using the vaccine's CPT or CVX code. When the Procedure search returns zero results, the skill automatically falls back to searching the MedicationRequest resource using text-based matching on the vaccine name. This two-step strategy ensures comprehensive coverage since vaccine records may be stored in either resource depending on the healthcare system's implementation.

You must always start with the Procedure resource search using the exact code provided in the task context. If that returns zero results, immediately proceed to the MedicationRequest fallback search using the vaccine name as a text parameter. Do not stop after a single empty Procedure result — the vaccine data may exist only in MedicationRequest.

## When to Use This Skill

- When the task asks you to find a vaccine administration record (e.g., influenza, COVID-19) and provides a specific code (CPT, CVX, or custom code) for the Procedure resource
- When the task context explicitly mentions that the vaccine may also be recorded as a MedicationRequest with specific text (e.g., "COVID-19 VAC")
- When a Procedure search returns zero results but the task expects a vaccine record to exist
- When constructing a MedicationRequest to order a vaccine and you need to verify prior vaccination history first

## Common Failure Patterns

- Searching only Procedure with the given code and concluding no vaccine exists when the record is actually in MedicationRequest
- Using the wrong search parameter on MedicationRequest (e.g., using `code` instead of `text` for vaccine name matching)
- Failing to include a date range filter on the MedicationRequest search, causing excessive results or missing recent records
- Stopping after a single empty Procedure search without attempting the fallback
- Using an incorrect or incomplete vaccine name in the MedicationRequest text search (e.g., "COVID" instead of "COVID-19 VAC")

## Recommended Patterns

**Pattern 1: Primary Procedure Search**
1. Construct a GET request to `/Procedure` with parameters: `patient={patientId}`, `code={vaccineCode}`, and `date=ge{lookbackDate}`
2. Use the exact code provided in the task context (e.g., "COVIDVACCINE", "90686", "150")
3. Set the lookback date to at least 1 year before the current time, or as specified in the task
4. Parse the response bundle — check `total` field and iterate through `entry` array if results exist

CORRECT: `GET /Procedure?patient=S6549951&code=COVIDVACCINE&date=ge2018-11-07`
WRONG:   `GET /Procedure?patient=S6549951&code=COVIDVACCINE` (missing date filter)

**Pattern 2: MedicationRequest Fallback**
1. If Procedure search returns `total: 0`, immediately search MedicationRequest
2. Construct a GET request to `/MedicationRequest` with parameters: `patient={patientId}`, `text={vaccineName}`
3. Use the exact text string specified in the task context (e.g., "COVID-19 VAC")
4. Also include a `date=ge{lookbackDate}` parameter to narrow results
5. If the text search fails (400 error), retry without the text parameter but with the date filter

CORRECT: `GET /MedicationRequest?patient=S6549951&text=COVID-19%20VAC&date=ge2018-11-07`
WRONG:   `GET /MedicationRequest?patient=S6549951` (no text or date filter — returns all medications)

**Pattern 3: Decision and Ordering**
1. If both searches return zero results, conclude no prior vaccine exists
2. If the task requires ordering a vaccine when none found or when last dose was too long ago, construct a POST to `/MedicationRequest`
3. Include `medicationCodeableConcept` with the appropriate coding system (e.g., NDC) and code
4. Set `status: "active"`, `intent: "order"`, and `authoredOn` to the current date
5. Include `subject.reference` pointing to the patient

CORRECT POST body:
```json
{
  "resourceType": "MedicationRequest",
  "medicationCodeableConcept": {
    "coding": [{
      "system": "http://hl7.org/fhir/sid/ndc",
      "code": "91320",
      "display": "COVID-19 vaccine, single-dose"
    }],
    "text": "COVID-19 VAC"
  },
  "authoredOn": "2023-11-07T22:47:00+00:00",
  "status": "active",
  "intent": "order",
  "subject": {
    "reference": "Patient/S6549951"
  }
}
```

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S6549951. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Issue GET to Procedure with the provided code:
   `GET http://localhost:8080/fhir/Procedure?patient=S6549951&code=COVIDVACCINE&date=ge2018-11-07`
   
2. Response shows `"total": 0` — no Procedure records found.

3. Immediately fall back to MedicationRequest search:
   `GET http://localhost:8080/fhir/MedicationRequest?patient=S6549951&date=ge2018-11-07`
   
4. Response shows `"total": 0` — no MedicationRequest records found either.

5. Since no vaccine records exist, it has been more than 12 months since the last dose. Order a booster:
   `POST http://localhost:8080/fhir/MedicationRequest` with body containing COVID-19 vaccine coding.

CORRECT output: `FINISH(["No COVID-19 vaccine records found for patient S6549951 after searching Procedure and MedicationRequest. Since no vaccine was found, it has been more than 12 months since the last dose. Ordered a single-dose COVID booster (CPT 91320) for today."])`
WRONG output:   `FINISH(["No COVID-19 vaccine found in Procedure. No action taken."])`

## Success Indicators

- Agent searches Procedure first with the exact code provided
- When Procedure returns zero results, agent immediately searches MedicationRequest with text parameter
- Agent includes date filters on both searches to limit scope
- Agent correctly parses the response bundles and extracts relevant dates
- When ordering a vaccine, the POST body includes proper coding, status, intent, and subject

## Failure Indicators

- Agent stops after a single empty Procedure result without attempting MedicationRequest fallback
- Agent searches MedicationRequest without a text or date filter, returning too many results
- Agent uses `code` parameter on MedicationRequest instead of `text` for vaccine name matching
- Agent fails to include the vaccine name text in the MedicationRequest search (e.g., searching without `text=COVID-19%20VAC`)
- Agent orders a vaccine without first verifying that no prior record exists
