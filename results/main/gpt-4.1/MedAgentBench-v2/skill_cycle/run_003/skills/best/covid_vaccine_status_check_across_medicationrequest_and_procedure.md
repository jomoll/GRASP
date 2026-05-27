---
description: Check both MedicationRequest and Procedure resources for COVID-19 vaccination
  status before ordering a booster
name: covid_vaccine_status_check_across_medicationrequest_and_procedure
provenance:
  action: MODIFY
  epoch: 4
  fixes: 7
  parent_version: 2
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task10_10
  - task3_12
  - task8_7
  - task2_1
  - task8_9
  - task3_7
  - task8_21
  - task2_14
  - task3_10
  - task1_13
  update_cycle: 0
tags:
- covid
- vaccine
- resource-type
- code-filter
- FHIR
version: 3
---

# COVID Vaccine Resource Type and Code Filtering

## Pattern Description

When determining COVID-19 vaccination status, you must not only check both MedicationRequest and Procedure resources, but also ensure that your FHIR queries are restricted to only those entries that are specific to COVID-19 vaccines. This means using resource type filters and code filters (e.g., CPT 91320 for COVID-19 vaccine) in your queries, rather than searching all MedicationRequests or Procedures for a patient. This prevents false positives from unrelated vaccines or procedures and ensures accurate assessment of COVID-19 vaccination history.

## When to Use This Skill

- When reviewing a patient's COVID-19 vaccination status to determine if a booster is needed
- When the task specifies to "find the most recent COVID-19 vaccine" or similar
- When searching MedicationRequest or Procedure resources for evidence of COVID-19 vaccination

## Common Failure Patterns

- Omitting the `code` parameter in MedicationRequest or Procedure queries, resulting in retrieval of unrelated vaccines or procedures
- Searching all MedicationRequests or Procedures for a patient without filtering for COVID-19 vaccine codes (e.g., 91320, or text containing 'COVID-19 VAC')
- Using only text search in MedicationRequest and missing code-based matches
- Failing to check both resource types (MedicationRequest and Procedure)

## Recommended Patterns

**Pattern 1: Query with Resource Type and Code Filter**
- For MedicationRequest: Use `GET /MedicationRequest?patient={id}&code=91320` (or other COVID-19 vaccine codes as specified)
- For Procedure: Use `GET /Procedure?patient={id}&code=COVIDVACCINE` (or other relevant codes)
- If the task context mentions text-based vaccine names, also check MedicationRequest with a text filter if supported, but always include code-based queries

CORRECT:
- `GET /MedicationRequest?patient=S2450227&code=91320`
- `GET /Procedure?patient=S2450227&code=COVIDVACCINE`

WRONG:
- `GET /MedicationRequest?patient=S2450227` (no code filter)
- `GET /Procedure?patient=S2450227` (no code filter)

**Pattern 2: Fallback for Text-based Vaccine Names**
- If no results are found with code-based queries, and the task context mentions text-based vaccine names (e.g., 'COVID-19 VAC'), you may issue a secondary query filtering on `medicationCodeableConcept.text` if supported, but do not rely solely on this.

**Pattern 3: Output Construction**
- In your summary or decision, explicitly state which resource types and codes were checked (e.g., "Checked both MedicationRequest (code 91320) and Procedure (code COVIDVACCINE)")

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S2450227. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Issue `GET /MedicationRequest?patient=S2450227&code=91320`
2. If no results, optionally check for text matches: `GET /MedicationRequest?patient=S2450227` and filter entries where `medicationCodeableConcept.text` contains 'COVID-19 VAC'
3. Issue `GET /Procedure?patient=S2450227&code=COVIDVACCINE`
4. Extract the most recent date from the returned entries
5. If the most recent date is >12 months ago, POST a new MedicationRequest for COVID-19 booster (CPT 91320)
6. FINISH with a summary that specifies which resource types and codes were checked

CORRECT output: `FINISH(["Checked both MedicationRequest (code 91320) and Procedure (code COVIDVACCINE) for COVID-19 vaccination status for patient S2450227. The most recent COVID-19 vaccine was on 2022-08-12. As this is more than 12 months before today (2023-11-07), a COVID-19 booster (CPT 91320, single dose) should be ordered today."])`

WRONG output: `FINISH(["Checked both MedicationRequest and Procedure records for COVID-19 vaccination status for patient S2450227. No COVID-19 vaccine found. COVID-19 booster (CPT 91320) will be ordered for today (2023-11-07)."])

## Success Indicators

- All FHIR queries for COVID-19 vaccine status include a `code` parameter specific to COVID-19 vaccines
- Both MedicationRequest and Procedure resources are checked with code filters
- Output summary specifies which codes and resource types were checked
- No unrelated vaccines or procedures are considered in the decision

## Failure Indicators

- MedicationRequest or Procedure queries omit the `code` parameter, returning unrelated results
- Agent checks all MedicationRequests or Procedures for a patient without filtering for COVID-19 vaccine codes
- Output summary is vague (e.g., "Checked both MedicationRequest and Procedure records") and does not specify codes
- COVID-19 booster is ordered based on incomplete or incorrect vaccine history due to lack of code filtering
