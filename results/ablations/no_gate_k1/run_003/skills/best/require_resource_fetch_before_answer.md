---
description: Force a GET request for any needed FHIR resource before answering or
  posting.
name: require_resource_fetch_before_answer
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task4_7
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task3_10
  - task2_14
  - task5_23
  update_cycle: 1
tags:
- resource_fetch
- precondition
- clinical_decision
version: 1
---

# Require Resource Fetch Before Answer

## Pattern Description
You must never answer a clinical question or create a new FHIR resource without first retrieving the data you need from the server.  For any task that references a patient attribute, lab value, vital sign, or other observable, the first operational step is a **GET** request that fetches the exact resource (Patient, Observation, Condition, etc.) using the identifiers supplied in the instruction.  Only after the GET response is received may you extract fields, make decisions, or issue a POST/PUT.

## When to Use This Skill
- When the instruction says *"Check patient Sxxxx's most recent potassium level"* or *"What’s the age of the patient with MRN of Sxxxx?"*.
- When the instruction asks to *"If low, order replacement …"* – you need the lab value first.
- When the instruction requires a value that is not already known to the agent (e.g., a lab, vital sign, medication, or demographic).
- Any time the agent is about to call `FINISH` or `POST` without a preceding `GET` that targets the required resource.

## Common Failure Patterns
- Direct `FINISH([...])` with a computed answer while no prior `GET Observation?...` or `GET Patient?...` appears.
- `POST MedicationRequest` or `ServiceRequest` based on a lab value that was never retrieved.
- Answer contains placeholder text like `"[value]"` because the value was never fetched.
- The agent includes explanatory comments in the final answer instead of the pure result.

## Recommended Patterns
**Pattern 1: Identify needed resource**
1. Parse the instruction and list required data elements (e.g., patient identifier, observation code, date range).
2. Construct the exact FHIR query string using the API base URL.
   - For a patient lookup: `GET {api_base}/Patient?identifier={MRN}` or `GET {api_base}/Patient?family={last}&given={first}&birthdate={DOB}`.
   - For an observation: `GET {api_base}/Observation?code={CODE}&patient={MRN}` optionally with `date=ge{start}&date=le{end}` for time windows.
3. **Issue the GET request as the very next action.**

**Pattern 2: Wait for and validate the response**
- Ensure the response contains a `Bundle` with at least one `entry`.
- If `total == 0` (no matching resource), handle the "not found" case according to the instruction (e.g., do not order medication, return `-1`, or output "Patient not found").

**Pattern 3: Extract and act**
- After the GET response, extract the exact field needed:
  - Age: `entry[0].resource.birthDate` → compute years.
  - Lab value: `entry[0].resource.valueQuantity.value` (numeric) and optionally `unit`.
  - Vital sign string: `entry[0].resource.valueString`.
- Apply any thresholds or dosing logic.
- Only now may you issue a `POST` (MedicationRequest, ServiceRequest, Observation) **or** call `FINISH` with the final answer.

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium …"

**Step‑by‑step:**
1. Identify needed data: Observation with code `K` for patient `S3241217`.
2. Action: `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
3. Receive response, locate the most recent entry, read `valueQuantity.value`.
4. If the value < low‑threshold, construct a `POST` for the replacement potassium using the provided NDC.
5. Also `POST` a follow‑up Observation request for a morning serum potassium.
6. Finally `FINISH` with a concise success message.

**Correct output sequence:**
```
GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217
... (response received) ...
POST http://localhost:8080/fhir/MedicationRequest { ... }
POST http://localhost:8080/fhir/ServiceRequest { ... }
FINISH(["Potassium replacement ordered and follow‑up test scheduled."])
```

## Success Indicators
- The first action after receiving the instruction is a `GET` that matches the needed resource type and parameters.
- No `FINISH` or `POST` appears before the corresponding `GET`.
- The final answer uses data extracted from the GET response (numeric value, age, etc.).

## Failure Indicators
- `FINISH` or `POST` occurs without any preceding `GET` for the required resource.
- The answer contains placeholder text or comments instead of concrete values.
- The agent assumes a value (e.g., low potassium) without evidence from a GET response.
