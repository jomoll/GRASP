---
description: "Require a GET request for any patient\u2011specific query before producing\
  \ a FINISH answer."
name: enforce_fhir_get_before_answer
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 0
  fixes_unused: 5
  probe_score_unused: 4
  regressions_unused: 1
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  - task9_27
  update_cycle: 0
tags: []
version: 1
---

# Enforce FHIR GET Before Answer

## Pattern Description
You must never answer a question that depends on patient‑specific data (e.g., age, lab values, vital signs) without first retrieving that data from the FHIR server. The agent’s workflow should always start with a precise `GET` request, wait for the response, extract the required field, and only then construct the final `FINISH` output. This prevents the "no_fhir_action_performed" failure mode where the agent replies with reasoning but never issues the needed API call.

## When to Use This Skill
- When the task asks for a patient’s age, most recent lab result, or any observation value.
- When the instruction includes conditional logic based on a lab value (e.g., "If potassium is low, order replacement").
- When the task references a patient identifier (MRN, identifier) and expects a value derived from the FHIR record.

## Common Failure Patterns
- Agent returns reasoning text without any preceding `GET` request.
- Agent attempts to compute a value from memory instead of querying the server.
- Agent issues a `FINISH` directly, skipping the required data retrieval step.

## Recommended Patterns
**Pattern 1: Identify required FHIR resource and construct GET URL**
1. Parse the instruction to determine the needed resource (Patient, Observation, Condition, etc.).
2. Build the exact query string using the provided identifiers and codes.
   - Example for age: `GET {api_base}/Patient?identifier={MRN}`
   - Example for potassium: `GET {api_base}/Observation?code=K&patient={MRN}&date=ge{now-24h}`
3. Issue the `GET` request as the first action.

**Pattern 2: Wait for and validate the GET response**
1. Ensure the response is a `Bundle` with `total >= 1`.
2. Extract the relevant field:
   - Age: `entry[0].resource.birthDate` → compute years difference to current time.
   - Observation value: `entry[0].resource.valueQuantity.value` (numeric) and `unit` if needed.
3. If the bundle is empty, follow the task’s "no data" branch (e.g., do not order medication).

**Pattern 3: Conditional ordering or answer construction**
1. Apply any thresholds or conditional logic after extraction.
2. If an order is required, construct the appropriate `POST` (e.g., `MedicationRequest` or `ServiceRequest`).
3. Finally, issue `FINISH` with the exact expected format (array of strings, not full sentences).

## Example Application
**Task:** "What's the age of the patient with MRN of S1152319?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S1152319`
2. Receive response, extract `birthDate` (e.g., `1970-04-15`).
3. Compute age: floor((2023‑11‑13 – 1970‑04‑15) / 365.25) = 53.
4. `FINISH(["53"])`

**Correct output:** `FINISH(["53"])`
**Wrong output:** `FINISH(["The patient is 53 years old."])`

## Success Indicators
- The first action in the agent’s trace is a `GET` request matching the needed resource.
- The `FINISH` payload contains only the raw value(s) in the required array format.
- Conditional orders are only posted after the GET response is examined.

## Failure Indicators
- The agent emits reasoning or a final answer without any preceding `GET`.
- The `FINISH` output includes explanatory text or combines multiple values into one string.
- The agent posts an order without confirming the lab value from a GET response.
