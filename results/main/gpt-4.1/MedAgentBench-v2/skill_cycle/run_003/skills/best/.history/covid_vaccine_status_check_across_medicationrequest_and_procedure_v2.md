---
description: Check both MedicationRequest and Procedure resources for COVID-19 vaccination
  status before ordering a booster
name: covid_vaccine_status_check_across_medicationrequest_and_procedure
provenance:
  action: MODIFY
  epoch: 3
  fixes: 4
  parent_version: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task3_7
  - task3_14
  - task9_28
  - task3_10
  - task3_12
  - task10_21
  - task8_7
  - task1_10
  - task2_22
  - task3_19
  update_cycle: 1
tags:
- covid-19
- vaccine
- resource-type
- code-filtering
- FHIR
version: 2
---

# COVID-19 Vaccine Status Check with Resource Type and Code Filtering

## Pattern Description

When determining a patient's COVID-19 vaccination status, you must search both MedicationRequest and Procedure resources. However, it is not sufficient to query only by patient; you must also filter by the specific codes or text that identify COVID-19 vaccines. This ensures you do not miss relevant records or include unrelated medications or procedures. Filtering by code (e.g., `code=COVIDVACCINE` for Procedure, `code=91320` or text containing 'COVID-19 VAC' for MedicationRequest) is essential for accurate status determination and appropriate booster ordering.

## When to Use This Skill

- When reviewing COVID-19 vaccination status for a patient to determine if a booster is needed.
- When the task instructs you to "find the most recent COVID-19 vaccine" or "check for prior COVID-19 vaccination".
- When searching MedicationRequest or Procedure resources for evidence of COVID-19 vaccination.

## Common Failure Patterns

- Querying MedicationRequest with only `?patient=...` and omitting a code or text filter for COVID-19 vaccines, resulting in irrelevant results.
- Querying Procedure with only `?patient=...` or with an incorrect or missing `code` parameter.
- Failing to use the correct COVID-19 vaccine codes (e.g., CPT 91320) or text filters (e.g., 'COVID-19 VAC').
- Interpreting the absence of any MedicationRequest or Procedure as absence of COVID-19 vaccination, when the search was not properly filtered.

## Recommended Patterns

**Pattern 1: Filtered Search for COVID-19 Vaccines**
- For Procedure: Use `GET /Procedure?code=COVIDVACCINE&patient={id}` or include all known COVID-19 vaccine codes if available.
- For MedicationRequest: Use `GET /MedicationRequest?patient={id}&code=91320` if the code is known, or use a text search if only the display name is available (e.g., filter for text containing 'COVID-19 VAC').
- If the FHIR server does not support code filtering on MedicationRequest, retrieve all for the patient and filter client-side by `medicationCodeableConcept.coding.code` or `medicationCodeableConcept.text` containing COVID-19 vaccine identifiers.

CORRECT:
- `GET /MedicationRequest?patient=S123&code=91320`
- `GET /Procedure?code=COVIDVACCINE&patient=S123`

WRONG:
- `GET /MedicationRequest?patient=S123` (no code or text filter)
- `GET /Procedure?patient=S123` (no code filter)

**Pattern 2: Fallback for Uncertain Code Support**
- If you are unsure which codes are supported, check the task context for provided codes (e.g., CPT 91320) or text patterns (e.g., 'COVID-19 VAC').
- If multiple codes are possible, use a comma-separated list in the `code` parameter if supported (e.g., `code=91320,91321`).

**Pattern 3: Verification Before Decision**
- Before concluding that no COVID-19 vaccine is present, confirm that your search included the correct code or text filter.
- Only order a booster if no filtered records are found or if the most recent dose is older than the specified threshold (e.g., 12 months).

## Example Application

**Task:** "Review COVID-19 vaccination status for patient S6488980. Find the most recent COVID-19 vaccine and if the last dose was more than 12 months ago, order a COVID booster."

**Step-by-step:**

1. Issue `GET /MedicationRequest?patient=S6488980&code=91320` (or use text filter for 'COVID-19 VAC' if code is not available).
2. Issue `GET /Procedure?code=COVIDVACCINE&patient=S6488980`.
3. If both responses have empty `entry` arrays, conclude no prior COVID-19 vaccine.
4. If any record is found, extract the date and compare to current date.
5. If last dose >12 months ago, order booster; otherwise, do not order.

CORRECT output: `FINISH(["Checked both MedicationRequest and Procedure records for COVID-19 vaccination status for patient S6488980. No COVID-19 vaccine found. COVID-19 booster (CPT 91320) ordered for today (2023-11-07)."])
`
WRONG output: `FINISH(["Checked both MedicationRequest and Procedure records for patient S6488980. No evidence of any prior COVID-19 vaccine found. COVID-19 booster (CPT 91320, single dose) should be ordered today."])` (if the MedicationRequest search was not filtered by code/text)

## Success Indicators

- MedicationRequest and Procedure queries include a code or text filter specific to COVID-19 vaccines.
- The agent does not conclude "no vaccine found" unless both filtered queries return no results.
- Booster is only ordered if no filtered record is found or the last dose is too old.

## Failure Indicators

- MedicationRequest or Procedure queries omit the code or text filter for COVID-19 vaccines.
- The agent concludes no vaccine is present based on an unfiltered MedicationRequest or Procedure search.
- Booster is ordered when prior COVID-19 vaccine records exist but were missed due to improper filtering.
