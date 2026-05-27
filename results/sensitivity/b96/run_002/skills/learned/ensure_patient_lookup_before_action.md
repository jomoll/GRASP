---
description: Require a GET /Patient query before any operation that needs a patient
  reference
name: ensure_patient_lookup_before_action
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task3_7
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task3_30
  - task4_28
  - task4_7
  - task10_8
  update_cycle: 0
tags:
- patient_lookup
- precondition
- fhir_query
version: 1
---

# Ensure Patient Lookup Before Dependent Actions

## Pattern Description
You must always retrieve the FHIR Patient resource for a given MRN (or other identifier) before performing any downstream action that depends on a patient reference. This includes creating Observations, calculating age, or fetching other resources (e.g., Observation, Condition) that require a `subject` reference. By guaranteeing a successful patient lookup first, you avoid malformed POST bodies and undefined age calculations.

## When to Use This Skill
- When the instruction mentions a patient MRN/identifier and the next step is to **POST** an Observation, ServiceRequest, MedicationRequest, etc.
- When the instruction asks for the **age** of a patient or any calculation that needs the patient’s `birthDate`.
- When you need to **GET** another resource (Observation, Condition, etc.) filtered by `patient=` and you only have the MRN, not the full reference.
- Any task that will reference `Patient/{id}` in the request body or query parameters.

## Common Failure Patterns
- Skipping the GET request and directly using the MRN in a POST `subject.reference` (e.g., `"reference": "Patient/S123456"` without confirming the ID exists).
- Attempting to compute age from a hard‑coded MRN without first retrieving the patient’s `birthDate`.
- Using the MRN string in an Observation GET query (`patient=S123456`) without confirming the patient exists, leading to empty bundles.
- Posting an Observation or ServiceRequest before the patient lookup, causing the server to reject the request.

## Recommended Patterns
**Pattern 1: mandatory patient lookup**
1. Detect that the task mentions a patient identifier (MRN, identifier, name+DOB, etc.).
2. Issue a GET request:
   ```
   GET {api_base}/Patient?identifier={MRN}
   ```
   - If the task supplies name/DOB instead, use the appropriate search parameters (`family`, `given`, `birthdate`).
3. Verify the response bundle has `total >= 1` and extract the first entry’s `resource.id`.
4. Store the full reference string `Patient/{id}` for later use.

**Pattern 2: fallback when patient not found**
- If the GET returns `total == 0`, abort the downstream action and return a clear message such as `"Patient not found"` or `"Cannot record observation because patient does not exist"`.
- Do **not** attempt a POST or age calculation.

**Pattern 3: use the extracted reference**
- For a POST Observation:
  ```json
  {
    "resourceType": "Observation",
    "subject": { "reference": "Patient/{id}" },
    ...
  }
  ```
- For age calculation:
  - Parse `birthDate` from the patient resource.
  - Compute `age = floor((now - birthDate) / 1 year)`.
- For any other GET that needs a patient filter, use `patient=Patient/{id}`.

## Example Application
**Task:** "I just measured the blood pressure for patient with MRN of S6534835, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. Detect MRN `S6534835` and that we need to record a blood pressure Observation.
2. Issue `GET http://localhost:8080/fhir/Patient?identifier=S6534835`.
3. Receive a Bundle with `entry[0].resource.id = "S6534835"` (or another internal ID). Build reference `Patient/S6534835`.
4. POST the Observation using that reference:
   ```
   POST http://localhost:8080/fhir/Observation
   {
     "resourceType": "Observation",
     "category": [{"coding":[{"system":"http://hl7.org/fhir/observation-category","code":"vital-signs","display":"Vital Signs"}]}],
     "code": {"text": "BP"},
     "effectiveDateTime": "2023-11-13T10:15:00+00:00",
     "status": "final",
     "valueString": "118/77 mmHg",
     "subject": {"reference": "Patient/S6534835"}
   }
   ```
5. FINISH with a success message.

## Success Indicators
- The first action in the trace is a GET `/Patient` request.
- The POST body contains `"subject": { "reference": "Patient/{id}" }` where `{id}` matches the ID returned by the GET.
- No POST is attempted if the GET returns an empty bundle.

## Failure Indicators
- A POST Observation (or other resource) is issued before any GET `/Patient`.
- The POST uses the raw MRN string without confirming the patient exists.
- Age is calculated without first retrieving the patient’s `birthDate`.
- The agent returns a result without having performed the required GET request.
