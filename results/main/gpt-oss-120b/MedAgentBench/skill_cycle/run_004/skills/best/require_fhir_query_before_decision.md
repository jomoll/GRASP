---
description: Force a GET request for needed FHIR resources before any ordering or
  answer logic is executed
name: require_fhir_query_before_decision
provenance:
  action: ADD
  epoch: 3
  fixes: 4
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_8
  - task10_15
  - task10_21
  - task10_27
  - task10_20
  - task9_20
  - task2_30
  - task10_16
  - task8_13
  - task4_28
  update_cycle: 0
tags:
- decision_control
- fhir_query
version: 1
---

# Require FHIR Query Before Decision

## Pattern Description
You must never make a clinical decision (e.g., create a MedicationRequest, ServiceRequest, or return a numeric answer) without first retrieving the relevant FHIR resource that informs that decision. The agent should treat the absence of a recent GET as a hard stop: issue the appropriate GET, wait for the response, then continue. This prevents decisions based on stale or missing data and eliminates the "missing_fhir_query_before_decision" failure mode.

## When to Use This Skill
- Any task that requires checking a lab value, vital sign, or patient attribute before ordering medication or returning a value.
- When the instruction mentions "most recent", "last", "current age", or any conditional logic based on a patient observation.
- Before constructing a FINISH response that contains a computed answer or an empty‑array placeholder for a conditional order.

## Common Failure Patterns
- Directly POSTing a MedicationRequest or ServiceRequest without a preceding GET Observation/Patient.
- Returning `FINISH([value])` or `FINISH([])` after reasoning, but the required GET for that value was never issued.
- Using a hard‑coded placeholder (e.g., assuming potassium is low) without confirming via a GET.

## Recommended Patterns
**Pattern 1: Verify required data is present**
1. Parse the task description and identify required FHIR resources (e.g., Observation?code=K&patient=XYZ, Patient?identifier=XYZ).
2. Scan the current turn’s action list. If no GET for each required resource appears, **immediately output a GET request** for the missing resource and **stop**.
3. Wait for the system to return the GET response before proceeding.

**Pattern 2: Continue after successful GET**
1. When a GET response is received, extract the needed field (e.g., `valueQuantity.value` for a lab, `birthDate` for age).
2. Apply the conditional logic described in the task.
3. Only then construct POST bodies or FINISH output.

**Pattern 3: Fallback when GET returns no entries**
- If the GET Bundle `total` is 0, treat the observation as unavailable and follow the task’s "do nothing" branch (e.g., return `FINISH([])` for conditional orders).

## Example Application
**Task:** "Check patient S123456's most recent potassium level. If low, order replacement potassium and schedule a follow‑up lab."

**Step‑by‑step:**
1. Identify required resources: `Observation?code=K&patient=S123456`.
2. No GET present → output:
   ```
   GET http://localhost:8080/fhir/Observation?code=K&patient=S123456
   ```
3. After the system returns the Bundle, extract `entry[0].resource.valueQuantity.value`.
4. If value < 3.5, POST MedicationRequest and ServiceRequest; otherwise `FINISH([])`.

**Correct output after GET:**
```json
POST http://localhost:8080/fhir/MedicationRequest { ... }
POST http://localhost:8080/fhir/ServiceRequest { ... }
FINISH([])
```
**Incorrect (missing GET):**
```json
POST http://localhost:8080/fhir/MedicationRequest { ... }
FINISH([])
```

## Success Indicators
- The first action for a conditional task is always a GET that matches the identified resource.
- No POST or FINISH appears before the required GET response.
- When the GET returns no entries, the agent returns an empty array without creating orders.

## Failure Indicators
- A POST or FINISH is emitted while the needed GET is still absent.
- The agent references a lab value that was never retrieved.
- The FINISH output contains a computed answer but the log shows no prior GET for the source data.
