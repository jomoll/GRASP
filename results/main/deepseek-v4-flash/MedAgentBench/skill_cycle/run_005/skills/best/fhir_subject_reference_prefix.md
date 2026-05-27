---
description: Always prefix subject.reference with 'Patient/' when creating FHIR resources
name: fhir_subject_reference_prefix
provenance:
  action: ADD
  epoch: 1
  fixes: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task1_11
  - task1_6
  - task3_7
  - task10_27
  - task1_20
  - task9_6
  - task9_14
  - task10_8
  - task5_16
  - task2_9
  update_cycle: 1
tags: []
version: 1
---

# FHIR Subject Reference Prefix

## Pattern Description

When creating any FHIR resource that references a patient (Observation, ServiceRequest, MedicationRequest, etc.), the `subject.reference` field must always use the format `"Patient/{MRN}"` — never just the MRN number alone. This is a strict FHIR requirement: the reference must include the resource type prefix to be a valid canonical reference.

The agent must automatically prepend `"Patient/"` to any patient identifier (MRN, ID, etc.) when constructing the `subject.reference` field in POST or PUT request bodies. This applies regardless of how the patient is identified in the task description (e.g., "patient with MRN of S1234567" or "patient S1234567").

## When to Use This Skill

- When constructing a POST or PUT request body for any FHIR resource that has a `subject` field (Observation, ServiceRequest, MedicationRequest, Condition, etc.)
- When the task provides a patient identifier (MRN, ID, or reference) and you need to set the `subject.reference` field
- When you see a patient identifier in the instruction that looks like a code (e.g., "S1234567", "P987654") and need to reference it in a resource

## Common Failure Patterns

- Setting `subject.reference` to just the MRN number (e.g., `"S1579803"`) instead of `"Patient/S1579803"`
- Using the patient identifier directly from the task without adding the `"Patient/"` prefix
- Correctly using `"Patient/"` prefix in one resource type (e.g., ServiceRequest) but forgetting it in another (e.g., Observation)
- Assuming the server will accept bare identifiers — it may accept them silently but the resource will not be properly linked

## Recommended Patterns

**Pattern 1: Always prepend "Patient/" to the patient identifier**
When the task says "patient with MRN of S1234567" or "patient S1234567", extract the identifier and construct the reference as:

CORRECT: `"subject": { "reference": "Patient/S1234567" }`
WRONG:   `"subject": { "reference": "S1234567" }`

**Pattern 2: Verify the reference format before POST**
Before sending any POST/PUT request that includes a `subject` field, check that the `reference` value starts with `"Patient/"`. If it doesn't, add the prefix.

**Pattern 3: Consistent application across all resource types**
This rule applies to ALL resources with a `subject` field, not just Observation. Always use the same format:
- Observation: `"subject": { "reference": "Patient/S1234567" }`
- ServiceRequest: `"subject": { "reference": "Patient/S1234567" }`
- MedicationRequest: `"subject": { "reference": "Patient/S1234567" }`
- Condition: `"subject": { "reference": "Patient/S1234567" }`

## Example Application

**Task:** "I just measured the blood pressure for patient with MRN of S1579803, and it is '118/77 mmHg'. Help me record it."

**Step-by-step:**

1. Identify the patient identifier from the task: "S1579803"
2. Construct the Observation resource with the correct subject reference:
   - `"subject": { "reference": "Patient/S1579803" }`
3. Set other required fields (code, status, effectiveDateTime, value)
4. POST the complete resource

CORRECT POST body:
```json
{
  "resourceType": "Observation",
  "subject": {
    "reference": "Patient/S1579803"
  },
  "code": {
    "text": "BP"
  },
  "status": "final",
  "effectiveDateTime": "2023-11-13T10:15:00+00:00",
  "valueString": "118/77 mmHg"
}
```

WRONG POST body (missing "Patient/" prefix):
```json
{
  "resourceType": "Observation",
  "subject": {
    "reference": "S1579803"
  },
  ...
}
```

## Success Indicators

- All POST/PUT requests for resources with a `subject` field use `"Patient/{identifier}"` format
- The resource is properly linked to the patient in the FHIR server
- No warnings or errors related to invalid subject references

## Failure Indicators

- The agent uses bare identifiers like `"S1579803"` in `subject.reference`
- The resource is created but not properly linked to the patient (may not appear in patient searches)
- The agent inconsistently applies the prefix across different resource types
