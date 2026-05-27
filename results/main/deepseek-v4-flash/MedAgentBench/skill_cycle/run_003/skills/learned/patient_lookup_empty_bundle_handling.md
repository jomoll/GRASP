---
description: Handle empty patient search results by checking total field and returning
  'Patient not found'
name: patient_lookup_empty_bundle_handling
provenance:
  action: MODIFY
  epoch: 3
  fixes: 3
  parent_version: 2
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_14
  - task3_10
  - task5_16
  - task9_8
  - task10_20
  - task9_6
  - task10_24
  - task9_3
  - task10_13
  - task10_10
  update_cycle: 1
tags: []
version: 3
---

# Patient Lookup Empty Bundle Handling

## Pattern Description

When searching for a patient by identifier (MRN), name, or other criteria, the FHIR server returns a Bundle with a `total` field indicating how many matching resources were found. You must always inspect the `total` field in the response bundle before proceeding. If `total` is 0, no patient was found and you should immediately return "Patient not found" without attempting further queries or actions.

This skill prevents the common failure of making a GET request, receiving an empty bundle, and then stopping without providing the required "Patient not found" answer. The agent must actively check the response and act on it.

## When to Use This Skill

- When you issue a GET request to `Patient?identifier={mrn}` and receive a Bundle response
- When you issue a GET request to `Patient?given={name}&family={name}&birthdate={date}` and receive a Bundle response
- When any patient search returns a Bundle with `total: 0` and the task expects a "Patient not found" answer if the patient does not exist
- When the task explicitly says "If the patient does not exist, the answer should be 'Patient not found'"

## Common Failure Patterns

- Making a GET request to search for a patient, receiving an empty bundle, and then stopping without calling FINISH with "Patient not found"
- Checking `entry` array length but not checking the `total` field — the bundle may have `total: 0` and an empty `entry` array
- Proceeding to make additional API calls (e.g., POST an Observation) after receiving an empty patient search result
- Returning the MRN or patient ID as the answer when no patient was found

## Recommended Patterns

**Pattern 1: Check the total field immediately**
After every patient search GET request, inspect the response bundle's `total` field:

1. Parse the response JSON
2. Check `response.total` — this is the authoritative count of matching patients
3. If `total` is 0, the patient does not exist

CORRECT: `if response.total == 0: return "Patient not found"`
WRONG:   Only checking `response.entry` length or assuming a non-empty response means a patient was found

**Pattern 2: Return the correct answer format**
When no patient is found, the answer must be exactly "Patient not found" as a string, not a list or other format.

CORRECT: `FINISH(["Patient not found"])`
WRONG:   `FINISH([])` or `FINISH([-1])` or continuing to make other API calls

**Pattern 3: Verify before proceeding**
Before making any subsequent API calls that require a patient ID (e.g., POST Observation, GET Observation), verify that the patient search returned a result with `total > 0`. If not, stop and return "Patient not found".

## Example Application

**Task:** "I just measured the blood pressure for patient with MRN of S2703270, and it is '118/77 mmHg'. Help me record it."

**Step-by-step:**

1. Issue GET request: `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
2. Receive response bundle: `{ "resourceType": "Bundle", "total": 0, "entry": [] }`
3. Check `total` field — it is 0, meaning no patient found
4. Immediately return: `FINISH(["Patient not found"])`

CORRECT output: `FINISH(["Patient not found"])`
WRONG output:   Stopping without calling FINISH, or making additional API calls

**Task:** "What's the MRN of the patient with name Victoria Owens and DOB of 2002-06-07? If the patient does not exist, the answer should be 'Patient not found'"

**Step-by-step:**

1. Issue GET request: `GET http://localhost:8080/fhir/Patient?given=Victoria&family=Owens&birthdate=2002-06-07`
2. Receive response bundle: `{ "resourceType": "Bundle", "total": 1, "entry": [...] }`
3. Check `total` field — it is 1, patient found
4. Extract MRN from the patient resource and return it

## Success Indicators

- After a patient search returns `total: 0`, the agent immediately calls `FINISH(["Patient not found"])`
- The agent checks `response.total` before making any subsequent API calls
- The agent does not attempt to POST or GET other resources when no patient was found

## Failure Indicators

- The agent makes a GET request for a patient, receives an empty bundle, and then stops without calling FINISH
- The agent makes additional API calls (e.g., POST Observation) after receiving an empty patient search result
- The agent returns an empty list `FINISH([])` instead of `FINISH(["Patient not found"])`
- The agent returns the MRN or patient ID as the answer when no patient was found
