---
description: Ensures a GET request is performed to fetch required FHIR data before
  answering or taking action.
name: require_fhir_query_before_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 15
  probe_score: 17
  regressions: 1
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task9_14
  - task9_27
  - task1_12
  update_cycle: 0
tags: []
version: 1
---

# Require FHIR Query Before Answering Clinical Question

## Pattern Description
You must never answer a clinical question or create a resource without first retrieving the necessary data from the FHIR server. This pattern forces a deterministic data‑driven flow: identify the needed resource, issue a GET request with the correct search parameters, validate that the response contains the required fields, and only then construct the answer, make a decision, or issue a POST/PUT. By enforcing this step you avoid placeholder values (e.g., `-1`), incorrect formats, and actions taken on stale or missing data.

## When to Use This Skill
- When a task asks for a patient attribute (age, MRN, gender) or a clinical measurement (lab value, vital sign).
- When a task requires a decision based on the latest Observation (e.g., order a medication if a lab is abnormal).
- When creating a new Observation, ServiceRequest, or MedicationRequest that references a patient or other resource.
- Whenever the instruction includes a specific identifier (MRN, code, date range) that must be resolved via FHIR.

## Common Failure Patterns
- Directly calling `FINISH` with a placeholder (`-1`) without a preceding GET.
- Using hard‑coded values or assumptions instead of querying the server.
- Returning a string or formatted sentence when a numeric answer is required because the data was never fetched.
- Issuing a POST/ServiceRequest based on a condition that was never verified via a GET.

## Recommended Patterns
**Pattern 1: Identify and fetch required data**
1. Parse the instruction to determine the needed FHIR resource and search parameters (e.g., `Patient?identifier=S12345`, `Observation?code=MG&patient=S12345&date=ge2023-11-12T10:15:00Z`).
2. Issue a `GET` request to the exact endpoint.
3. Verify the response `Bundle.total > 0`. If `0`, handle the "not found" case as instructed.
4. Extract the exact field needed (e.g., `entry[0].resource.birthDate`, `entry[0].resource.valueQuantity.value`).

**Pattern 2: Decision making after data retrieval**
1. Apply any business logic (e.g., compare dates, thresholds) **only after** the GET succeeded.
2. If the logic dictates an action, construct the appropriate POST body using the IDs obtained from the GET response.
3. If the logic dictates no action, call `FINISH` with the prescribed explanatory text.

**Pattern 3: Formatting the final answer**
- Return raw values in the required type (number, string, array) without extra wording.
- Example correct vs. wrong:
  - CORRECT: `FINISH([3.5])` for a numeric lab value.
  - WRONG: `FINISH(["HbA1c is 3.5%, within range."])`.

## Example Application
**Task:** "What’s the age of the patient with MRN of S2863714?"

**Step‑by‑step:**
1. Identify needed resource: `Patient?identifier=S2863714`.
2. GET `http://localhost:8080/fhir/Patient?identifier=S2863714`.
3. Parse `entry[0].resource.birthDate` (e.g., `1970-04-22`).
4. Compute age from current time (`2023-11-13`).
5. Return numeric age: `FINISH([53])`.

**Correct output:** `FINISH([53])`
**Incorrect output (missing GET):** `FINISH(["53 years old"])` or `FINISH([-1])`.

## Success Indicators
- A `GET` request appears in the action list before any `FINISH` or `POST`.
- The `GET` response is inspected and the required field is extracted.
- The final output matches the type required by the instruction (number, array, or specific string).

## Failure Indicators
- `FINISH` is called without a preceding `GET` for the same resource.
- The agent returns placeholder `-1` or a formatted sentence when a raw value was expected.
- A POST/ServiceRequest is issued without confirming the condition via a prior GET.
