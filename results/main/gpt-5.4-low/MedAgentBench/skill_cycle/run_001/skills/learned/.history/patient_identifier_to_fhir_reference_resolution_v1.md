---
description: Resolve MRN/identifier to Patient.id before using patient search params
  or subject.reference fields.
name: patient_identifier_to_fhir_reference_resolution
provenance:
  action: ADD
  epoch: 1
  fixes: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task4_10
  - task10_24
  - task5_17
  - task9_6
  - task4_6
  - task4_27
  - task5_7
  update_cycle: 0
tags:
- fhir
- patient-resolution
- references
- search
version: 1
---

# Patient Identifier to FHIR Reference Resolution

## Pattern Description

When a task gives me a patient MRN or identifier such as `S0722219`, I must treat that value as a search key, not as a reusable FHIR resource reference. Before I query patient-linked resources or create new resources, I must first resolve the patient with `GET /Patient?identifier=...` and extract the actual `Patient.id` from the returned resource.

This changes behavior in two places: follow-up GET searches that use a `patient=` parameter, and POST bodies that use `subject.reference`. In both cases, I should use the resolved FHIR id, not the original MRN string, unless the Patient resource itself clearly shows they are identical.

## When to Use This Skill

- When the task names a patient by MRN or identifier and I need labs, vitals, medications, or orders for that patient
- When I start with `GET /Patient?identifier=<mrn>` and then need `GET /Observation`, `GET /Condition`, or other patient-scoped searches
- When constructing `Observation.subject.reference`, `MedicationRequest.subject.reference`, or `ServiceRequest.subject.reference`
- When a task says "patient S..." and I am about to place that `S...` string directly into `patient=` or `Patient/...`

## Common Failure Patterns

- Using `GET /Observation?patient=S0722219&code=A1C` immediately after a patient lookup instead of using the resolved `Patient.id`
- Posting `"subject": {"reference": "Patient/S6500497"}` when `S6500497` came from the task prompt rather than `Patient.id`
- Posting `"subject": {"reference": "S3236936"}` without the `Patient/` prefix and without id resolution
- Extracting `entry[0].resource.identifier[0].value` and reusing that as the FHIR reference instead of `entry[0].resource.id`
- Ignoring `entry[0].fullUrl` / `resource.id` from the Patient search response and continuing to use the original MRN everywhere
- Concluding an order is done after POST acceptance even though a bad `subject.reference` may prevent correct storage or retrieval

## Recommended Patterns

**Pattern 1: resolve once, then reuse the resolved id**
Before any downstream query or POST, issue `GET /Patient?identifier=<mrn>`.
From the returned Bundle, inspect `entry[0].resource.id` first. If needed, `entry[0].fullUrl` can confirm the same id.
Store that resolved id and use it consistently.

CORRECT: `GET /Observation?patient=eKMKb0urR6M6qdhG3fyhBzQ3&code=A1C`
WRONG:   `GET /Observation?patient=S0722219&code=A1C`

CORRECT: `"subject": {"reference": "Patient/eKMKb0urR6M6qdhG3fyhBzQ3"}`
WRONG:   `"subject": {"reference": "Patient/S0722219"}`

**Pattern 2: use resource.id, not identifier.value, for references**
In the Patient search result, distinguish these fields:
- `resource.id` = FHIR resource id for references and patient search params
- `resource.identifier[*].value` = MRN/identifier for human lookup only

If the task starts from name/DOB or MRN, I still must convert the match into `resource.id` before querying dependent resources or posting new ones.

**Pattern 3: build all downstream actions from the resolved id**
For GET searches, pass `patient=<resolved Patient.id>`.
For POST bodies, use `subject.reference = "Patient/<resolved Patient.id>"`.
Apply this to `Observation`, `ServiceRequest`, `MedicationRequest`, and similar resources.
Only finish after all created resources use the resolved reference format.

## Example Application

**Task:** "What’s the last HbA1C value in the chart for patient S0722219 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

## Step-by-step:

1. Issue `GET /Patient?identifier=S0722219`.
2. Extract `entry[0].resource.id` from the Bundle, for example `347755`.
3. Issue `GET /Observation?patient=347755&code=A1C`.
4. Extract the most recent result from the returned Observation.
5. If ordering is required, construct the POST body with `"subject": {"reference": "Patient/347755"}`.

CORRECT output body fragment:
`"subject": {"reference": "Patient/347755"}`

WRONG output body fragment:
`"subject": {"reference": "Patient/S0722219"}`

## Success Indicators

- After `GET /Patient?identifier=...`, I explicitly use `entry[0].resource.id` in later actions
- Follow-up searches use `patient=<resolved id>` rather than the MRN string
- POST bodies use `subject.reference` in the form `Patient/<resolved id>`
- I no longer mix identifier values and FHIR ids within the same task

## Failure Indicators

- Any downstream URL still contains `patient=S...` after a successful patient lookup
- Any POST body contains `"reference": "Patient/S..."` or just `"reference": "S..."`
- I cite a correct lab result but create an order tied to the wrong patient reference format
- A POST is accepted but later verification warns the resource may not have been stored correctly, and my subject reference used the MRN instead of `Patient.id`
