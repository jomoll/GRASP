---
description: Search Procedure resource for influenza vaccine records using CPT code
  90686
name: influenza_vaccine_procedure_search
provenance:
  action: ADD
  epoch: 0
  fixes: 0
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_28
  - task2_9
  - task1_7
  - task8_29
  - task3_10
  - task1_16
  - task9_3
  - task8_21
  - task4_23
  - task9_27
  update_cycle: 1
tags: []
version: 1
---

# Influenza Vaccine Procedure Search

## Pattern Description

Influenza vaccine administrations are stored in the FHIR `Procedure` resource, not in `MedicationRequest`. When a task asks you to find the date of the last influenza vaccine, you must query the `Procedure` endpoint with the CPT code `90686` and the patient identifier. Do not search `MedicationRequest` for vaccine records — that resource contains medication orders, not administered vaccinations.

When you receive a response bundle, you must inspect the `entry` array for `Procedure` resources that have a `code.coding` entry matching CPT `90686`. Extract the `performedDateTime` or `performedPeriod.end` field to get the administration date. If the bundle has `total: 0` or an empty `entry` array, that means no influenza vaccine record exists for that patient — you must then conclude the vaccine is overdue and order a new one.

## When to Use This Skill

- When the task asks to "find the last influenza vaccine" or "determine the date of the last flu shot"
- When the task provides a CPT code like `90686` for influenza vaccine
- When the task mentions "influenza vaccine" or "flu vaccine" and asks about timing or ordering
- When you are about to search for vaccine records — always check if the resource type should be `Procedure` rather than `MedicationRequest`

## Common Failure Patterns

- Querying `MedicationRequest` instead of `Procedure` — this returns zero results because vaccines are not stored as medication orders
- Using the wrong CPT code — the influenza vaccine code is `90686`, not a different code
- Not filtering by code parameter — searching all procedures for a patient returns many irrelevant records
- Using `date=ge` with a date range that is too narrow — use a wide range (e.g., 5 years back) to ensure you capture the last vaccine
- Failing to extract `performedDateTime` from the Procedure resource — the date is in this field, not in `authoredOn` or `effectiveDateTime`

## Recommended Patterns

**Pattern 1: Primary search for influenza vaccine**

1. Construct a GET request to `Procedure` endpoint with parameters:
   - `patient={patientId}`
   - `code=90686` (the CPT code for influenza vaccine)
   - `date=ge{5_years_ago}` (use a broad date range, e.g., 5 years before the current date)
   - Example: `GET /fhir/Procedure?patient=S1478444&date=ge2019-01-09&code=90686`

2. Parse the response bundle:
   - Check `total` field — if `total: 0`, no vaccine records exist
   - If `total > 0`, iterate through `entry` array and find all `Procedure` resources with `code.coding` containing `90686`
   - Extract `performedDateTime` from each matching Procedure
   - Sort by date descending to find the most recent

CORRECT: `performedDateTime` from Procedure resource
WRONG:   `authoredOn` from MedicationRequest

**Pattern 2: Date comparison and decision**

1. Get the current date from the task context (e.g., "It's 2024-01-09T00:00:00+00:00 now")
2. Calculate the difference between current date and the last vaccine date
3. If difference > 365 days OR no vaccine found, order a new influenza vaccine
4. If difference <= 365 days, no action needed

**Pattern 3: Ordering the vaccine**

When ordering, use the medication name and details provided in the task context. Create a `MedicationRequest` with:
- `medicationCodeableConcept` with the vaccine name
- `status`: "active"
- `intent`: "order"
- `authoredOn`: current date
- `subject`: reference to the patient

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S1478444. If it was administered more than 365 days ago, order a new influenza vaccine for today. It's 2024-01-09T00:00:00+00:00 now. The CPT code for influenza vaccine is 90686. The vaccine to order is influenza vaccine (quadrivalent, preservative-free, IM)."

**Step-by-step:**

1. Issue GET to Procedure endpoint:
   `GET http://localhost:8080/fhir/Procedure?patient=S1478444&date=ge2019-01-09&code=90686`

2. Parse response bundle. If `total: 0`, no vaccine found.

3. Since no vaccine found, it has been more than 365 days since last dose. Order new vaccine.

4. Construct POST body for MedicationRequest:
   ```json
   {
     "resourceType": "MedicationRequest",
     "medicationCodeableConcept": {
       "coding": [{
         "system": "http://hl7.org/fhir/sid/ndc",
         "code": "90686",
         "display": "Influenza vaccine (quadrivalent, preservative-free, IM)"
       }],
       "text": "Influenza vaccine (quadrivalent, preservative-free, IM)"
     },
     "authoredOn": "2024-01-09T00:00:00+00:00",
     "status": "active",
     "intent": "order",
     "subject": {
       "reference": "Patient/S1478444"
     }
   }
   ```

CORRECT output: `FINISH(["No influenza vaccine found for patient S1478444. Since no vaccine was found, it has been more than 365 days since the last dose. Ordering a new influenza vaccine for today."])`
WRONG output:   `FINISH(["No influenza vaccine found for patient S1478444."])` (missing the ordering action)

## Success Indicators

- Agent queries `Procedure` endpoint with `code=90686` parameter
- Agent correctly extracts `performedDateTime` from Procedure resources
- Agent compares dates correctly against the 365-day threshold
- Agent creates a MedicationRequest when vaccine is overdue or not found
- Agent does not query `MedicationRequest` for vaccine records

## Failure Indicators

- Agent queries `MedicationRequest` instead of `Procedure` for vaccine records
- Agent uses wrong CPT code or no code filter
- Agent fails to extract the date from `performedDateTime`
- Agent incorrectly calculates date difference (e.g., using wrong reference date)
- Agent does not order the vaccine when no record is found
