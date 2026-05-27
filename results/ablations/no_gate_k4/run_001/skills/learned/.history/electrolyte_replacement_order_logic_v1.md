---
description: "Order IV magnesium or potassium replacement when a recent level is below\
  \ the low\u2011threshold"
name: electrolyte_replacement_order_logic
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
tags: []
version: 1
---

# electrolyte_replacement_order_logic

## Pattern Description
You must decide whether to place a replacement order for serum magnesium or potassium based on the most recent lab value within a defined time window. If the value is below the clinically‑defined low threshold, construct a `ServiceRequest` with the appropriate coding, dosage, and NDC. If no recent lab is found or the value is normal, do **not** place an order and return a clear “no action” message.

## When to Use This Skill
- Task asks to *check* a serum magnesium or potassium level within the last 24 hours and *order replacement* if low.
- The task explicitly mentions dosing instructions or an NDC code for the replacement product.
- Example triggers:
  - `GET /Observation?code=MG&patient=…&date=ge…&date=le…`
  - `GET /Observation?code=K&patient=…&date=ge…&date=le…`
- The task expects a FINISH output that either confirms the order or states that no order was needed.

## Common Failure Patterns
- Agent returns an empty array `FINISH([])` when the value is low.
- Agent returns only a confirmation message without the required order fields (e.g., missing `code.coding[0].code`).
- Agent orders replacement even when the lab result is missing or normal.

## Recommended Patterns
**Pattern 1: extract and evaluate the lab value**
1. Perform the GET request for the target code (MG or K) with the appropriate date range.
2. If the Bundle `total == 0`, treat as missing → `FINISH(["No recent result; no replacement ordered."])`.
3. If entries exist, sort by `effectiveDateTime` descending and extract the most recent `valueQuantity.value`.
4. Compare the numeric value to the low‑threshold (e.g., Mg < 1.5 mg/dL, K < 3.5 mmol/L).

**Pattern 2: construct the replacement ServiceRequest**
- For magnesium:
  ```json
  {
    "resourceType": "ServiceRequest",
    "status": "active",
    "intent": "order",
    "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "428341000124106", "display": "Magnesium sulfate 50% IV" }] },
    "medicationCodeableConcept": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "12345-6789-00" }] },
    "dosageInstruction": [{ "text": "Give 2 g over 30 min" }],
    "subject": { "reference": "Patient/{{patient_id}}" },
    "authoredOn": "{{now}}"
  }
  ```
- For potassium (replace with appropriate SNOMED and NDC codes).
5. POST the ServiceRequest to `/ServiceRequest`.
6. Return a concise confirmation, e.g., `FINISH(["Magnesium replacement ordered for patient {{patient_id}}."])`.

**Pattern 3: no‑order fallback**
- If the value is ≥ low‑threshold, return `FINISH(["Serum {{lab_name}} is normal; no replacement ordered."])`.

## Example Application
**Task:** “Check patient S6541353's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium.”
**Step‑by‑step:**
1. GET `.../Observation?code=MG&patient=S6541353&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`.
2. Bundle total = 0 → `FINISH(["No magnesium level recorded in the last 24 hours; no replacement ordered."])`.
3. If a result existed and value = 1.2 mg/dL (< 1.5), build the ServiceRequest JSON (as above) and POST.
4. After successful POST, `FINISH(["Magnesium replacement ordered for patient S6541353."])`.

## Success Indicators
- When a low value is present, a POST to `/ServiceRequest` is made with the correct SNOMED and NDC codes.
- FINISH output contains a clear confirmation string.
- When no result or a normal value is present, FINISH output states that no replacement was ordered.

## Failure Indicators
- FINISH output is empty or does not mention the ordering decision.
- The ServiceRequest payload is missing `code`, `medicationCodeableConcept`, or dosage fields.
- An order is placed despite the lab being normal or missing.
