---
description: Enforce the 'ResourceType/ID' format for all subject references in POST/PUT
  requests.
name: fhir_subject_reference_validation
provenance:
  action: ADD
  epoch: 7
  fixes: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task10_24
  - task4_28
  - task9_14
  - task3_30
  - task5_19
  - task9_5
  - task10_27
  - task9_1
  - task10_20
  update_cycle: 0
tags:
- fhir
- validation
- post-request
version: 1
---

# FHIR Subject Reference Validation

## Pattern Description
When creating or updating FHIR resources that require a `subject` field (such as `Observation` or `ServiceRequest`), the `reference` string must strictly follow the format `ResourceType/ID` (e.g., `Patient/S12345`). Providing only the ID (e.g., `S12345`) is a common error that leads to resource storage failures or invalid references.

## When to Use This Skill
- When constructing a POST or PUT request for any FHIR resource containing a `subject` object.
- Whenever you have retrieved a patient ID or MRN and need to link it to a new clinical resource.

## Common Failure Patterns
- Using `"reference": "MRN_VALUE"` instead of `"reference": "Patient/MRN_VALUE"`.
- Assuming the API will automatically infer the resource type from the ID string.

## Recommended Patterns

**Pattern 1: Reference Formatting**
Always prepend the resource type and a forward slash to the identifier.

CORRECT: `"subject": { "reference": "Patient/S6531922" }`
WRONG:   `"subject": { "reference": "S6531922" }`

**Pattern 2: Verification**
Before finalizing the POST body, verify that the `subject.reference` field contains the literal string "Patient/" followed by the patient's identifier.

## Example Application

**Task:** "Record blood pressure for patient S6531922."

**Step-by-step:**
1. Perform GET to confirm patient existence and retrieve the correct ID.
2. Construct the Observation resource.
3. Set `subject.reference` to `"Patient/S6531922"`.
4. Execute POST.

## Success Indicators
- POST requests are accepted by the server without validation errors.
- Resources are correctly linked to the patient record in the FHIR store.

## Failure Indicators
- Server returns 400 Bad Request or validation errors regarding the `subject` field.
- Resource is created but cannot be retrieved via patient-specific queries.
