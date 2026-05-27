---
description: Guarantee a Patient GET before any Observation query for recent lab values
name: ensure_patient_lookup_before_observation_query
provenance:
  action: MODIFY
  epoch: 4
  fixes: 5
  parent_version: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task4_28
  - task4_21
  - task9_5
  - task4_10
  - task4_26
  - task10_10
  - task8_23
  - task10_21
  - task4_7
  - task9_3
  update_cycle: 0
tags: []
version: 3
---

# ensure_patient_lookup_before_observation_query

## Pattern Description
You must always retrieve the patient resource **before** you query any Observation that is tied to a specific patient. This pattern applies to any task that asks for the most recent value of a lab, vital, or other observation (e.g., magnesium, potassium, HbA1c) within a time window. The agent should treat the patient lookup as a mandatory first step, not merely a planning note.

## When to Use This Skill
- The instruction contains a request for a lab/observation value **and** references a patient identifier (MRN, identifier, or name).
- The request specifies a time constraint (e.g., "within last 24 hours", "most recent", "last result").
- The observation code is mentioned explicitly (e.g., `MG`, `K`, `A1C`) or implied by a lab name.
- The task expects a numeric result or a decision based on that result.

## Common Failure Patterns
- The agent describes the need for a patient lookup but never emits a `GET /Patient?...` API call.
- The agent proceeds directly to `GET /Observation?...` without a patient reference, causing the server to reject the request or return no data.
- The agent includes the patient identifier in the Observation URL **without** first confirming the patient exists (e.g., using a hard‑coded MRN).

## Recommended Patterns
**Pattern 1: Mandatory patient lookup**
1. Detect that the task requires an observation value for a specific patient.
2. Issue **exactly one** `GET` request to retrieve the patient resource:
   ```
   GET http://localhost:8080/fhir/Patient?identifier={MRN}
   ```
3. Parse the response to obtain the patient’s logical ID (`Patient/{id}`).
4. Use that ID in the subsequent Observation query.

**Pattern 2: Observation query with date filter**
1. Compute the start of the window (e.g., `now - 24h`).
2. Issue the Observation request **only after** the patient GET succeeded:
   ```
   GET http://localhost:8080/fhir/Observation?code={CODE}&patient=Patient/{id}&date=ge{START}&date=le{NOW}
   ```
3. If the Observation bundle is empty, return `-1` (or the task‑specific "no result" message).

**Pattern 3: Verification before proceeding**
- If the patient GET returns `total = 0`, abort the task and return an appropriate error (e.g., "Patient not found").
- If the Observation GET fails or returns an error, surface the error instead of fabricating a value.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S0674240`
2. Extract the patient ID, e.g., `Patient/S0674240`.
3. Compute `START = 2023-11-12T10:15:00+00:00` (now minus 24 h).
4. `GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S0674240&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`
5. If a bundle entry exists, pull `valueQuantity.value` (convert to mg/dL if needed) and `effectiveDateTime`.
6. `FINISH([value])` or `FINISH([-1])` if no entry.

**Correct output:** `FINISH([1.8])`
**Incorrect output:** `FINISH(["Magnesium is 1.8 mg/dL"])`

## Success Indicators
- The first API call in the trace is a `GET /Patient?...` matching the MRN from the instruction.
- The patient ID is used verbatim in the subsequent Observation request.
- No Observation request appears before the patient request.
- The final `FINISH` contains only the numeric value (or `-1`).

## Failure Indicators
- The agent emits an Observation request without a preceding Patient GET.
- The Observation URL contains a hard‑coded MRN instead of `Patient/{id}`.
- The `FINISH` payload includes free‑text or extra formatting.
- The agent proceeds to ordering or other actions before confirming the observation result.
