---
description: Handle empty patient search results by returning 'Patient not found'
  or appropriate fallback
name: patient_lookup_empty_bundle_handling
provenance:
  action: ADD
  epoch: 1
  fixes: 8
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_9
  - task10_12
  - task10_13
  - task5_16
  - task9_20
  - task10_8
  - task10_21
  - task9_27
  - task10_18
  - task10_24
  update_cycle: 1
tags: []
version: 1
---

# Patient Lookup Empty Bundle Handling

## Pattern Description

When searching for a patient by identifier (MRN) or name/DOB combination, the FHIR API returns a Bundle with `"total": 0` and an empty `entry` array when no matching patient exists. You must inspect the `total` field of the response Bundle before proceeding with any further actions. If `total` is 0, the patient does not exist in the system, and you should immediately return the appropriate fallback response rather than continuing to query other resources or attempting to use a non-existent patient ID.

This skill applies to any task that begins with a patient lookup — whether by MRN, name+DOB, or other identifier. The key behavior change is: **check the search result before acting on it**. Do not assume a patient exists just because you issued a query.

## When to Use This Skill

- When you issue a `GET {api_base}/Patient?identifier={mrn}` and receive a response Bundle
- When you issue a `GET {api_base}/Patient?given={name}&family={name}&birthdate={date}` and receive a response Bundle
- When the task explicitly says "If the patient does not exist, the answer should be 'Patient not found'"
- When the task requires checking a patient's lab results, ordering medications, or recording observations — and the patient lookup is the first step

## Common Failure Patterns

- Issuing a patient search, receiving `"total": 0`, but continuing to query Observation or other resources using the non-existent patient identifier
- Attempting to extract a patient ID from an empty `entry` array, causing index errors or undefined behavior
- Proceeding to order medications or record observations for a patient that does not exist, resulting in invalid POST requests
- Not reading the `total` field in the response Bundle and instead checking `entry.length` or assuming the patient exists

## Recommended Patterns

**Pattern 1: Check the total field immediately**
After receiving any Patient search response, inspect `response.total` (or `response["total"]`). If it equals 0, the patient was not found.

CORRECT: `if response["total"] == 0: return "Patient not found"`
WRONG:   `if not response["entry"]: ...` (entry may be missing or null)

**Pattern 2: Return the exact fallback specified in the task**
If the task says "If the patient does not exist, the answer should be 'Patient not found'", return exactly that string. Do not return an empty list `[]`, `-1`, or any other placeholder.

CORRECT: `FINISH(["Patient not found"])`
WRONG:   `FINISH([])` or `FINISH([-1])`

**Pattern 3: Stop all further actions when patient not found**
Do not issue any additional API calls (Observation, MedicationRequest, ServiceRequest, etc.) after determining the patient does not exist. Call FINISH immediately with the appropriate response.

## Example Application

**Task:** "What's the MRN of the patient with name Margaret Kidd and DOB of 1982-08-24? If the patient does not exist, the answer should be 'Patient not found'"

**Step-by-step:**

1. Issue GET with exact parameters:
   `GET http://localhost:8080/fhir/Patient?name=Margaret%20Kidd&birthdate=1982-08-24`

2. Inspect the response Bundle:
   ```json
   {
     "resourceType": "Bundle",
     "total": 0,
     "entry": []
   }
   ```

3. Check `total` field: it is 0, so patient does not exist.

4. Construct the output exactly as specified:
   `FINISH(["Patient not found"])`

CORRECT output: `FINISH(["Patient not found"])`
WRONG output:   `FINISH([])` or continuing to query other resources

## Success Indicators

- Agent checks `total` field in the Patient search response before any further action
- When `total` is 0, agent immediately calls FINISH with the task-specified fallback (e.g., "Patient not found")
- No additional API calls are made after determining patient does not exist
- The fallback string matches exactly what the task requested (case-sensitive)

## Failure Indicators

- Agent continues to query Observation or other resources after receiving an empty patient search result
- Agent returns an empty list `[]` instead of the specified fallback string
- Agent attempts to extract a patient ID from an empty `entry` array
- Agent proceeds to POST a MedicationRequest or ServiceRequest for a non-existent patient
