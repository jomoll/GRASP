---
description: Enforce issuing a GET request for needed FHIR resources before any computation
  or POST that depends on that data.
name: require_fhir_query
provenance:
  action: ADD
  epoch: 2
  fixes: 9
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - task1_27
  - task10_20
  - task10_27
  - task1_10
  - task8_23
  - task3_12
  - task2_6
  - task3_17
  - task2_28
  - task1_7
  update_cycle: 0
tags:
- require_fhir_query
- resource_fetch
- precondition
version: 1
---

# Require FHIR Query Before Using Resource Data

## Pattern Description
You must never assume that patient identifiers, ages, or observation values are available without first retrieving them from the FHIR server. For any task that references a patient (by MRN, name, or DOB) or an observation (by code, patient, and date range), the first operational step is a GET request that returns a Bundle. Only after confirming the Bundle contains the expected entry should you extract fields, compute ages, or build POST bodies. This prevents "missing_fhir_query" failures where the agent tries to compute or reference data that has never been fetched.

## When to Use This Skill
- When the instruction asks for a patient attribute (e.g., age, MRN, name lookup).
- When the instruction asks for the most recent value of a lab or vital sign.
- When constructing a new Observation or ServiceRequest that requires a `subject.reference` to a Patient.
- When the task involves conditional logic based on a value that must come from an Observation.

## Common Failure Patterns
- Directly computing age from a hard‑coded date without a preceding `GET Patient?...` request.
- Building an Observation payload with `subject.reference = "Patient/S123"` without first confirming the patient exists.
- Attempting to extract `valueQuantity.value` from an empty Observation bundle and proceeding as if a value were present.
- Returning `-1` for a missing measurement without first checking the bundle for entries.

## Recommended Patterns
**Pattern 1: Identify and fetch the required resource**
1. Parse the instruction to determine the needed FHIR resource type (Patient or Observation).
2. Construct the appropriate GET URL:
   - Patient by MRN: `GET {base}/Patient?identifier={MRN}`
   - Patient by name/DOB: `GET {base}/Patient?given={given}&family={family}&birthdate={YYYY-MM-DD}`
   - Observation by code/date: `GET {base}/Observation?code={CODE}&patient={MRN}&date=ge{ISO8601}`
3. Issue the GET request **as the first action** and wait for the response.

**Pattern 2: Validate the response before proceeding**
- If `Bundle.total == 0`, apply the task‑specific fallback (e.g., return `-1`, use a broader date range, or report "Patient not found").
- If `Bundle.total > 0`, extract the needed field:
  - Patient ID: `entry[0].resource.id`
  - Observation value: `entry[0].resource.valueQuantity.value` (or `valueString` for BP).

**Pattern 3: Use the extracted data in subsequent actions**
- For age: compute `age = floor((now - birthDate) / 365.25)` using the `birthDate` from the Patient resource.
- For Observation POST: set `subject.reference = "Patient/{id}"` where `{id}` is the extracted Patient ID.
- For conditional orders: evaluate the extracted numeric value before deciding to POST a ServiceRequest.

## Example Application
**Task:** "What's the age of the patient with MRN of S0722219?"

**Step‑by‑step:**
1. Identify needed resource → Patient.
2. Issue `GET http://localhost:8080/fhir/Patient?identifier=S0722219`.
3. Receive Bundle; extract `birthDate` from `entry[0].resource.birthDate`.
4. Compute age using current time `2023-11-13T10:15:00+00:00`.
5. Return `FINISH([age])` as a plain number (scalar formatting handled by another skill).

**Correct output:** `FINISH([45])` (assuming birthDate yields 45 years).
**Wrong output (missing query):** Directly returning a hard‑coded number or skipping step 1.

## Success Indicators
- The first action in the trace is a GET request for the required resource.
- The agent checks `Bundle.total` before extracting any field.
- Subsequent actions (POST, FINISH) reference IDs or values obtained from the GET response.

## Failure Indicators
- No GET request appears before a computation or POST that needs patient/observation data.
- The agent attempts to read fields from a response that was never requested.
- FINISH is called with a value that was not derived from a verified FHIR response.
