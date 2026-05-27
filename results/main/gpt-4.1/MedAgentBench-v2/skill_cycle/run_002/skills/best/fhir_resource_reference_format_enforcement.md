---
description: Ensure all FHIR resource references in POSTed resources use the correct
  'ResourceType/ID' format.
name: fhir_resource_reference_format_enforcement
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task4_27
  - task8_23
  - task2_26
  - task1_7
  - task3_29
  - task3_19
  - task1_10
  - task3_14
  - task3_30
  - task9_22
  update_cycle: 1
tags:
- fhir
- reference
- format
- post
- servicerequest
- medicationrequest
- resource-linking
version: 1
---

# FHIR Resource Reference Format Enforcement

## Pattern Description

When constructing FHIR resources for POST (such as ServiceRequest, MedicationRequest, Procedure, etc.), all references to other resources (e.g., the patient, encounter, practitioner) must use the correct FHIR reference format: `'ResourceType/ID'` (e.g., `Patient/S1234567`). This ensures that the FHIR server can resolve and link resources correctly. Omitting the resource type or using only the ID (e.g., `"S1234567"`) will result in resources that cannot be retrieved or linked properly, even if the POST is superficially accepted.

This pattern is critical for any field in a FHIR resource that is a reference, such as `subject.reference`, `encounter.reference`, `requester.reference`, etc. Failure to use the correct format leads to downstream errors, missing data, and resources that cannot be found by subsequent queries.

## When to Use This Skill

- When constructing any FHIR resource for POST that includes a reference to another resource (e.g., ServiceRequest, MedicationRequest, Procedure, Observation, etc.).
- When setting the value of fields like `subject.reference`, `encounter.reference`, `requester.reference`, or any other `Reference` field.
- When the only information available is the resource ID (e.g., patient ID like `S1234567`).

## Common Failure Patterns

- Setting `subject.reference` to just the ID (e.g., `"S1234567"`) instead of `"Patient/S1234567"`.
- Omitting the resource type prefix in any reference field.
- Using an incorrect resource type (e.g., `"Person/S1234567"` instead of `"Patient/S1234567"`).
- Using a full URL when only a relative reference is required (unless the server expects absolute references).

## Recommended Patterns

**Pattern 1: Always include resource type in reference**
- When constructing a reference, concatenate the resource type and the ID with a slash: `"ResourceType/ID"`.
- For patients, always use `"Patient/" + patient_id`.
- For encounters, use `"Encounter/" + encounter_id`, etc.

CORRECT:
```json
"subject": { "reference": "Patient/S1234567" }
```
WRONG:
```json
"subject": { "reference": "S1234567" }
```

**Pattern 2: Verification before POST**
- Before POSTing any resource, check all fields of type `Reference` and ensure they match the `ResourceType/ID` pattern.
- If only the ID is available, prepend the correct resource type.

**Pattern 3: Consistency across resource types**
- Apply this rule to all FHIR resources, not just ServiceRequest or MedicationRequest.
- If referencing other resource types (e.g., Practitioner, Encounter), use the same pattern: `"Practitioner/ID"`, `"Encounter/ID"`, etc.

## Example Application

**Task:** "Order a new CT Abdomen with IV contrast for patient S2111822."

**Step-by-step:**

1. Patient ID is `S2111822`.
2. Construct the ServiceRequest resource.
3. Set `subject.reference` to `"Patient/S2111822"`.
4. POST the following body:

CORRECT:
```json
{
  "resourceType": "ServiceRequest",
  ...
  "subject": { "reference": "Patient/S2111822" },
  ...
}
```
WRONG:
```json
{
  "resourceType": "ServiceRequest",
  ...
  "subject": { "reference": "S2111822" },
  ...
}
```

## Success Indicators

- All reference fields in POSTed resources use the `ResourceType/ID` format (e.g., `"Patient/S1234567"`).
- Resources can be retrieved and linked by subsequent GET requests using the reference.
- No warnings or errors about missing or unresolvable references after POST.

## Failure Indicators

- Reference fields contain only the ID without the resource type (e.g., `"S1234567"`).
- POSTed resources are accepted but cannot be found or linked on retrieval.
- Downstream tasks fail due to missing or unresolvable references.
- System notes or logs indicate resource not found on retrieval after POST.
