---
description: Handle empty patient search results by immediately returning 'Patient
  not found'
name: patient_lookup_empty_bundle_handling
provenance:
  action: MODIFY
  epoch: 2
  fixes: 5
  parent_version: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task10_17
  - task10_10
  - task9_28
  - task10_13
  - task9_20
  - task10_12
  - task1_12
  - task5_3
  - task10_20
  - task10_27
  update_cycle: 0
tags: []
version: 2
---

# Patient Lookup Empty Bundle Handling

## Pattern Description

When you perform a GET request to search for a patient (by identifier, name, or other criteria) and the response bundle has zero entries, you must immediately stop further processing and return "Patient not found" as the final answer. Do not proceed to query observations, create orders, or perform any other actions for a patient that does not exist in the system.

The key capability is inspecting the `total` field of a searchset Bundle response and recognizing that a value of 0 means the patient does not exist. This applies to any patient lookup, whether by MRN/identifier, name+birthdate, or other search parameters.

## When to Use This Skill

- When you issue `GET /Patient?identifier={value}` and receive a Bundle response
- When you issue `GET /Patient?name={name}&birthdate={date}` and receive a Bundle response
- When you issue `GET /Patient?given={given}&family={family}&birthdate={date}` and receive a Bundle response
- Any time you search for a patient resource and need to check if the patient exists before proceeding

## Common Failure Patterns

- Issuing a patient lookup, receiving an empty bundle (`"total": 0`), but continuing to query Observations or other resources anyway
- Issuing a patient lookup, receiving an empty bundle, but proceeding to POST a ServiceRequest or MedicationRequest for a non-existent patient
- Not checking the `total` field at all and assuming the patient exists
- Checking the `entry` array instead of `total` — the `entry` field may be absent entirely when `total` is 0

## Recommended Patterns

**Pattern 1: Inspect the bundle response immediately**
After every GET /Patient request, examine the response JSON. Look at the `total` field at the top level of the Bundle object.

CORRECT: Check `response.total` — if it equals 0, the patient does not exist.
WRONG:   Checking `response.entry` — this may be undefined/null when total is 0, causing errors.

**Pattern 2: Return "Patient not found" immediately**
If `total` is 0, call `FINISH(["Patient not found"])` right away. Do not make any additional API calls.

CORRECT: `FINISH(["Patient not found"])`
WRONG:   Continuing to make Observation queries or other requests

**Pattern 3: Extract patient ID when patient exists**
If `total` is 1 or more, extract the patient's FHIR ID from `response.entry[0].resource.id` for use in subsequent queries.

## Example Application

**Task:** "Check patient S6488980's most recent potassium level. If low, then order replacement potassium."

**Step-by-step:**

1. Issue GET request: `GET http://localhost:8080/fhir/Patient?identifier=S6488980`
2. Receive response: `{ "resourceType": "Bundle", "total": 0, ... }`
3. Inspect `total` field — it is 0.
4. Immediately call `FINISH(["Patient not found"])` — do not query Observations or order anything.

CORRECT output: `FINISH(["Patient not found"])`
WRONG output:   Continuing to query `GET /Observation?code=K&patient=S6488980`

## Success Indicators

- Agent checks `total` field after every patient GET request
- Agent immediately returns "Patient not found" when total is 0
- No subsequent API calls are made after detecting an empty patient bundle

## Failure Indicators

- Agent makes additional API calls (Observation, ServiceRequest, etc.) after receiving an empty patient bundle
- Agent returns a value other than "Patient not found" when patient does not exist
- Agent crashes or errors when trying to access `response.entry[0]` on an empty bundle
