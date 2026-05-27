---
description: "Guarantee a GET Patient lookup (by MRN) and required Observation GET/POST\
  \ before finishing any vital\u2011sign or lab\u2011check task."
name: ensure_fhir_call_for_patient_and_observation
provenance:
  action: ADD
  epoch: 0
  fixes: 7
  probe_score: 7
  regressions: 2
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task2_16
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  - task2_9
  update_cycle: 0
tags: []
version: 1
---

# Ensure FHIR Call for Patient Lookup and Observation

## Pattern Description
You must always retrieve the patient resource before attempting to read or write any clinical data. For tasks that involve recording a vital sign (e.g., blood pressure) or checking a recent lab value (e.g., magnesium, potassium), the first step is a **GET** request to `/Patient?identifier=<MRN>`. Only after a successful patient reference is obtained should you issue the subsequent GET (for a lab lookup) or POST (to create an Observation). This pattern prevents the agent from finishing a task without any FHIR interaction, which is the most common failure in the current batch.

## When to Use This Skill
- When the instruction mentions a **MRN** (or other patient identifier) and asks to *record*, *check*, or *report* a measurement.
- When the task requires a **vital‑sign Observation** (e.g., blood pressure, heart rate) to be created.
- When the task asks for the **most recent lab value** within a time window (e.g., magnesium, potassium, HbA1c).
- When the instruction includes a **flowsheet ID** or a **code** that maps to a FHIR Observation.

## Common Failure Patterns
- No GET request to `/Patient` before using a patient reference.
- Directly issuing a POST Observation with a hard‑coded patient ID.
- Skipping the GET Observation step for a lab‑value lookup.
- Returning a plain answer without any preceding FHIR call.

## Recommended Patterns
**Pattern 1: Patient lookup**
1. Extract the MRN from the instruction (e.g., `S2703270`).
2. Issue `GET {api_base}/Patient?identifier=<MRN>`.
3. Verify the response contains exactly one entry; use `entry[0].resource.id` as the patient reference.

**Pattern 2: Lab value retrieval (optional date filter)**
1. Identify the lab code (`code` parameter) from the task description (e.g., `MG` for magnesium).
2. If a time window is specified, construct a date filter: `date=ge<ISO‑8601 start>` where start = current_time - window.
3. Issue `GET {api_base}/Observation?code=<code>&patient=<MRN>&date=<filter>`.
4. If `total == 0`, treat as “no recent measurement”.
5. If results exist, sort by `effectiveDateTime` descending and extract `valueQuantity.value` (or `valueString` when appropriate).

**Pattern 3: Observation creation for vital signs**
1. After successful patient lookup, build a POST body:
```json
{
  "resourceType": "Observation",
  "category": [{"coding": [{"system": "http://hl7.org/fhir/observation-category","code": "vital-signs","display": "Vital Signs"}]}],
  "code": {"text": "<flowsheet ID>"},
  "effectiveDateTime": "<current_time>",
  "status": "final",
  "valueString": "<measurement>",
  "subject": {"reference": "Patient/<MRN>"}
}
```
2. POST to `{api_base}/Observation`.
3. Verify the POST succeeded before calling `FINISH`.

**Pattern 4: Decision logic after lab lookup**
1. If a recent value is found, compare against the clinical threshold defined in the task.
2. If the value is low, issue the appropriate medication/service request (e.g., POST `MedicationRequest` or `ServiceRequest`).
3. If no value or value is normal, finish with an explanatory message and **do not** create any order.

## Example Application
**Task:** "I just measured the blood pressure for patient with MRN of S2703270, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. Extract MRN `S2703270` and measurement `118/77 mmHg`.
2. `GET http://localhost:8080/fhir/Patient?identifier=S2703270`.
3. Use the returned patient reference `Patient/S2703270`.
4. Build POST body as shown in Pattern 3 (flowsheet ID = `BP`).
5. `POST http://localhost:8080/fhir/Observation` with the body.
6. On success, `FINISH(["Blood pressure recorded successfully"])`.

**Correct output:** `FINISH(["Blood pressure recorded successfully"])`
**Wrong output:** `FINISH(["118/77 mmHg recorded."])` (no FHIR call made).

## Success Indicators
- The agent issues a `GET /Patient` request before any other action.
- For lab checks, a `GET /Observation` request appears with the correct `code` and optional `date` filter.
- For vital‑sign recordings, a `POST /Observation` follows the patient GET.
- The final `FINISH` is called only after the required FHIR call(s) succeed.

## Failure Indicators
- The agent calls `FINISH` without any preceding GET/POST.
- The patient GET is omitted or uses an incorrect query parameter (e.g., `id=` instead of `identifier=`).
- The Observation POST uses a hard‑coded patient reference that was not verified.
- The lab GET lacks the `code` parameter or uses the wrong date filter syntax.
