---
description: "Resolve a patient\u2019s FHIR reference from an MRN/identifier before\
  \ any resource creation or query that needs the patient."
name: patient_reference_by_identifier
provenance:
  action: ADD
  epoch: 3
  fixes: 12
  probe_score: 6
  regressions: 1
  triggering_sample_ids:
  - task5_3
  - task3_7
  - task9_11
  - task9_27
  - task3_3
  - task2_30
  - task3_14
  - task2_25
  - task9_20
  - task2_28
  update_cycle: 0
tags: []
version: 1
---

# Patient Reference Resolution by Identifier

## Pattern Description
You must always resolve a patient’s FHIR reference before using it in any subsequent request (POST, PUT, PATCH, or a GET that filters on `patient=`). The reliable way is to perform a `GET /Patient?identifier={MRN}` call, extract the exact identifier used in the `reference` field (e.g., `Patient/S1234567`), and reuse that string for all later API calls. This prevents the agent from constructing an invalid reference like a raw MRN or an empty string, which leads to failed POSTs or incorrect queries.

## When to Use This Skill
- When a task mentions an MRN, identifier, or any patient ID string and you need to create or update a resource that references the patient (e.g., Observation, ServiceRequest, MedicationRequest).
- When a GET request requires a `patient=` filter and you only have the MRN.
- When the task asks for a vital sign, lab, or order for a specific patient.

## Common Failure Patterns
- Skipping the lookup and using the raw MRN in `subject.reference` (e.g., `"reference": "S1234567"`).
- Using an empty or placeholder reference (`"reference": "Patient/"`).
- Assuming the MRN is the same as the FHIR resource ID without verification.
- Posting an Observation before confirming the patient exists, resulting in a 404 or silent failure.

## Recommended Patterns
**Pattern 1: Resolve patient reference**
1. Detect that the task provides an MRN/identifier.
2. Issue `GET {base}/Patient?identifier={MRN}`.
3. Verify the response Bundle has `total == 1`.
4. Extract the `fullUrl` or the `id` from the entry and build the reference string `Patient/{id}`.
5. Store this reference in a variable (e.g., `patient_ref`).

**Pattern 2: Use the resolved reference**
- For any subsequent POST/PUT/PATCH that needs a patient, set `subject.reference` (or equivalent) to the `patient_ref` value.
- For GET filters, use `patient={id}` (not the MRN).

**Pattern 3: Fallback handling**
- If the lookup returns `total == 0`, abort the task and return an error message like `"Patient not found for MRN {MRN}"`.
- If the lookup returns multiple entries, pick the first and log a warning.

## Example Application
**Task:** "I just measured the blood pressure for patient with MRN of S3236936, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. Detect MRN `S3236936` in the instruction.
2. `GET http://localhost:8080/fhir/Patient?identifier=S3236936`
3. Response Bundle contains one entry with `fullUrl: http://localhost:8080/fhir/Patient/S3236936` → `patient_ref = "Patient/S3236936"`.
4. Build Observation payload:
   ```json
   {
     "resourceType": "Observation",
     "category": [{"coding": [{"system": "http://hl7.org/fhir/observation-category", "code": "vital-signs"}]}],
     "code": {"text": "BP"},
     "effectiveDateTime": "2023-11-13T10:15:00+00:00",
     "status": "final",
     "valueString": "118/77 mmHg",
     "subject": {"reference": "Patient/S3236936"}
   }
   ```
5. `POST http://localhost:8080/fhir/Observation` with the payload.
6. Call `FINISH([])` after successful POST.

**CORRECT output:** `FINISH([])` after the POST succeeds.
**WRONG output:** Using `"reference": "S3236936"` or omitting the lookup step.

## Success Indicators
- The agent performs a GET on `/Patient?identifier=...` before any POST that references the patient.
- The Observation (or other resource) payload contains `"reference": "Patient/<id>"`.
- The POST request returns a success status and the agent finishes without error.

## Failure Indicators
- The agent posts a resource with `subject.reference` equal to the raw MRN or an empty string.
- No GET request to `/Patient` is observed before the POST.
- The POST fails (404 or validation error) and the agent does not report the missing patient.
