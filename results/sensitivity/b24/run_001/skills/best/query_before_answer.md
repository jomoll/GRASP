---
description: Enforce issuing a GET request for required FHIR data before any FINISH
  output.
name: query_before_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 8
  probe_score: 10
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  - task9_27
  - task4_20
  update_cycle: 0
tags: []
version: 1
---

# Query Before Answer Enforcement

## Pattern Description
You must never answer a clinical question that depends on patient‑specific data without first retrieving that data from the FHIR server. The agent should always construct a precise GET request for the needed resource (Patient, Observation, Condition, etc.), wait for the response, extract the required fields, and only then produce a FINISH output. This prevents guesses, placeholder values, and answers that bypass the data source.

## When to Use This Skill
- Any task that asks for a patient attribute (age, MRN, gender, etc.).
- Any task that requests the latest lab or vital sign value (e.g., potassium, magnesium, HbA1c).
- Any task that requires checking a condition, medication, or service request before acting.
- When the instruction includes identifiers (MRN, patient ID) or codes (e.g., `code=K` for potassium).

## Common Failure Patterns
- Directly calling `FINISH([...])` with a value without a preceding GET request.
- Returning a placeholder string such as "[value]" or "N/A" when data was not fetched.
- Using hard‑coded values or assumptions instead of querying the server.
- Omitting required query parameters (e.g., missing `patient=` or `code=`).

## Recommended Patterns
**Pattern 1: Identify and issue the required GET request**
1. Parse the task to determine which FHIR resource and search parameters are needed.
2. Construct the exact GET URL using the base URL `http://localhost:8080/fhir/`.
3. Include all mandatory query parameters (e.g., `patient=S12345`, `code=K`, `date=ge2023-11-12T10:15:00Z`).
4. Emit the GET request as the next action.

**Pattern 2: Wait for and process the GET response**
1. When the user supplies the response bundle, locate the first entry (most recent) if ordering is required.
2. Extract the precise field:
   - For age: `birthDate` → compute years difference from current time.
   - For lab value: `valueQuantity.value` (numeric) and optionally `valueQuantity.unit`.
   - For MRN: `identifier.value` where `type.coding.code` matches "MR".
3. Validate that the extracted value is of the expected type (integer, decimal, string).

**Pattern 3: Produce the final answer**
1. Use the extracted value to build the FINISH payload.
2. Do **not** include any raw JSON or extra commentary.
3. Example correct format: `FINISH([3.5])` for a numeric lab value, or `FINISH([27])` for age.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step‑by‑step:**
1. Identify needed resource: `Patient` with `identifier=S2703270`.
2. Issue GET: `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
3. Receive Bundle, extract `birthDate` (e.g., `1990-04-15`).
4. Compute age using current time `2023-11-13T10:15:00+00:00` → `33`.
5. Output: `FINISH([33])`

**Correct output:** `FINISH([33])`
**Wrong output:** `FINISH(["33 years"] )` or answering without the GET request.

## Success Indicators
- A GET request appears **before** any FINISH action for data‑dependent tasks.
- Extracted values are numeric when required and match the type expected by the task.
- The FINISH payload contains only the clean value (or list of values) without extra text.

## Failure Indicators
- FINISH is emitted without a preceding GET request.
- The answer includes placeholder text like "[value]" or explanatory sentences.
- The GET URL is missing required parameters or uses the wrong resource.
- The extracted value is of the wrong type (e.g., string instead of integer).
