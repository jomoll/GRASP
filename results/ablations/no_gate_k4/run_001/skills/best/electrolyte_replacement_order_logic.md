---
description: "Order IV potassium or magnesium when the latest level is below the low\u2011\
  threshold"
name: electrolyte_replacement_order_logic
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task1_27
  - task8_14
  - task10_20
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task5_16
  - task9_11
  update_cycle: 0
tags: []
version: 3
---

# Electrolyte Replacement Order Logic

## Pattern Description
When a task asks to “check the most recent <electrolyte> level and, if low, order replacement”, the agent must (1) retrieve the latest Observation, (2) compare the numeric value against a clinically‑defined low‑threshold, and (3) create a ServiceRequest for the appropriate replacement. The decision must be made **before** any FINISH call.

## When to Use This Skill
- Tasks that mention “if low then order replacement” for potassium (K) or magnesium (MG).
- The request includes a dosing instruction or NDC code for the replacement product.
- The observation is expected to be within a recent time window (often last 24 h) but the skill should also handle any recent value.

## Common Failure Patterns
- Agent returns the lab value but never creates the ServiceRequest even when the value is below the threshold.
- Agent orders the replacement without checking the value (false positive).
- Agent uses the wrong NDC or coding system for the replacement ServiceRequest.

## Recommended Patterns
**Pattern 1: Retrieve and evaluate**
1. Perform `GET /Observation?code=<code>&patient=<MRN>&date=ge<now-24h>`.
2. If `total == 0`, invoke `missing_observation_placeholder` and **do not order**.
3. Extract the numeric value from `valueQuantity.value` (or from `valueString`).
4. Compare against the low‑threshold:
   - Potassium: `< 3.5 mmol/L`
   - Magnesium: `< 1.5 mg/dL`
5. If the value is **below** the threshold, proceed to Pattern 2.

**Pattern 2: Build the replacement ServiceRequest**
- For potassium use the NDC supplied in the task context (e.g., `"<K_NDC>"`).
- For magnesium use the NDC supplied for magnesium.
- Construct a minimal ServiceRequest:
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "<NDC>", "display": "IV <Electrolyte> replacement" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>"
}
```
- POST the ServiceRequest **before** calling FINISH.

**Pattern 3: Confirmation output**
- After a successful POST, call `order_confirmation_output` to return a concise message such as `"Potassium replacement ordered for patient S123456."`.
- Then call `FINISH([valueString])` where `valueString` is the scalar lab result (handled by `concise_lab_value_output`).

## Example Application
**Task:** "Check patient S3213957's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3213957&date=ge2023-11-12T10:15:00+00:00`
2. Bundle returns `valueQuantity.value = 3.2` mmol/L.
3. 3.2 < 3.5 → low.
4. Build ServiceRequest with potassium NDC (e.g., `"12345-6789-00"`).
5. `POST /fhir/ServiceRequest { … }`
6. `FINISH(["3.2 mmol/L"])` (scalar output enforced by the other skill).

**Correct behavior:** Replacement order is created and the scalar value is returned.

## Success Indicators
- A ServiceRequest POST is observed **only** when the extracted value is below the defined threshold.
- The POST body contains the correct NDC/code for the electrolyte.
- FINISH returns the scalar lab value (handled by `concise_lab_value_output`).
- No order is placed when the observation is missing or the value is normal/high.

## Failure Indicators
- FINISH is called without a preceding POST when the value is low.
- A POST is made regardless of the lab value (false positive ordering).
- The ServiceRequest uses an incorrect coding system or missing NDC.
- The agent returns a placeholder message instead of ordering when the value is low.
