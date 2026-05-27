---
description: Resolve external patient identifiers to the actual Patient id before
  Observation/Procedure/MedicationRequest queries.
name: resolve_patient_identifier_before_dependent_search
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task1_15
  - task3_17
  - task4_11
  - task3_19
  - task3_10
  - task8_5
  - task1_20
  - task9_9
  - task8_29
  - task4_23
  update_cycle: 0
tags:
- fhir
- patient-resolution
- search
- observation
- procedure
- medicationrequest
version: 1
---

# Patient Identifier Resolution Before Dependent Searches

## Pattern Description

When a task names a patient by an external identifier such as `S6268253`, you must not assume that string is always the correct `patient` search value for every downstream FHIR resource query. First resolve the patient with `GET /Patient?identifier=...`, then extract the actual Patient resource id/reference and use that resolved value consistently in subsequent searches and POST bodies.

This skill changes behavior in tasks that otherwise return false empty results. The common failure is querying `Observation`, `Procedure`, or `MedicationRequest` with the raw external identifier, seeing `total: 0`, and concluding that no data exists even though the data may be linked to the resolved Patient resource id or reference.

## When to Use This Skill

- When the instruction identifies a patient by an MRN-like or external identifier such as `S6500497`
- When you are about to query a patient-linked resource such as `Observation`, `Procedure`, `MedicationRequest`, or `ServiceRequest`
- When you have already called `GET /Patient?identifier=...` and need to issue follow-up searches
- When a dependent search like `GET /Observation?...&patient=S6268253` returns `total: 0` or empty `entry`, especially if the task strongly expects data to exist
- When constructing a POST body with `subject.reference` and the patient was given as an identifier rather than an explicit FHIR reference

## Common Failure Patterns

- Using the raw task identifier directly in dependent searches: `Observation?patient=S6268253` without first checking the Patient lookup result
- Ignoring `entry[0].resource.id` or `entry[0].fullUrl` from `Patient?identifier=...`
- Mixing identifier styles across steps, such as resolving the patient but still querying downstream resources with the unresolved identifier
- Concluding "no observations available" after an empty dependent search without verifying whether the patient parameter should instead use the resolved Patient id/reference
- Building POST bodies with a guessed `subject.reference` before confirming the Patient resource identity
- Sending malformed combined tool calls like `GET /Patient?...GET /Observation?...` instead of waiting for the Patient response before issuing the next request

## Recommended Patterns

**Pattern 1: resolve first, then search**
1. Start with `GET /Patient?identifier={task_patient_identifier}`.
2. Confirm the Bundle has `total >= 1` and inspect `entry[0].resource.id`.
3. Form the patient reference you will use downstream:
   - preferred reference form: `Patient/{entry[0].resource.id}`
   - if needed, also note the bare id: `{entry[0].resource.id}`
4. Use the resolved value in every subsequent patient-linked query and in any `subject.reference` for POST.

CORRECT: `subject.reference = "Patient/8a8f0f33-bb8c-4d73-a2f0-b080f5f6f996"`
WRONG:   `subject.reference = "Patient/S6268253"` without checking the Patient resource

**Pattern 2: retry on empty dependent results with the alternate patient form**
1. After resolving the patient, issue the dependent search with one patient form.
2. If the search returns `total: 0`, retry once with the alternate resolved form before concluding absence:
   - try bare id: `patient={resource.id}`
   - or try reference form: `patient=Patient/{resource.id}`
3. Only after both resolved forms fail should you conclude that no matching data was found.
4. Do not treat the raw external identifier as equivalent to the resolved Patient id unless the API evidence shows it works.

**Pattern 3: keep output and POST bodies aligned with the resolved patient**
1. Use the same resolved patient identity in all follow-up requests within the task.
2. For POST resources, set `subject.reference` to the resolved Patient reference.
3. In the final answer, report findings for the task’s patient identifier, but base the search on the resolved Patient resource.

CORRECT: search with resolved patient id/reference, then `FINISH(["Most recent TSH: 2.22 uIU/mL on 2022-09-30"])`
WRONG:   return `"no results"` immediately after `Observation?patient=S6500497` returned empty without trying the resolved Patient id/reference

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6268253."

**Step-by-step:**

1. Issue patient lookup first: `GET /Patient?identifier=S6268253`
2. Extract `entry[0].resource.id` from the Bundle, for example `8a8f0f33-bb8c-4d73-a2f0-b080f5f6f996`.
3. Query heart rate Observations using the resolved patient value, e.g. `GET /Observation?code=HEARTRATE&patient=8a8f0f33-bb8c-4d73-a2f0-b080f5f6f996&date=ge2023-11-07T10:47:00Z`
4. If that returns empty, retry once with `patient=Patient/8a8f0f33-bb8c-4d73-a2f0-b080f5f6f996`.
5. Only then compute the 6-hour and 12-hour averages from returned `Observation` entries, or conclude that no heart rate observations were found.

CORRECT output: `FINISH(["Average heart rate over past 6 hours: 84.5 bpm", "Average heart rate over past 12 hours: 81.0 bpm"])`
WRONG output:   `FINISH(["Average heart rate over past 6 hours: no heart rate observations available", "Average heart rate over past 12 hours: no heart rate observations available"])` immediately after querying with `patient=S6268253`

## Success Indicators

- You always call `GET /Patient?identifier=...` before patient-linked resource searches when the task gives an external identifier.
- Your later GETs use a patient value derived from `entry[0].resource.id` or `Patient/{id}`.
- You retry an empty dependent search with the alternate resolved patient form before concluding absence.
- Your POST bodies use a resolved `subject.reference` rather than a guessed identifier-based reference.

## Failure Indicators

- You query `Observation`, `Procedure`, or `MedicationRequest` with the raw external identifier and stop after `total: 0`.
- You ignore the Patient lookup response entirely or perform it but never use its result.
- Your follow-up searches use inconsistent patient values across steps.
- You claim "no data found" without ever trying a resolved Patient id/reference.
- You concatenate multiple GETs into one malformed request instead of sequencing patient resolution before dependent searches.
