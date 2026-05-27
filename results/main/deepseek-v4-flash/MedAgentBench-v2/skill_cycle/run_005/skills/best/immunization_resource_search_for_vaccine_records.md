---
description: Search Immunization resource when checking vaccine history
name: immunization_resource_search_for_vaccine_records
provenance:
  action: ADD
  epoch: 1
  fixes: 1
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - task3_14
  - task10_20
  - task10_13
  - task10_16
  - task3_12
  - task8_7
  - task10_15
  - task8_19
  - task9_3
  - task9_5
  update_cycle: 0
tags: []
version: 1
---

# Immunization Resource Search for Vaccine Records

## Pattern Description

When a task requires finding vaccine administration records (e.g., COVID-19, influenza), you must search the `Immunization` FHIR resource in addition to `MedicationRequest` and `Procedure`. The `Immunization` resource is the standard FHIR resource for recording vaccine administrations, and many healthcare systems store vaccination data exclusively there. Relying only on `MedicationRequest` or `Procedure` will miss vaccine records and lead to incorrect conclusions.

This skill teaches you to always include the `Immunization` endpoint in your search strategy when the task involves vaccination history. You must query all three resources (`Immunization`, `MedicationRequest`, `Procedure`) to ensure complete coverage before concluding that no vaccine records exist.

## When to Use This Skill

- When the task asks to "find the most recent COVID-19 vaccine" or "check COVID-19 vaccination status"
- When the task asks to "determine the date of the last influenza vaccine" or any other vaccine
- When the task mentions "vaccine", "vaccination", "immunization", or "booster"
- When you have searched `MedicationRequest` and `Procedure` and found no results, but the task expects vaccine data
- When the task context provides vaccine-specific codes (e.g., 'COVIDVACCINE' for Procedure) but you haven't checked Immunization

## Common Failure Patterns

- Searching only `MedicationRequest?category=community` or `MedicationRequest?date=ge...` and concluding no vaccine exists
- Searching only `Procedure?code=COVIDVACCINE` and concluding no vaccine exists
- Missing the `Immunization` resource entirely, even though it is the primary FHIR resource for vaccine records
- Concluding "no prior vaccination" and ordering a booster when vaccine records actually exist in Immunization
- Using only a date filter without also searching without date restrictions (older vaccines may exist)

## Recommended Patterns

**Pattern 1: Always search Immunization first or in parallel**
When the task involves vaccine history, you must query the `Immunization` endpoint. Use the patient identifier and, if known, the vaccine code or text filter.

CORRECT: `GET /fhir/Immunization?patient=S6551923` (no date filter initially to catch all records)
WRONG:   Only `GET /fhir/MedicationRequest?patient=S6551923&category=community`

**Pattern 2: Search without date restrictions first, then narrow**
Start with a broad search (no date filter) to find all vaccine records. If you need the most recent, sort by date descending. If you need records within a timeframe, apply date filters only after confirming records exist.

CORRECT: `GET /fhir/Immunization?patient=S6551923` then sort by `occurrenceDateTime`
WRONG:   `GET /fhir/Immunization?patient=S6551923&date=ge2022-11-07` (may miss older vaccines)

**Pattern 3: Combine all three resource types**
Search `Immunization`, `MedicationRequest`, and `Procedure` for vaccine records. Only conclude "no vaccine records found" after all three return empty results.

CORRECT: Search sequence: Immunization → MedicationRequest → Procedure (or parallel)
WRONG:   Searching only one or two of these resources

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S6551923. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Search Immunization first: `GET http://localhost:8080/fhir/Immunization?patient=S6551923`
   - Check the response bundle for entries. If entries exist, examine `occurrenceDateTime` to find the most recent.
   - If no entries, proceed to step 2.

2. Search MedicationRequest: `GET http://localhost:8080/fhir/MedicationRequest?patient=S6551923`
   - Look for entries where `medicationCodeableConcept.text` contains "COVID-19 VAC" or similar.
   - If no entries, proceed to step 3.

3. Search Procedure: `GET http://localhost:8080/fhir/Procedure?patient=S6551923&code=COVIDVACCINE`
   - Check for entries with the specified code.

4. If all three searches return empty, then conclude no vaccine records exist. Calculate the date 12 months ago from current time (2023-11-07 → 2022-11-07). Since no records exist, the last dose is considered more than 12 months ago. Order a COVID booster.

CORRECT output: `FINISH(["No COVID-19 vaccine records found for patient S6551923. Since no prior vaccination is documented, the last dose is considered more than 12 months ago. Ordering a single-dose COVID booster (CPT 91320) today."])`

WRONG output: `FINISH(["No COVID-19 vaccine records found..."])` without having searched Immunization

## Success Indicators

- The agent queries `Immunization` endpoint for vaccine-related tasks
- The agent searches all three resources (Immunization, MedicationRequest, Procedure) before concluding no vaccine records exist
- The agent correctly identifies the most recent vaccine from Immunization records when they exist
- The agent uses broad searches (no date filter) initially to capture all records

## Failure Indicators

- The agent only searches `MedicationRequest` and/or `Procedure` for vaccine records
- The agent concludes "no vaccine records found" without ever querying `Immunization`
- The agent applies date filters too early, missing older vaccine records
- The agent orders a booster when vaccine records actually exist in Immunization
