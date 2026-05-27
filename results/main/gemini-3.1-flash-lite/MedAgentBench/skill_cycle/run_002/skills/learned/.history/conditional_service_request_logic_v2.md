---
description: Enforce strict conditional logic for ServiceRequest creation, including
  mandatory resource reference formatting.
name: conditional_service_request_logic
provenance:
  action: MODIFY
  epoch: 0
  fixes: 2
  parent_version: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task4_26
  - task9_28
  - task2_9
  - task5_17
  - task9_3
  - task9_27
  - task2_15
  - task2_6
  - task10_24
  - task8_9
  update_cycle: 1
tags:
- fhir
- servicerequest
- validation
version: 2
---

# ServiceRequest Creation and Validation Strategy

## Pattern Description
When creating a `ServiceRequest` resource, you must ensure that all references to other resources (such as `Patient`) follow the strict FHIR `ResourceType/ID` format. Additionally, you must verify that the request is only generated when the specific clinical conditions (e.g., lab thresholds, time-since-last-test) are met. 

## When to Use This Skill
- When the task requires creating a `ServiceRequest` (e.g., lab orders, referrals).
- When the task involves conditional logic based on lab results or time-based thresholds.
- When you have retrieved a patient identifier and need to link it to a new resource.

## Common Failure Patterns
- Using an incorrect reference format (e.g., just the ID `S12345` instead of `Patient/S12345`).
- Failing to verify the existence of a patient or the validity of the lab result before posting.
- Omitting the `subject` field or providing an unformatted string.

## Recommended Patterns

**Pattern 1: Resource Reference Formatting**
Always format the `subject.reference` field as `"Patient/{MRN}"`. 
CORRECT: `"subject": { "reference": "Patient/S6192632" }`
WRONG: `"subject": { "reference": "S6192632" }`

**Pattern 2: Conditional Validation**
Before issuing the `POST`, confirm the clinical criteria are met. If the criteria (e.g., "within 24 hours") are not met, do not proceed with the `POST`.

**Pattern 3: Verification**
After the `POST`, ensure the response indicates success. If the system returns a warning that the resource was not found, re-verify the `subject` reference format.

## Example Application

**Task:** "Check patient S6192632's last serum magnesium level. If low, order IV magnesium."

**Step-by-step:**
1. GET `.../Observation?code=MG&patient=S6192632`.
2. Evaluate the result against the threshold.
3. If ordering, construct the `ServiceRequest` with `"subject": { "reference": "Patient/S6192632" }`.
4. POST the JSON to `.../ServiceRequest`.

## Success Indicators
- `ServiceRequest` is accepted by the server.
- The `subject` field correctly uses the `Patient/` prefix.

## Failure Indicators
- Server returns an error or warning regarding resource resolution.
- The `subject` field is missing or incorrectly formatted.
