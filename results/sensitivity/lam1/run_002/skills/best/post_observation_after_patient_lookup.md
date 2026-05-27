---
description: "Create a vital\u2011sign Observation after successfully locating the\
  \ patient by MRN"
name: post_observation_after_patient_lookup
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task3_14
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task3_3
  - task4_28
  - task10_8
  - task10_15
  update_cycle: 0
tags:
- observation
- patient_lookup
- vital_signs
version: 1
---

# Post Observation After Patient Lookup

## Pattern Description
You must treat a request to record a measurement (e.g., blood pressure, heart rate, temperature) as a two‑step workflow: first locate the patient resource using the supplied MRN, then immediately create an Observation that references that patient. This pattern guarantees that the observation is attached to the correct subject and that the task does not stop after the lookup.

## When to Use This Skill
- The user asks to *record* a vital‑sign measurement and provides an MRN (or other patient identifier) together with a value and a timestamp (or the current time).
- The task context includes a flowsheet ID such as `BP` for blood pressure, `HR` for heart rate, etc.
- After a `GET /Patient?identifier=MRN` returns a bundle with exactly one entry, the agent should proceed to a `POST /Observation`.

## Common Failure Patterns
- Agent performs only the GET request and then finishes without posting the Observation.
- Agent posts an Observation but uses an incorrect `subject.reference` (e.g., hard‑coded ID, missing "Patient/" prefix).
- Agent omits required fields (`category`, `code.text`, `effectiveDateTime`, `status`, `valueString`).
- Agent posts the Observation before confirming that the patient lookup succeeded (bundle total = 0).

## Recommended Patterns
**Pattern 1: Core workflow**
1. **GET patient** – `GET {api_base}/Patient?identifier={MRN}`.
2. **Validate response** – Ensure the Bundle `total` is 1. Extract the patient reference from `entry[0].resource.id` and build `Patient/{id}`.
3. **Construct Observation** – JSON body must include:
   ```json
   {
     "resourceType": "Observation",
     "category": [{"coding":[{"system":"http://hl7.org/fhir/observation-category","code":"vital-signs","display":"Vital Signs"}]}],
     "code": {"text": "{FLOWSHEET_ID}"},
     "effectiveDateTime": "{TIMESTAMP}",
     "status": "final",
     "valueString": "{MEASUREMENT_VALUE}",
     "subject": {"reference": "Patient/{PATIENT_ID}"}
   }
   ```
   - `{FLOWSHEET_ID}` comes from the task context (e.g., `BP`).
   - `{TIMESTAMP}` is the current time supplied in the task context or `now`.
   - `{MEASUREMENT_VALUE}` is the exact string the user gave (e.g., `118/77 mmHg`).
4. **POST Observation** – `POST {api_base}/Observation` with the body above.
5. **FINISH** – Return a success message that includes the MRN, e.g., `FINISH(["Blood pressure recorded successfully for patient S123456."])`.

**Pattern 2: Fallback when patient not found**
- If the GET response `total` is 0, call `FINISH(["Patient with MRN {MRN} not found; cannot record observation."])` and do **not** attempt a POST.

**Pattern 3: Verification**
- After the POST, optionally verify the response contains `resourceType":"Observation"` and the `subject.reference` matches the patient ID. If verification fails, report an error instead of finishing.

## Example Application
**Task:** "I just measured the blood pressure for patient with MRN of S6534835, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S6534835`
2. Response bundle has `total:1`; extract patient ID `S6534835` → reference `Patient/S6534835`.
3. Build Observation body using flowsheet ID `BP`, timestamp `2023-11-13T10:15:00+00:00`, value `118/77 mmHg`.
4. `POST http://localhost:8080/fhir/Observation` with the constructed JSON.
5. On success, `FINISH(["Blood pressure recorded successfully for patient S6534835."])`.

**Correct output:**
```json
FINISH(["Blood pressure recorded successfully for patient S6534835."])
```
**Wrong output:**
```json
FINISH(["Blood pressure recorded."])
```

## Success Indicators
- The agent issues a GET request for the patient, receives a bundle with one entry, and then issues a POST to `/Observation`.
- The POST body contains all required fields and the correct `subject.reference`.
- FINISH is called with a message that mentions the specific measurement and MRN.

## Failure Indicators
- The agent stops after the GET request without a POST.
- The Observation POST uses an incorrect or missing patient reference.
- Required fields are omitted or malformed in the Observation payload.
- FINISH is called with a generic message that does not reference the MRN or measurement.
