---
description: Query Immunization resource (not Procedure) for vaccine history and use
  correct resource for vaccine ordering, but only for tasks involving immunizations
  (vaccines), not for non-vaccine procedures such as urinary catheter placement/removal.
name: immunization_resource_selection_for_vaccine_tasks
provenance:
  action: ADD
  epoch: 3
  fixes: 3
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task1_16
  - task6_26
  - task8_5
  - task10_24
  - task9_5
  - task3_30
  - task8_7
  - task2_14
  - task3_27
  update_cycle: 0
tags: []
version: 1
---

# Immunization Resource Selection for Vaccine Tasks

## Pattern Description

When determining a patient's vaccination history or ordering a new vaccine, you must use the correct FHIR resource types. Immunizations (such as influenza or COVID-19 vaccines) are recorded in the `Immunization` resource, not in `Procedure`. Similarly, vaccine orders should be placed using `MedicationRequest` (for medication-based vaccines) or `ServiceRequest` (if the workflow requires a service order), but never as a `Procedure` resource. Using the wrong resource type leads to missed vaccine history and incorrect order placement.

**Guard Clause:**
- This skill applies ONLY to tasks involving immunizations (vaccines), such as influenza, COVID-19, pneumococcal, hepatitis, tetanus, etc.
- If the task involves non-vaccine procedures (e.g., urinary catheter placement/removal, surgical procedures, device insertions), continue to use the `Procedure` resource as appropriate.

## When to Use This Skill

- When asked to determine the date of a patient's last vaccine (e.g., influenza, COVID-19, pneumococcal, etc.).
- When the task requires checking if a vaccine was administered within a certain time window.
- When the task requires ordering a new vaccine if the last dose is too old or missing.
- When the instruction provides a CPT or CVX code for a vaccine.

## Common Failure Patterns

- Querying `Procedure?code=...&patient=...` for vaccine history instead of `Immunization?code=...&patient=...` (for immunization tasks).
- Failing to find prior immunizations because the wrong resource type is searched.
- Placing a vaccine order as a `Procedure` or `ServiceRequest` when a `MedicationRequest` or `Immunization` is required.
- Using only `MedicationRequest` to check for prior vaccines, missing those recorded as `Immunization`.
- Using only `Procedure` to check for prior vaccines, missing those recorded as `Immunization`.

## Recommended Patterns

**Pattern 1: Querying Vaccine History**
1. When asked for a patient's vaccine history, always issue a GET on the `Immunization` resource:
   - GET `/Immunization?code={vaccine_code}&patient={patient_id}`
   - Use the CPT or CVX code as provided in the task.
2. If the vaccine may have been ordered but not yet administered, you may also check `MedicationRequest` for active or completed vaccine orders.
3. Do not use `Procedure` to search for immunization history unless the system is known to record vaccines as procedures (rare).

**Pattern 2: Placing Vaccine Orders**
1. Place new vaccine orders using `MedicationRequest` (preferred for medication-based vaccines) or `ServiceRequest` (if the workflow requires a service order), not as a `Procedure`.
2. Populate the `medicationCodeableConcept` (for `MedicationRequest`) or `code` (for `ServiceRequest`) with the correct coding (CPT or CVX) and display text.
3. Include `authoredOn`, `status`, `intent`, `subject`, and any relevant `dosageInstruction` or `note` fields as required.

**Pattern 3: Fallback and Verification**
1. If no `Immunization` records are found, check for relevant `MedicationRequest` resources as a fallback (e.g., for vaccines administered as medications).
2. If both are empty, conclude that no prior vaccine is documented.

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S6474456. If it was administered more than 365 days ago, order a new influenza vaccine for today."

**Step-by-step:**

1. Issue GET:
   - `GET /Immunization?code=90686&patient=S6474456`
2. If no results, optionally check:
   - `GET /MedicationRequest?code=90686&patient=S6474456`
3. Extract the most recent `occurrenceDateTime` from the `Immunization` resource.
4. If the last dose is >365 days ago or not found, POST a new order:
   - `POST /MedicationRequest` with `medicationCodeableConcept.coding.code = 90686`, correct display, and today's date.

CORRECT output:
- GET `/Immunization?code=90686&patient=S6474456`
- If no result, POST `/MedicationRequest` for influenza vaccine

WRONG output:
- GET `/Procedure?code=90686&patient=S6474456` (misses immunization records)
- POST `/Procedure` or `/ServiceRequest` for vaccine order (incorrect resource)

## Success Indicators

- The agent queries `Immunization` for vaccine history, not `Procedure`, for immunization tasks.
- The agent finds and reports the correct last vaccine date (if present in Immunization).
- New vaccine orders are placed as `MedicationRequest` or `ServiceRequest`, not as `Procedure`.
- The agent does not miss prior vaccines due to searching the wrong resource type.

## Failure Indicators

- The agent issues GET requests to `Procedure` for vaccine history and fails to find existing immunizations (for immunization tasks).
- The agent places vaccine orders as `Procedure` resources.
- The agent reports "no prior vaccine found" when an `Immunization` record exists.
- The agent omits vaccine ordering or history reporting due to resource type mismatch.

## Guard Clause Examples

- **Do NOT apply this skill to tasks involving non-vaccine procedures (e.g., urinary catheter placement/removal, surgical procedures, device insertions). For those, continue to use the `Procedure` resource as appropriate.**
