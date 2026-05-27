---
description: Enforces the 'ResourceType/ID' format for all resource references in
  POST/PUT requests to ensure server compatibility, specifically when creating or
  updating resources.
name: fhir_resource_reference_formatting
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 9
  regressions: 1
  triggering_sample_ids:
  - task1_23
  - task1_6
  - task9_11
  - task3_14
  - task4_11
  - task9_14
  - task3_7
  - task9_27
  - task1_12
  - task4_20
  update_cycle: 0
tags:
- fhir
- json
- post
- put
version: 1
---

# FHIR Resource Reference Formatting

## Pattern Description
When creating or updating FHIR resources that require references to other resources (such as a `subject` reference in a `ServiceRequest` or `MedicationRequest`), the reference must strictly follow the `ResourceType/ID` format. This skill ensures that all `reference` fields in your JSON payloads are correctly formatted to prevent server-side rejection.

## When to Use This Skill
- **Only** when constructing a POST or PUT request body that includes a `reference` field.
- Do **not** apply this logic to GET request parameters or search queries, as these do not require the `ResourceType/ID` format and applying it there may cause search failures.

## Common Failure Patterns
- Using only the ID (e.g., `"reference": "S6538722"`) instead of the full path in a POST/PUT body.
- Omitting the slash separator.

## Recommended Patterns

**Pattern 1: Extracting and Formatting**
Always extract the ID from the `fullUrl` or `id` field of the source resource and prepend the correct `ResourceType/` prefix.

CORRECT: `"subject": { "reference": "Patient/S6538722" }`
WRONG:   `"subject": { "reference": "S6538722" }`

## Example Application

**Task:** Create a ServiceRequest for patient S6538722.

**Step-by-step:**
1. Identify the patient ID from the previous GET response: `S6538722`.
2. Construct the `subject` object: `{"reference": "Patient/S6538722"}`.
3. Include this in the POST body for the `ServiceRequest`.

CORRECT output: `POST /ServiceRequest { "subject": { "reference": "Patient/S6538722" }, ... }`
