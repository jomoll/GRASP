---
description: Ensure Immunization resource is queried when determining vaccination
  status, not MedicationRequest.
name: immunization_resource_selection_for_vaccine_status_queries
provenance:
  action: ADD
  epoch: 1
  fixes: 8
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task10_10
  - task8_19
  - task1_13
  - task2_15
  - task8_5
  - task2_22
  - task3_3
  - task3_19
  - task8_26
  - task6_26
  update_cycle: 0
tags:
- FHIR
- Immunization
- vaccine
- resource selection
- clinical decision
version: 1
---

# Immunization Resource Selection for Vaccine Status Queries

## Pattern Description

When determining a patient's vaccination status, you must query the FHIR Immunization resource, not MedicationRequest, unless the task or system context explicitly states that immunizations are only recorded as MedicationRequests. Immunization is the canonical FHIR resource for documenting administered vaccines, including COVID-19 and influenza. MedicationRequest typically represents orders or prescriptions, not completed vaccinations. Relying solely on MedicationRequest can result in missing valid immunization records and lead to incorrect clinical decisions.

This pattern is critical for tasks that require finding the most recent vaccine administration date, checking for overdue boosters, or confirming vaccine series completion. Using the wrong resource type can cause the agent to miss existing immunizations and inappropriately recommend or order additional doses.

## When to Use This Skill

- When asked to determine if a patient has received a specific vaccine (e.g., COVID-19, influenza, hepatitis B).
- When the task requires finding the date of the most recent vaccine administration.
- When deciding whether a booster or repeat vaccination is needed based on time since last dose.
- When the instruction references "vaccination status" or "immunization record".

## Common Failure Patterns

- Querying only `MedicationRequest` for vaccine status, missing actual administered doses in `Immunization`.
- Returning "no vaccine found" when Immunization records exist.
- Using `Procedure` or `MedicationAdministration` inappropriately for vaccine status when Immunization is available.
- Failing to check Immunization when the task context or FHIR server supports it.

## Recommended Patterns

Pattern 1: Core Query Strategy
1. When asked about vaccine administration status, issue a GET request to `/Immunization?patient=Patient/{id}&vaccine-code={code}` (or use text search if code is not available).
2. If the vaccine code is not known, use a text search on Immunization (e.g., `?patient=Patient/{id}&_text=COVID-19`).
3. Sort results by `occurrenceDateTime` descending to find the most recent dose.

CORRECT: GET `/Immunization?patient=Patient/S2450227&_text=COVID-19`
WRONG:   GET `/MedicationRequest?patient=Patient/S2450227` (for vaccine status)

Pattern 2: Fallback or Verification Rule
- If Immunization returns no results and the task context suggests vaccines may be recorded as Procedure or MedicationRequest, then query those resources as a fallback, but always check Immunization first.

Pattern 3: Output Construction
- When reporting vaccine status, use the date from the most recent Immunization entry's `occurrenceDateTime`.
- If no Immunization is found, state "No record of prior [vaccine] found" only after checking Immunization.

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S2450227. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Issue GET `/Immunization?patient=Patient/S2450227&_text=COVID-19`.
2. If Immunization entries are found, extract the most recent `occurrenceDateTime`.
3. If no Immunization entries are found, optionally check `/Procedure` or `/MedicationRequest` as a fallback if the system context allows.
4. Decide on booster need based on the date.
5. Construct output: "Most recent COVID-19 vaccine was on [date]. Booster [needed/not needed]."

CORRECT output: "No record of prior COVID-19 vaccination found for patient S2450227. COVID booster (CPT 91320) should be ordered."
WRONG output:   "No COVID-19 vaccine found in MedicationRequest for patient S2450227. COVID booster (CPT 91320) should be ordered." (if Immunization was not checked)

## Success Indicators

- The agent issues a GET request to the Immunization resource when asked about vaccine status.
- The agent reports vaccine status based on Immunization entries, not just MedicationRequest.
- The agent only reports "no vaccine found" after checking Immunization.

## Failure Indicators

- The agent queries only MedicationRequest or Procedure for vaccine status and misses Immunization.
- The agent incorrectly reports no vaccine found when Immunization entries exist.
- The agent orders unnecessary boosters due to missing Immunization data.
