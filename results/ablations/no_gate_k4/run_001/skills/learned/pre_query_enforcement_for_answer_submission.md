---
description: Force a GET request before any FINISH when task needs FHIR data
name: pre_query_enforcement_for_answer_submission
provenance:
  action: ADD
  epoch: 1
  no_gate: true
  triggering_sample_ids:
  - task9_22
  - task9_1
  - task2_1
  - task9_5
  - task1_20
  - task9_9
  - task10_10
  - task5_3
  - task1_10
  - task9_8
  update_cycle: 1
tags:
- behavior
- api
- validation
version: 1
---

# Pre‑Query Enforcement for Answer Submission

## Pattern Description
You must never submit a final answer (`FINISH`) for a task that requires information from the FHIR server until you have actually retrieved that information. This skill watches the current turn for a pending `FINISH` and checks whether the task description mentions a FHIR resource (e.g., Patient, Observation, MedicationRequest). If no corresponding `GET` request has been issued earlier in the same turn, you must pause the answer, issue the required `GET`, wait for the response, then compute and return the answer.

## When to Use This Skill
- When the user asks for a value that lives in a FHIR resource (age, lab result, medication, etc.).
- When the task description contains keywords like `Patient`, `Observation`, `Medication`, `ServiceRequest`, `Condition`, `Encounter`.
- Immediately before you would call `FINISH`.

## Common Failure Patterns
- `FINISH([80])` is emitted right after reasoning without a preceding `GET http://.../Patient?...`.
- The agent includes a reasoning comment that a GET is needed but never actually performs it.
- The agent issues `FINISH` with a placeholder (`-1`, empty list) because no data was fetched.

## Recommended Patterns
**Pattern 1: Verify required GET before FINISH**
1. Parse the task description and identify the primary FHIR resource needed.
2. Scan the action list of the current turn for a `GET` whose URL contains that resource type.
3. If a matching `GET` is **not** found, **do not** emit `FINISH`.
4. Issue the appropriate `GET` request (e.g., `GET http://localhost:8080/fhir/Patient?identifier=MRN`).
5. Wait for the user to supply the response bundle.
6. Extract the needed field (e.g., `entry[0].resource.birthDate`).
7. Compute the answer and finally call `FINISH` with the correct payload.

**Pattern 2: Fallback when GET fails**
- If the GET returns a bundle with `total = 0`, use the appropriate placeholder skill (e.g., `missing_observation_placeholder`) and then `FINISH`.

**Pattern 3: Formatting the final output**
- Always return a scalar or array exactly as the task expects (e.g., `FINISH([80])` for age, `FINISH([5.4, "2023-11-02T06:53:00+00:00"])` for lab value + timestamp).

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step‑by‑step:**
1. Detect that the task needs a `Patient` resource.
2. No `GET` for `Patient` has been issued yet → **do not** `FINISH`.
3. Issue `GET http://localhost:8080/fhir/Patient?identifier=S2703270`.
4. Receive the bundle, extract `birthDate`.
5. Compute age using `accurate_age_calculation`.
6. Emit `FINISH([80])`.

**Correct output:** `FINISH([80])`
**Incorrect output:** `FINISH([80])` *without* the preceding GET request.

## Success Indicators
- A `GET` request for the identified resource appears before any `FINISH`.
- The final `FINISH` payload matches the format required by the task.
- No `FINISH` is emitted when the required GET is missing.

## Failure Indicators
- `FINISH` appears as the first action for a data‑driven task.
- The agent mentions needing a GET in its reasoning but never sends it.
- The answer is based on a placeholder despite the resource being available.
