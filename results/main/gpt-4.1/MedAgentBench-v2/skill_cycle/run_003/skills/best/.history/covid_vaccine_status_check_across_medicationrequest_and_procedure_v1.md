---
description: Check both MedicationRequest and Procedure resources for COVID-19 vaccination
  status before ordering a booster
name: covid_vaccine_status_check_across_medicationrequest_and_procedure
provenance:
  action: ADD
  epoch: 2
  fixes: 3
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task8_19
  - task10_27
  - task8_7
  - task10_13
  - task4_27
  - task3_17
  - task10_21
  - task2_22
  - task10_16
  - task10_10
  update_cycle: 1
tags:
- covid-19
- vaccine
- FHIR
- MedicationRequest
- Procedure
- immunization
- order logic
version: 1
---

# COVID-19 Vaccination Status Check Across MedicationRequest and Procedure

## Pattern Description

When determining a patient's COVID-19 vaccination status, you must search both MedicationRequest and Procedure resources. COVID-19 vaccines may be documented as medication orders (MedicationRequest with text or code indicating COVID-19 vaccine) or as completed procedures (Procedure with code 'COVIDVACCINE' or similar). Relying on only one resource type can result in missing valid vaccination records, leading to inappropriate booster orders or missed opportunities for care.

This pattern ensures that the agent comprehensively reviews all relevant FHIR resources to accurately determine vaccination status and make correct ordering decisions.

## When to Use This Skill

- When asked to review or determine a patient's COVID-19 vaccination status.
- When deciding whether to order a COVID-19 booster based on the timing of the last COVID-19 vaccine.
- When the task or context mentions COVID-19 vaccine, booster, or immunization, and provides codes or text for both MedicationRequest and Procedure.

## Common Failure Patterns

- Only querying MedicationRequest and ignoring Procedure resources, missing vaccines documented as procedures.
- Only querying Procedure and ignoring MedicationRequest, missing vaccines documented as medication orders.
- Failing to check both resource types before concluding that no prior COVID-19 vaccine exists.
- Ordering a booster without confirming absence of both MedicationRequest and Procedure evidence.

## Recommended Patterns

**Pattern 1: Comprehensive Search**
1. Issue a GET request for MedicationRequest resources for the patient. Filter by text or code indicating COVID-19 vaccine (e.g., text contains 'COVID-19 VAC', code '91320', etc.).
2. Issue a GET request for Procedure resources for the patient. Filter by code 'COVIDVACCINE' or other relevant codes provided in the task context.
3. Combine results from both resource types. Identify the most recent COVID-19 vaccine administration date from either source.

CORRECT: Search both MedicationRequest and Procedure, then determine the most recent vaccine date.
WRONG: Only search MedicationRequest and ignore Procedure.

**Pattern 2: Decision Logic**
- If neither MedicationRequest nor Procedure shows a prior COVID-19 vaccine, treat the patient as unvaccinated and order a booster if appropriate.
- If a prior vaccine is found, check the date. If more than 12 months have passed, order a booster; otherwise, no order is needed.

**Pattern 3: Output Formatting**
- Clearly state in the output which resources were checked and the basis for the decision.
- If ordering a booster, include the correct CPT code (e.g., 91320) and today's date.

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S1234567. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. GET /MedicationRequest?patient=S1234567 (filter for COVID-19 vaccine orders)
2. GET /Procedure?patient=S1234567&code=COVIDVACCINE
3. Extract all COVID-19 vaccine dates from both responses.
4. Find the most recent date. If >12 months ago, POST a new MedicationRequest for COVID-19 booster (CPT 91320) with today's date.
5. FINISH with a summary: "Checked both MedicationRequest and Procedure records. No COVID-19 vaccine found. COVID-19 booster (CPT 91320) ordered for today."

CORRECT output: "Checked both MedicationRequest and Procedure records. No COVID-19 vaccine found. COVID-19 booster (CPT 91320) ordered for today."
WRONG output: "No COVID-19 vaccine or booster found for patient S1234567 in MedicationRequest records. Ordering a COVID-19 booster (CPT 91320) today." (if Procedure was not checked)

## Success Indicators

- Agent issues GET requests for both MedicationRequest and Procedure resources when checking COVID-19 vaccination status.
- Agent combines results from both resource types before making a decision.
- Output or order decision is based on the most recent vaccine date from either resource.

## Failure Indicators

- Agent only queries MedicationRequest or only Procedure, not both.
- Agent concludes no vaccine is present without checking both resource types.
- Agent orders a booster inappropriately due to incomplete search.
