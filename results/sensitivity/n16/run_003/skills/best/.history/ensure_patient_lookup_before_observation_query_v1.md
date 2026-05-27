---
description: Guarantee a Patient lookup and use the resolved patient ID when querying
  Observations
name: ensure_patient_lookup_before_observation_query
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task4_21
  - task3_19
  - task10_17
  - task9_28
  - task10_13
  - task9_20
  - task8_9
  - task10_20
  - task10_27
  - task9_14
  update_cycle: 0
tags:
- observation
- patient_lookup
- reference_resolution
version: 1
---

# ensure_patient_lookup_before_observation_query

## Pattern Description
You must always resolve a patient’s logical FHIR ID before any Observation search that is keyed to a patient.  The identifier (e.g., MRN) used in the task may not match the resource’s `id` field, so querying `Observation?patient={identifier}` can miss results or return empty bundles.  By first performing a `GET /Patient?identifier=...`, extracting the patient’s `id`, and then using `patient=Patient/{id}` (or just `{id}`) in the Observation request, you ensure the query is scoped to the correct resource.

## When to Use This Skill
- When a task asks for the latest value of a lab or vital sign for a patient identified by MRN, identifier, or any external key.
- When constructing an `Observation` search that includes the `patient` search parameter.
- When the task may later need to reference the patient in a ServiceRequest or other resource.

## Common Failure Patterns
- Using the raw identifier in the Observation query: `GET .../Observation?code=A1C&patient=S123456` – the server treats `patient` as a reference, not an identifier, and may return no results.
- Skipping the Patient lookup entirely and assuming the identifier equals the resource ID.
- Extracting the patient ID from the wrong field (e.g., `fullUrl` instead of `resource.id`).

## Recommended Patterns
**Pattern 1: Resolve patient ID first**
1. Issue `GET {base}/Patient?identifier={identifier}`.
2. Verify the bundle `total` is 1; if 0, abort with “Patient not found”.
3. Extract the patient logical ID: `patient_id = bundle.entry[0].resource.id`.
4. Build the Observation query using the reference form: `GET {base}/Observation?code={code}&patient=Patient/{patient_id}` (or `patient={patient_id}` if the server accepts plain IDs).

**Pattern 2: Fallback if patient lookup fails**
- Return a clear error message or `FINISH(["Patient not found"])` instead of proceeding to an Observation request.

**Pattern 3: Consistent reference usage for downstream resources**
- When creating a `ServiceRequest` or other resource that references the patient, use the same `Patient/{patient_id}` reference.

## Example Application
**Task:** "What’s the last HbA1C value for patient S2823623 and when was it recorded? If older than 1 year, order a new test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2823623`
2. Response bundle contains `entry[0].resource.id = "S2823623"` (or another internal ID).
3. Construct Observation query: `GET http://localhost:8080/fhir/Observation?code=A1C&patient=Patient/S2823623`
4. Extract `valueQuantity.value` and `effectiveDateTime` from the first entry.
5. If the date is >1 year old, POST a `ServiceRequest` referencing `Patient/S2823623`.
6. `FINISH([value, date])` or `FINISH(["order placed"])` as appropriate.

**Correct output example:**
```json
FINISH([5.2, "2022-09-15T08:30:00+00:00"])
```
**Wrong output example (missing lookup):**
```json
FINISH(["5.2 %","2022-09-15T08:30:00+00:00"])
```

## Success Indicators
- The agent always performs a Patient GET before any Observation GET that includes a `patient` parameter.
- Observation queries use `patient=Patient/{id}` (or plain `{id}`) rather than the raw identifier.
- When the patient cannot be found, the agent aborts with a clear “Patient not found” response.

## Failure Indicators
- Observation GET is issued with `patient={identifier}` without a prior Patient lookup.
- The agent proceeds to extract values from an empty Observation bundle because the patient reference was incorrect.
- A ServiceRequest is created referencing the raw identifier instead of the resolved patient ID.
