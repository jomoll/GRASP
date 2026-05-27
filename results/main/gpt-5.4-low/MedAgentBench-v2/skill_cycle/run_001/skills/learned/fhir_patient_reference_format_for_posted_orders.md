---
description: Use canonical Patient/<id> subject references in order-creating POST
  bodies.
name: fhir_patient_reference_format_for_posted_orders
provenance:
  action: ADD
  epoch: 2
  fixes: 7
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task3_29
  - task2_1
  - task9_9
  - task3_3
  - task3_7
  - task2_14
  - task3_27
  - task1_20
  - task2_30
  - task1_13
  update_cycle: 1
tags:
- fhir
- orders
- servicerequest
- medicationrequest
- patient-reference
version: 1
---

# FHIR Patient Reference Format for Posted Orders

## Pattern Description

When you create an order resource that points to a patient, you must build the patient link as a FHIR reference, not as a bare identifier. For order resources such as `ServiceRequest` and `MedicationRequest`, this usually means `"subject": {"reference": "Patient/<id>"}`.

This skill changes how you construct POST bodies. Even if searches use `?patient=S1234567`, the posted resource should usually not use `"subject": {"reference": "S1234567"}`. A malformed subject reference can make an accepted POST fail downstream validation or retrieval.

## When to Use This Skill

- When creating a `ServiceRequest` or `MedicationRequest` with a `subject` field
- When the task gives a patient identifier like `S1891852` and you need to build a POST body
- When prior reads show patient references formatted as `Patient/<id>` in returned resources
- When a POST is accepted but there is a warning that the created order may not have been stored or retrieved correctly

## Common Failure Patterns

- Using `"subject": {"reference": "S1891852"}` instead of `"subject": {"reference": "Patient/S1891852"}`
- Copying the search parameter value from `?patient=S1891852` directly into `subject.reference`
- Using `subject.identifier` when the task expects a direct FHIR reference
- Formatting one resource type correctly (for example `MedicationRequest`) but forgetting the same rule for `ServiceRequest`
- Building a valid-looking POST body except for the `subject.reference` field, causing silent storage/retrieval issues

## Recommended Patterns

**Pattern 1: core strategy or rule**
Before any order POST, inspect the target resource's patient field and populate it as a FHIR reference.

For `ServiceRequest`:
- Use `subject.reference`
- Format it as `Patient/<patient_id>`

For `MedicationRequest`:
- Use `subject.reference`
- Format it as `Patient/<patient_id>`

CORRECT: `"subject": {"reference": "Patient/S1891852"}`
WRONG:   `"subject": {"reference": "S1891852"}`

**Pattern 2: fallback or verification rule**
If you are unsure of the correct format, check previously returned resources for the same patient. If `Procedure.subject.reference`, `Observation.subject.reference`, or existing orders use `Patient/<id>`, mirror that exact pattern in your POST.

If the task only provides a bare identifier and no prior resources, default to `Patient/<identifier>` rather than the bare identifier alone.

**Pattern 3: formatting or completion rule**
When constructing the final POST body, keep `subject` as an object with a `reference` string.

CORRECT:
```json
"subject": {"reference": "Patient/S1891852"}
```

WRONG:
```json
"subject": {"reference": "S1891852"}
```

WRONG:
```json
"subject": "Patient/S1891852"
```

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S1891852. If it was administered more than 365 days ago, order a new influenza vaccine for today."

## Step-by-step:

1. Issue the history query:
   `GET /Procedure?patient=S1891852&code=90686&date=lt2024-01-10`
2. See that no prior qualifying vaccine was returned.
3. Construct the `ServiceRequest` using the patient as a FHIR reference:
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "subject": {"reference": "Patient/S1891852"},
     "code": {
       "coding": [
         {
           "system": "http://www.ama-assn.org/go/cpt",
           "code": "90686",
           "display": "influenza vaccine (quadrivalent, preservative-free, IM)"
         }
       ]
     },
     "authoredOn": "2024-01-09T00:00:00+00:00",
     "occurrenceDateTime": "2024-01-09T00:00:00+00:00"
   }
   ```
4. After successful POST, finish with the decision summary.

CORRECT output: `FINISH(["No documented influenza vaccine was found within the past 365 days.", "Ordered influenza vaccine for today."])`
WRONG output:   `FINISH(["Order placed."])` after posting a body with `"subject":{"reference":"S1891852"}`

## Success Indicators

- Your POST body contains `subject.reference` with the exact form `Patient/<id>`
- Returned resources in the chart and your newly created order use the same patient reference pattern
- Order-creation tasks no longer fail because of malformed patient linkage

## Failure Indicators

- The POST body contains a bare identifier in `subject.reference`
- You copy `patient=S1234567` directly into `subject.reference` without the `Patient/` prefix
- The server accepts the POST but later retrieval/verification indicates the order may not have been stored correctly
- Similar tasks succeed for `MedicationRequest` but fail for `ServiceRequest` because only one resource type uses the correct patient reference format
