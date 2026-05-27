---
description: "Check a lab value against a threshold and automatically create a replacement\
  \ medication and follow\u2011up order"
name: electrolyte_threshold_order
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  update_cycle: 1
tags:
- lab_threshold
- order_creation
- electrolyte
version: 1
---

# Electrolyte Lab Value Threshold Check and Replacement Order

## Pattern Description
You must treat any task that asks you to *check a lab value and, if it is below a defined threshold, order a replacement medication and a follow‑up lab* as a reusable decision pattern. The core capability is:
1. Retrieve the most recent Observation for the requested code.
2. Extract the numeric value from `valueQuantity.value` (ignore any unit string – the unit is always the same as the task’s context, e.g., mmol/L for potassium).
3. Compare the value to the task‑provided threshold (or a default clinical threshold you know, e.g., 3.5 mmol/L for potassium).
4. If the value is **below** the threshold, create two resources:
   - a **MedicationRequest** (or a ServiceRequest of type “medication”) that references the replacement product (use the NDC supplied in the task context).
   - a **ServiceRequest** for a repeat serum electrolyte draw scheduled for the next calendar day at the time the task specifies (often 08:00).
5. If the value is **not** below the threshold, simply report the value and state that no replacement is needed.

This pattern changes the agent’s behavior from “only report the lab” to “act on the lab when clinically indicated”.

## When to Use This Skill
- Task description contains phrases like *"check patient … most recent potassium level. If low, then order replacement potassium"*.
- The task provides a lab code (e.g., `K` for potassium, `MG` for magnesium) and a numeric threshold or a clinical guideline you know.
- The task also asks for a *follow‑up lab* (e.g., *"pair this order with a morning serum potassium level to be completed the next day at 8am"*).
- The observation query you performed returns a non‑empty Bundle with at least one `Observation` entry.

## Common Failure Patterns
- Agent extracts the value from `valueString` or from the wrong field (`effectiveDateTime`) and never compares it to the threshold.
- Agent finishes with a sentence like *"No potassium replacement ordered"* even when the value is below the threshold.
- Agent creates a `ServiceRequest` with the wrong `resourceType` (e.g., a generic `ServiceRequest` without medication details) or omits the follow‑up request entirely.
- The medication request uses the wrong coding system (e.g., SNOMED instead of the NDC supplied) or leaves out `dosageInstruction`.
- The follow‑up lab request is scheduled for the wrong date/time (e.g., same day instead of next day at 08:00).

## Recommended Patterns
**Pattern 1: Extract and compare lab value**
1. From the Observation Bundle, locate the entry with the highest `effectiveDateTime`.
2. Read `valueQuantity.value` as a number → `lab_value`.
3. Read `valueQuantity.unit` if needed for sanity check (should match expected unit).
4. Compare `lab_value` to the threshold (e.g., `if lab_value < 3.5`).

**Pattern 2: Create replacement MedicationRequest**
```json
POST {api_base}/MedicationRequest
{
  "resourceType": "MedicationRequest",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [{
      "system": "http://hl7.org/fhir/sid/ndc",
      "code": "<NDC_FROM_TASK>",
      "display": "Potassium chloride oral solution"
    }]
  },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>",
  "dosageInstruction": [{
    "text": "Give 20 mEq PO once",
    "timing": { "repeat": { "frequency": 1, "period": 1, "periodUnit": "d" } }
  }]
}
```
**Pattern 3: Create follow‑up serum electrolyte ServiceRequest**
```json
POST {api_base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/​liter] in Serum or Plasma" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>",
  "occurrenceDateTime": "<NEXT_DAY_08:00>",
  "note": [{ "text": "Follow‑up serum potassium as ordered with replacement" }]
}
```
**Pattern 4: Reporting when no order is needed**
- If `lab_value >= threshold`, FINISH with:
  `FINISH(["Latest <lab_name> for patient <MRN> is <lab_value> <unit> (effective <date>). No replacement needed."])`

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET {api_base}/Observation?code=K&patient=S6309742`
2. From the returned Bundle, pick the Observation with the latest `effectiveDateTime`.
3. Extract `valueQuantity.value` → `3.2`; unit → `mmol/L`.
4. Compare: `3.2 < 3.5` → **true**.
5. `POST {api_base}/MedicationRequest` using the NDC supplied in the task (e.g., `12345-6789-01`).
6. Compute next day date: if today is `2023‑11‑13`, set `occurrenceDateTime` to `2023‑11‑14T08:00:00+00:00`.
7. `POST {api_base}/ServiceRequest` for serum potassium with that `occurrenceDateTime`.
8. FINISH with confirmation:
   `FINISH(["Potassium 3.2 mmol/L is low; replacement potassium ordered (NDC 12345-6789-01) and follow‑up serum potassium scheduled for 2023‑11‑14T08:00:00+00:00."])`

## Success Indicators
- The FINISH output mentions both the replacement medication and the follow‑up lab.
- The system logs show two successful POST calls (MedicationRequest and ServiceRequest) with HTTP 201/200.
- The created resources can be retrieved with a subsequent GET and contain the correct patient reference, code, and timing.

## Failure Indicators
- FINISH output only reports the lab value and says *"no replacement"* despite the value being below threshold.
- No POST request is made, or the POST payload uses the wrong `resourceType` (e.g., `ServiceRequest` for medication without NDC).
- The follow‑up ServiceRequest has an `occurrenceDateTime` that is not the next day at 08:00.
- The MedicationRequest is missing `medicationCodeableConcept.coding.system` set to the NDC system.
