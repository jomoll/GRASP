---
description: "Trigger medication or lab orders when a retrieved lab value falls below\
  \ a task\u2011specified threshold"
name: low_lab_value_order
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task4_28
  - task9_5
  - task10_27
  update_cycle: 1
tags: []
version: 1
---

# Low Lab Value Order Trigger

## Pattern Description
You must treat any task that asks "Check the most recent *X* level. If low, then order *Y* …" as a two‑step workflow: (1) retrieve the latest observation for the specified code, (2) evaluate the numeric result against the low‑threshold supplied in the task description. If the value is below the threshold, automatically construct and POST a `ServiceRequest` (or `MedicationRequest`) using the NDC or LOINC details also provided in the task context, and optionally schedule a follow‑up observation as instructed.

## When to Use This Skill
- After a `GET /Observation?code={code}&patient={id}` returns a bundle with at least one entry and the task text contains phrases like "if low, then order" or "order replacement".
- The task description includes a numeric low‑threshold (e.g., "low if <3.5 mmol/L") and the medication or lab ordering information (NDC, LOINC, dosage instructions, follow‑up time).
- The observation value is present in `valueQuantity.value` (or a plain number in `valueString`).

## Common Failure Patterns
- Agent finishes with only the numeric value (`FINISH([4.5])`) and never issues the order.
- Agent extracts the value but compares it to the wrong field or uses string comparison, causing the threshold check to be skipped.
- Agent posts an order but omits required fields (e.g., missing `code.coding`, `subject.reference`, or `authoredOn`).
- Agent does not create the paired follow‑up lab request when the task asks for it.

## Recommended Patterns
**Pattern 1: Core low‑value detection and ordering**
1. Parse the task description to locate:
   - Lab code (`code=` parameter used in the GET request).
   - Low‑threshold numeric value (e.g., `<3.5`).
   - Ordering details: NDC or LOINC code, dosage text, and any timing instructions.
2. From the GET response, locate the most recent entry and read:
   - `valueQuantity.value` **or** numeric part of `valueString`.
3. Compare the extracted number to the threshold using a numeric `<` comparison.
4. If the value is below the threshold, build a `ServiceRequest` (or `MedicationRequest`) JSON:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "{LOINC}", "display": "{display}" }] },
     "authoredOn": "{current_time}",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/{patient_id}" },
     "note": { "text": "{dosage_instructions}" }
   }
   ```
5. POST the JSON to `/fhir/ServiceRequest` (or `/fhir/MedicationRequest` if a medication).

**Pattern 2: Scheduling a paired follow‑up observation**
1. If the task requests a repeat lab (e.g., "pair this order with a morning serum potassium level tomorrow at 8 am"), construct a second `ServiceRequest` with:
   - `code` set to the same lab LOINC.
   - `occurrenceDateTime` set to the requested future datetime.
2. POST this second request after the first order.

**Pattern 3: Output formatting**
- After successful ordering, finish with the original numeric value **and** a confirmation string, e.g.:
  `FINISH([3.2, "Ordered replacement potassium and scheduled follow‑up at 2023-11-14T08:00:00+00:00"])`
- If the value is not low, simply return the numeric value: `FINISH([4.5])`.

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low (<3.5), then order replacement potassium (NDC 12345‑6789‑01) and schedule a morning serum potassium level tomorrow at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
2. Extract the latest entry's `valueQuantity.value` → `3.2`.
3. Compare `3.2 < 3.5` → true.
4. Build first order:
   ```json
   {
     "resourceType": "MedicationRequest",
     "medicationCodeableConcept": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "12345-6789-01" }] },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "status": "active",
     "intent": "order",
     "subject": { "reference": "Patient/S3241217" },
     "dosageInstruction": [{ "text": "Replace potassium as per dosing instructions" }]
   }
   ```
   `POST http://localhost:8080/fhir/MedicationRequest`
5. Build follow‑up lab order:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Serum potassium" }] },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "occurrenceDateTime": "2023-11-14T08:00:00+00:00",
     "status": "active",
     "intent": "order",
     "subject": { "reference": "Patient/S3241217" }
   }
   ```
   `POST http://localhost:8080/fhir/ServiceRequest`
6. Finish:
   `FINISH([3.2, "Ordered replacement potassium and scheduled follow‑up at 2023-11-14T08:00:00+00:00"])`

## Success Indicators
- The agent posts a `MedicationRequest` or `ServiceRequest` **only when** the extracted value is below the threshold.
- The POST body contains the correct `code.coding` (NDC or LOINC) and `subject.reference`.
- A second follow‑up request is posted when the task specifies a future lab.
- The final `FINISH` includes the numeric value and, if an order was placed, a confirmation message.

## Failure Indicators
- Agent returns only the numeric value without any POST when the value is below the threshold.
- The posted request is missing required fields (`code`, `subject`, `authoredOn`).
- The agent posts an order even when the value is above the threshold.
- The follow‑up lab request is omitted despite being required.
- The `FINISH` output does not include the confirmation string when an order was made.
