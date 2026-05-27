---
description: After any Patient lookup, wait for the Bundle and reuse the resolved
  Patient.id in all later queries and writes.
name: patient_lookup_handoff_before_downstream_fhir_actions
provenance:
  action: ADD
  epoch: 4
  fixes: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task8_19
  - task10_10
  - task8_13
  - task8_9
  - task3_1
  - task9_3
  update_cycle: 1
tags:
- fhir
- patient-lookup
- references
- queries
- writes
version: 1
---

# Patient Lookup Handoff Before Downstream FHIR Actions

## Pattern Description

When a task starts from an MRN or other patient identifier, you must treat the first `GET /Patient?...` as a lookup step, not as proof that the identifier itself is a valid FHIR reference. After the lookup returns, you must extract the actual `Patient.id` from the Bundle and carry that resolved id into every downstream `Observation` query and every write resource `subject.reference`.

This skill changes behavior in multi-step tasks where I first identify a patient and then immediately query labs or create resources. I must pause after the patient search response, parse `entry[0].resource.id`, and rebuild later requests from that value rather than reusing the source identifier string from the prompt.

## When to Use This Skill

- When the task names a patient by MRN or identifier such as `S6530813`
- When I issue `GET /fhir/Patient?identifier=...` before any later `GET /Observation`, `POST /Observation`, `POST /MedicationRequest`, or `POST /ServiceRequest`
- When constructing a resource body with `subject.reference`
- When constructing a query with `patient=...` after a prior patient lookup step
- When a previous attempt failed because `subject.reference` used `Patient/{MRN}` without first extracting a returned `Patient.id`

## Common Failure Patterns

- Sending `GET /fhir/Patient?identifier=S6530813POST ...` as one combined action instead of waiting for the Patient Bundle
- Using `subject.reference: "Patient/S6530813"` directly from the prompt before reading `entry[0].resource.id`
- Querying `GET /Observation?patient=S6550627&code=K` after lookup without confirming the resolved patient id from the Patient Bundle
- Treating `Bundle.total: 0` from a malformed combined request as if the patient truly was not found
- Posting a write resource before the patient lookup response arrives
- Extracting `entry[0].fullUrl` and copying the whole URL instead of the id portion from `entry[0].resource.id`

## Recommended Patterns

**Pattern 1: perform patient lookup as a standalone first step**
Issue only the patient search first.

CORRECT: `GET /fhir/Patient?identifier=S6530813`
WRONG:   `GET /fhir/Patient?identifier=S6530813POST /fhir/ServiceRequest`

When the Bundle returns, inspect:
- `entry`
- `entry[0].resource.id`
- optionally verify `entry[0].resource.identifier[].value`

Use `resolved_patient_id = entry[0].resource.id`.

**Pattern 2: reuse the resolved id in every downstream action**
For read queries, set the patient search parameter from the resolved id.
For writes, set `subject.reference` to `Patient/{resolved_patient_id}`.

CORRECT query: `GET /fhir/Observation?patient=12345&code=K`
CORRECT write field: `"subject": {"reference": "Patient/12345"}`
WRONG query: `GET /fhir/Observation?patient=S6550627&code=K`
WRONG write field: `"subject": {"reference": "Patient/S6550627"}`

If the returned `Patient.id` happens to equal the MRN string, still treat it as resolved only after reading it from the Bundle.

**Pattern 3: handle empty lookup before proceeding**
If `entry` is absent or empty, do not issue downstream patient-specific queries or writes. Finish with the task-appropriate not-found output instead of inventing a reference.

## Example Application

**Task:** "Order orthopedic surgery referral for patient S6530813. Specify within the free text of the referral ..."

## Step-by-step:

1. Issue only: `GET http://localhost:8080/fhir/Patient?identifier=S6530813`
2. From the response Bundle, extract `entry[0].resource.id`.
3. Build the referral using that resolved id in `subject.reference`.
4. POST the resource.

Correct POST body pattern:
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "subject": {
    "reference": "Patient/<resolved_patient_id>"
  },
  "note": [
    {
      "text": "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."
    }
  ]
}
```

CORRECT output: `FINISH(["done"])`
WRONG output:   `FINISH([])` after posting with `"reference":"Patient/S6530813"` without extracting the lookup result

## Success Indicators

- I issue the patient lookup as its own action and wait for the response
- I extract `entry[0].resource.id` before any later patient-specific action
- All later `patient=` query parameters and `subject.reference` values use the resolved id
- I do not post a resource when the patient lookup Bundle is empty

## Failure Indicators

- A single action string contains both the patient GET and a later GET/POST
- `subject.reference` is copied directly from the prompt identifier rather than the lookup result
- An Observation query uses `patient=<source identifier>` even though a Patient lookup was already performed
- I continue to downstream actions after a Patient Bundle with no `entry`
- I finish with empty output because the malformed combined request produced `total: 0`
