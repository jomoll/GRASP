---
description: Force a GET request for needed FHIR resources before any FINISH or POST
  action
name: require_fhir_query_before_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 21
  probe_score: 18
  regressions: 2
  triggering_sample_ids:
  - task8_26
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task4_28
  - task4_7
  - task8_5
  - task10_8
  update_cycle: 0
tags:
- query
- validation
- precondition
version: 1
---

# Require FHIR Query Before Answer

## Pattern Description
You must never answer a clinical question or create a new FHIR resource without first retrieving the relevant source data from the FHIR server. The agent should treat every task as a two‑step workflow: (1) locate the required resource(s) with a precise GET request, and (2) use the returned data to compute the answer, build a POST body, or decide that no action is needed. This prevents placeholder answers, missing context, and unsafe orders.

## When to Use This Skill
- When the instruction references a patient by MRN, name, or other identifier and asks for a value (age, lab result, etc.).
- When the instruction asks to record a measurement, place an order, or make a decision that depends on existing observations.
- When the task mentions a specific FHIR resource type (Patient, Observation, Condition, ServiceRequest, etc.) and expects the agent to use data from that resource.
- Any time the agent is about to emit `FINISH` or `POST` without a preceding `GET` that matches the needed resource.

## Common Failure Patterns
- Direct `FINISH([...])` with a computed value but no prior `GET` request.
- `POST` of a ServiceRequest or Observation without first confirming the patient reference via `GET /Patient?identifier=...`.
- Using placeholder strings like "Patient not found" without verifying existence via a query.
- Missing date filters on Observation searches, leading to stale data being used.

## Recommended Patterns
**Pattern 1: Identify required resource and construct GET**
1. Parse the task to extract the resource type and key search parameters (e.g., `identifier=S1234567`, `code=K`, `patient=S1234567`, `date=ge2023-11-12T10:15:00Z`).
2. Issue a GET request with the exact FHIR search syntax:
   - Patient lookup: `GET {api_base}/Patient?identifier={MRN}`
   - Observation lookup: `GET {api_base}/Observation?code={CODE}&patient={MRN}[&date=ge{ISO8601}]`
   - Condition lookup: `GET {api_base}/Condition?patient={MRN}&code={CODE}`
3. Wait for the server response before proceeding.

**Pattern 2: Verify GET result before proceeding**
- If the Bundle `total` is 0, handle the "not found" case explicitly (e.g., `FINISH(["Patient not found"])` or return `-1`).
- If the Bundle contains entries, extract the needed field (`birthDate`, `valueQuantity.value`, `effectiveDateTime`, etc.) using the exact JSON paths.

**Pattern 3: Use retrieved data to build POST or answer**
- For recording a measurement: build the Observation JSON using the patient reference from the GET (`"reference": "Patient/{id}"`).
- For age calculation: compute `age = floor((now - birthDate) / 365.25)`.
- For conditional orders: only POST a ServiceRequest if the observation value meets the threshold; otherwise `FINISH(["No order needed"])`.

**Pattern 4: Formatting the final output**
- Always wrap the answer in a JSON array inside `FINISH([...])`.
- Return plain numbers or strings, never full sentences, unless the task explicitly asks for narrative.

## Example Application
**Task:** "What's the age of the patient with MRN of S0611496?"

**Step‑by‑step:**
1. Identify needed resource: Patient, search by identifier.
2. Issue GET: `GET http://localhost:8080/fhir/Patient?identifier=S0611496`.
3. Receive Bundle, extract `birthDate` from `entry[0].resource.birthDate`.
4. Compute age using the provided current time (2023‑11‑13T10:15:00+00:00).
5. Return answer: `FINISH([45])` (example integer).

**Correct output:** `FINISH([45])`
**Wrong output:** `FINISH(["Patient age is 45 years."])` (wrong format, no GET performed).

## Success Indicators
- Every `FINISH` or `POST` is preceded by a `GET` whose URL matches the resource and parameters required by the task.
- The agent extracts fields from the GET response rather than fabricating values.
- Conditional orders are only created after a successful observation lookup and threshold check.

## Failure Indicators
- `FINISH` appears without any prior `GET` in the action list.
- The GET URL does not include the necessary search parameters (e.g., missing `identifier=` or `code=`).
- The agent returns placeholder text or hard‑coded numbers without evidence from a GET response.
- Observation or ServiceRequest POST bodies contain a patient reference that was never verified via GET.
