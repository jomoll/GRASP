---
description: "Require a Patient GET before any Observation POST that records a vital\u2011\
  sign measurement."
name: ensure_patient_query_before_observation
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task3_29
  - task2_1
  - task3_3
  - task3_7
  - task2_14
  - task3_27
  - task2_30
  - task10_10
  - task3_16
  - task10_13
  update_cycle: 1
tags:
- vital-signs
- observation
- "patient\u2011lookup"
version: 1
---

# Ensure Patient Query Before Observation

## Pattern Description
You must always retrieve the patient resource before creating a new Observation that records a vital‑sign measurement (e.g., blood pressure, heart rate, temperature, weight). The patient GET provides the canonical FHIR ID needed for the `subject.reference` field of the Observation. Skipping this step can lead to malformed references, failed POSTs, or privacy‑compliant errors.

## When to Use This Skill
- When a task asks to *record* a measurement for a patient identified only by MRN (e.g., "I just measured the blood pressure for patient with MRN S123456, help me record it.")
- When the agent is about to issue a `POST /Observation` for a **vital‑signs** category.
- When the task mentions a flowsheet ID, measurement value, or unit (e.g., BP, HR, Temp) and does **not** already include a prior Patient GET.

## Common Failure Patterns
- Directly `POST /Observation` with `subject.reference = "Patient/S123456"` without first `GET /Patient?identifier=S123456`.
- Using the MRN string as the reference instead of the internal FHIR ID (e.g., `"Patient/S123456"` when the actual ID is `"12345"`).
- Omitting the `GET` entirely, causing the POST to be rejected or stored with an invalid reference.

## Recommended Patterns
**Pattern 1: Core strategy**
1. **Issue a GET**: `GET {api_base}/Patient?identifier={MRN}`.
2. **Extract the patient ID** from the first entry in the returned Bundle (`entry[0].resource.id`).
3. **Construct the Observation POST** using that ID:
   ```json
   {
     "resourceType": "Observation",
     "category": [{"coding":[{"system":"http://hl7.org/fhir/observation-category","code":"vital-signs","display":"Vital Signs"}]}],
     "code": {"text": "{flowsheet_id}"},
     "effectiveDateTime": "{current_time}",
     "status": "final",
     "valueString": "{measurement_value}",
     "subject": {"reference": "Patient/{patient_id}"}
   }
   ```
   - **CORRECT**: `subject.reference` uses the extracted `{patient_id}`.
   - **WRONG**: `subject.reference` uses the MRN directly or is omitted.

**Pattern 2: Fallback verification**
- After the GET, verify that the Bundle `total` is `1`. If `0`, abort and return an error message (e.g., "Patient not found").
- If multiple entries are returned, pick the first and log a warning.

**Pattern 3: Formatting rule**
- Ensure the Observation `category` coding uses the exact system `http://hl7.org/fhir/observation-category` and code `vital-signs`.
- Keep `valueString` as a plain string (e.g., `"118/77 mmHg"`). Do not split into separate systolic/diastolic fields unless the API explicitly requires them.

## Example Application
**Task:** "I just measured the blood pressure for patient with MRN of S6352985, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S6352985`
2. Parse response, extract `patient_id = "6352985"` (or whatever the internal ID is).
3. `POST http://localhost:8080/fhir/Observation` with body:
   ```json
   {
     "resourceType": "Observation",
     "category": [{"coding":[{"system":"http://hl7.org/fhir/observation-category","code":"vital-signs","display":"Vital Signs"}]}],
     "code": {"text": "BP"},
     "effectiveDateTime": "2023-11-13T10:15:00+00:00",
     "status": "final",
     "valueString": "118/77 mmHg",
     "subject": {"reference": "Patient/6352985"}
   }
   ```
4. `FINISH([])` after successful POST.

**CORRECT output:** The agent first issues the GET, then the POST as shown.
**WRONG output:** Skipping step 1 or using `subject.reference = "Patient/S6352985"` without extracting the internal ID.

## Success Indicators
- A `GET /Patient` request appears in the action log **before** any `POST /Observation` for the same task.
- The Observation POST body contains `subject.reference` that matches the ID extracted from the GET response.
- The POST is accepted (no error response) and the agent calls `FINISH`.

## Failure Indicators
- The agent posts an Observation without a preceding Patient GET.
- `subject.reference` contains the MRN string or is missing.
- The agent returns an empty list or a combined value/date string instead of performing the required GET‑POST sequence.
