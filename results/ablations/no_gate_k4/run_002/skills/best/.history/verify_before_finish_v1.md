---
description: Require parsing of API responses before issuing FINISH to avoid premature
  answers
name: verify_before_finish
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task3_14
  update_cycle: 0
tags:
- verification
- response_parsing
- conditional_logic
version: 1
---

# Verify API Response Before FINISH

## Pattern Description
You must never submit a final answer (FINISH) until you have inspected and extracted the required information from any API response you have just requested. This pattern enforces a verification step that guarantees the data you base your decision on actually exists and is correctly interpreted. It applies to any task where the instruction depends on values retrieved from the FHIR server (e.g., patient age, latest lab result, vital sign) before a decision or order can be made.

## When to Use This Skill
- When a task asks for a value that must be looked up via a GET request (Patient, Observation, Condition, etc.) before you can answer or place an order.
- When you have just issued a GET call and the next logical step is to compute, compare, or conditionally act on the returned data.
- When the instruction includes conditional logic such as "If low, then order..." or "If the patient does not exist, answer 'Patient not found'."

## Common Failure Patterns
- Issuing `FINISH([...])` immediately after a GET without waiting for the response.
- Using reasoning text that references the needed value but never actually extracting it from the JSON bundle.
- Assuming a default value (e.g., `-1` or an empty list) when the GET response was never examined.

## Recommended Patterns
**Pattern 1: Mandatory verification step**
1. Issue the GET request.
2. **Wait** for the system to return the JSON response.
3. Parse the response to locate the exact field needed (e.g., `entry[0].resource.valueQuantity.value`).
4. Store the extracted scalar in a variable (conceptually) and use it for any subsequent comparison or decision.
5. Only after step 4 may you issue a POST, another GET, or `FINISH`.

**Pattern 2: Fallback when data is missing**
- If the parsed bundle has `total == 0` or the required field is absent, treat the value as *not available* and follow the task’s “no data” branch (e.g., do not order, answer "Patient not found").

**Pattern 3: Formatting the final output**
- When the task expects a scalar or list, return exactly that type. Do not embed explanatory sentences.
- Example of correct FINISH for a scalar value: `FINISH([3.5])`
- Example of correct FINISH for a string: `FINISH(["S3213957"])`

## Example Application
**Task:** "Check patient S3213957's most recent potassium level. If low, then order replacement potassium. Also schedule a serum potassium draw tomorrow at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3213957`
2. Receive the bundle. Extract the most recent `valueQuantity.value` (e.g., `3.2`).
3. Compare to the low‑threshold (e.g., `<3.5`).
4. If low, `POST` a MedicationRequest for potassium and a ServiceRequest for the follow‑up draw.
5. `FINISH(["Orders placed"] )` – note the output is a list containing only the required answer.

## Success Indicators
- The agent always waits for a GET response before any FINISH.
- Extracted values are used in conditional logic.
- Final output matches the exact format requested (scalar list, not a sentence).

## Failure Indicators
- FINISH appears immediately after a GET without an intervening parsing step.
- The agent references a value that was never extracted from the response.
- The output contains extra explanatory text or the wrong data type.
