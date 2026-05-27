---
description: Ensure a Patient resource is retrieved before computing age or creating
  an Observation
name: fetch_patient_before_dependent_action
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 10
  regressions: 2
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task4_10
  - task2_16
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  - task2_9
  update_cycle: 0
tags:
- patient
- age
- observation
version: 1
---

# Fetch Patient Record Before Age Calculation or Observation Creation

## Pattern Description
You must always retrieve the patient record from the FHIR server before you rely on any of its fields (e.g., `birthDate`) or use its reference in a subsequent resource creation. This guarantees that the patient exists, that you have the correct identifier, and that downstream calculations (such as age) are based on authoritative data. The pattern applies both to pure query tasks ("What is the age of patient X?") and to write‑back tasks ("Record a blood pressure Observation for patient X").

## When to Use This Skill
- When a task asks for the **age** of a patient identified only by MRN (or any identifier).
- When a task requires **recording an Observation** (vital sign, lab, etc.) for a patient and the only identifier provided is the MRN.
- Whenever you need to embed a patient reference (`Patient/{id}`) in a POST body.
- If the task description includes a time‑sensitive calculation (e.g., "rounded down to an integer"), you must first fetch the patient to obtain `birthDate`.

## Common Failure Patterns
- Skipping the `GET /Patient?identifier=...` request and directly computing age from an assumed value.
- Returning the age as a **string** or wrapped in a list (e.g., `FINISH(["45"])`) instead of a plain integer.
- Creating an `Observation` with a `subject.reference` that uses the MRN directly (`"Patient/S12345"`) without confirming the patient exists.
- Posting an Observation when the patient lookup returned `total: 0` (patient not found).

## Recommended Patterns
**Pattern 1: Fetch patient before using its data**
1. Issue `GET {api_base}/Patient?identifier={MRN}`.
2. Verify the response `Bundle.total > 0`.
3. Extract the patient **resource ID** from `entry[0].resource.id` and the `birthDate` field.
4. Compute age: `age = floor((current_time - birthDate) / 365.25 days)`.
5. Return the age as a plain integer: `FINISH([age])`.

**Pattern 2: Fetch patient before creating an Observation**
1. Issue the same `GET /Patient?identifier={MRN}` as above.
2. If `total == 0`, abort with `FINISH(["Patient not found"])`.
3. Use the extracted patient ID to build the reference: `"Patient/{id}"`.
4. Include that reference in the Observation `subject.reference` field.
5. POST the Observation.
6. Finish with a concise success message, e.g., `FINISH(["Blood pressure recorded successfully for patient {MRN}."])`.

**Pattern 3: Fallback when patient missing**
- If the patient lookup fails, do **not** proceed with age calculation or Observation creation. Immediately `FINISH(["Patient not found"])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
2. Response shows `total: 1` and `birthDate: "1978-04-22"`.
3. Compute age using the provided current time (`2023-11-13T10:15:00+00:00`).
4. `age = 45` (rounded down).
5. `FINISH([45])`.

**Correct output:** `FINISH([45])`
**Incorrect output:** `FINISH(["45"])` or `FINISH(["Age is 45 years."])`

## Success Indicators
- A `GET /Patient` request appears before any age calculation or Observation POST.
- The GET response contains `total > 0` and the agent extracts `birthDate`.
- The final `FINISH` payload is a single integer (for age) or a short string (for observation success).

## Failure Indicators
- No patient GET request is observed before the age is reported.
- The `FINISH` result contains a string or list instead of a plain integer for age.
- An Observation is posted with a `subject.reference` that was never validated.
- The agent proceeds to POST or compute age even when the patient lookup returned `total: 0`.
