---
description: Resolve chart identifiers to Patient resource ids before building subject.reference
  in POST bodies, but only after a completed Patient lookup response is available.
name: patient_identifier_to_resource_reference_resolution
provenance:
  action: ADD
  epoch: 3
  fixes: 15
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task10_16
  - task10_21
  - task10_10
  - task10_12
  - task10_20
  - task10_8
  update_cycle: 0
tags: []
version: 1
---

# Patient Identifier to Resource Reference Resolution

## Pattern Description

When a task gives me a patient MRN, chart number, or identifier-like string such as `S0722219`, I must not copy that string directly into a FHIR reference. Before creating a resource that points to a patient, I should resolve the identifier to the actual Patient resource and then build `subject.reference` from the returned Patient id.

However, this rule applies only after I have the actual lookup result in hand. I must not guess a fallback id like `UNKNOWN`, and I must not combine the lookup request and the POST into one unresolved step.

## When to Use This Skill

- When I am about to create a resource with `subject.reference` or another patient reference
- When the patient is identified by MRN or chart identifier text rather than an explicit FHIR resource id
- When I can first perform `GET /Patient?identifier=<mrn>` and inspect the response before building the POST body

## Guard Clause: Do Not Post Before Lookup Resolution

If I do not yet have the response to `GET /Patient?identifier=<mrn>`, I should stop after issuing that GET and wait for the result.

I must **not**:
- send a POST with `subject.reference` set to `Patient/UNKNOWN`
- send a POST in the same action block before I have inspected the Patient search response
- concatenate `GET /Patient?identifier=...` and `POST /ServiceRequest` into one malformed request string
- claim `Patient not found` until I have actually inspected a completed Bundle response showing no matches

## Recommended Pattern

1. If given an MRN like `S0722219`, first issue `GET /Patient?identifier=S0722219`.
2. Wait for the actual Bundle response.
3. If `entry[0].resource.id` exists, build `subject.reference` as `Patient/<resource.id>`.
4. Only then create the POST body and send the POST.
5. If the Bundle has `total: 0` or no matching entry, do not POST the resource; report that the patient was not found.

## Correct vs Wrong

CORRECT sequence:
1. `GET /Patient?identifier=S0722219`
2. inspect response
3. `POST /ServiceRequest` with `"subject": {"reference": "Patient/84721"}`

WRONG sequence:
1. `GET /Patient?identifier=S0722219POST /ServiceRequest ...`
2. or POST with `"subject": {"reference": "Patient/UNKNOWN"}`
3. or POST with `"subject": {"reference": "Patient/S0722219"}`

## Common Failure Patterns

- Copying the MRN directly into `subject.reference`
- Using a placeholder reference such as `Patient/UNKNOWN`
- Posting before the Patient lookup response has been returned
- Treating a not-yet-executed or malformed lookup as evidence that the patient does not exist
- Reading `identifier.value` or `fullUrl` instead of `entry[0].resource.id`

## Success Indicators

- I perform the Patient lookup first when only an MRN is provided
- I wait for and inspect the lookup response before POSTing
- The POST body uses `subject.reference` built from `entry[0].resource.id`
- If no patient match exists, I do not create the resource

## Failure Indicators

- I send a POST with `Patient/<MRN>` or `Patient/UNKNOWN`
- I combine GET and POST into one malformed request/action
- I finish with `Patient not found` without first receiving and checking the Patient search Bundle
- I create the resource before resolving the patient id
