---
description: "Create medication and follow\u2011up lab orders when a retrieved lab\
  \ value is below a defined threshold."
name: conditional_order_creation
provenance:
  action: ADD
  epoch: 1
  fixes: 14
  probe_score: 4
  regressions: 5
  triggering_sample_ids:
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task9_1
  - task9_5
  - task8_7
  - task9_9
  - task10_10
  - task9_8
  update_cycle: 1
tags:
- order_creation
- conditional_logic
- lab_result
version: 1
---

# Conditional Order Creation

## Pattern Description
You must translate a clinical decision rule that depends on a lab result into concrete FHIR POST actions. After fetching the most recent Observation for a given code, extract the numeric value, compare it to a task‑specific low‑threshold, and if the condition is met, (1) POST a `MedicationRequest` (or appropriate `ServiceRequest`) for the replacement therapy and (2) POST a `ServiceRequest` for a repeat lab at the requested future time. This pattern applies to any lab‑driven ordering task, not just potassium.

## When to Use This Skill
- When the task description says *"If low, then order ..."* or *"If high, then order ..."* for a lab value.
- After a successful `GET` of an `Observation` that returns a numeric `valueQuantity.value` (or a parsable `valueString`).
- When the task also requests a follow‑up lab (e.g., "pair this order with a morning serum potassium level to be completed the next day at 8am").

## Common Failure Patterns
- Agent finishes with only the lab value (`FINISH([value, timestamp])`) and never issues a POST.
- Agent extracts the value as a string with units (e.g., `"3.9 mmol/L"`) and fails numeric comparison.
- Agent posts the order but omits required fields such as `medicationCodeableConcept.coding.code` (NDC) or `authoredOn`.
- Agent does not schedule the follow‑up lab, leaving the second part of the instruction unmet.

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. From the `Bundle` response, locate the first entry's `resource` → `valueQuantity.value` (numeric). If the value is in `valueString`, parse the leading number.
2. Compare the numeric value to the task‑provided threshold (e.g., potassium low if `< 3.5`).
3. If the condition is *not* met, `FINISH([])` (no order needed).

**Pattern 2: Post replacement medication request**
- Build a `MedicationRequest` JSON:
```json
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<NDC_FROM_CONTEXT>" }]
  },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>",
  "dosageInstruction": [{ "text": "<DOSING_INSTRUCTIONS_FROM_CONTEXT>" }]
}
```
- `POST` to `/fhir/MedicationRequest`.

**Pattern 3: Schedule follow‑up lab request**
- Compute the desired datetime (e.g., next day at 08:00) based on the current task time.
- Build a `ServiceRequest` JSON:
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC_FOR_LAB>" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>",
  "occurrenceDateTime": "<NEXT_DAY_08:00>",
  "note": [{ "text": "Repeat <LAB_NAME> as ordered in the clinical instruction." }]
}
```
- `POST` to `/fhir/ServiceRequest`.

**Pattern 4: Finalize**
- After successful POST(s), call `FINISH([])` (empty array) because the answer is the performed actions, not a numeric result.

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET /fhir/Observation?code=K&patient=S6474456`
2. From the bundle, extract `valueQuantity.value` → `3.4`.
3. Compare: `3.4 < 3.5` → condition met.
4. `POST /fhir/MedicationRequest` with NDC `12345-6789-00` and dosage from context.
5. Compute next‑day 08:00 (`2023-11-14T08:00:00+00:00`).
6. `POST /fhir/ServiceRequest` with LOINC `2823-3` (serum potassium) and `occurrenceDateTime` set to the computed datetime.
7. `FINISH([])`.

**Correct output:**
```
FINISH([])
```

## Success Indicators
- The agent issues a `POST` to `/fhir/MedicationRequest` *and* a `POST` to `/fhir/ServiceRequest` when the lab value is below the threshold.
- The `MedicationRequest` contains the correct NDC code and dosage text.
- The `ServiceRequest` includes `occurrenceDateTime` set to the requested future time.
- Final `FINISH` payload is an empty JSON array (`[]`).

## Failure Indicators
- Agent finishes with only the lab value and no POST calls.
- POST body is missing required fields (e.g., `medicationCodeableConcept` or `occurrenceDateTime`).
- The numeric comparison fails because the value was not parsed correctly (e.g., still contains units).
- `FINISH` returns a non‑array or includes extraneous text.
