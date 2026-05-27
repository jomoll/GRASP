---
description: "Create ServiceRequests when a lab value is below a threshold and schedule\
  \ a paired follow\u2011up order."
name: conditional_service_request_creation
provenance:
  action: ADD
  blind_select: random
  epoch: 0
  fixes_unused: 4
  probe_score_unused: -3
  regressions_unused: 2
  triggering_sample_ids:
  - task4_26
  - task9_28
  - task2_9
  - task5_17
  - task9_3
  - task4_23
  - task9_27
  - task2_15
  - task2_6
  - task10_24
  update_cycle: 1
tags: []
version: 1
---

# Conditional ServiceRequest Creation for Lab‑Driven Orders

## Pattern Description
You must translate a clinical rule that depends on a lab result into one or more FHIR `ServiceRequest` resources. The pattern first extracts the most recent observation for a specified code, evaluates it against a numeric threshold, and, if the condition is met, creates a therapeutic `ServiceRequest` (e.g., potassium replacement) **and** a scheduled follow‑up lab `ServiceRequest` (e.g., repeat serum potassium at 08:00 the next day). This reusable capability applies to any lab‑driven ordering scenario, not just potassium.

## When to Use This Skill
- When a task description contains a conditional phrase like *"If low, then order replacement <medication> according to dosing instructions"*.
- When the same task also asks to *"pair this order with a morning serum <lab> level to be completed the next day at 8am"*.
- When the agent has already fetched the patient resource and the latest observation for the relevant lab code.

## Common Failure Patterns
- The agent finishes with a textual answer and never issues a `POST /ServiceRequest`.
- The agent extracts the observation value as a string (e.g., `"4.7 mmol/L"`) and compares it incorrectly.
- The agent creates only the replacement order but omits the follow‑up lab request.
- The agent posts a `ServiceRequest` with missing required fields (`subject`, `code`, `authoredOn`).

## Recommended Patterns
**Pattern 1: Extract and evaluate the lab value**
1. Identify the observation bundle entry with the highest `effectiveDateTime` for the requested `code` (e.g., `K`).
2. Prefer `valueQuantity.value` (numeric). If only `valueString` is present, parse the leading number.
3. Compare the numeric value to the threshold supplied in the task context (default potassium low threshold = 3.5 mmol/L).

```json
// Correct extraction
value = entry.resource.valueQuantity?.value
// Wrong extraction
value = entry.resource.valueString   // "4.7 mmol/L" – not a number
```

**Pattern 2: Create the therapeutic ServiceRequest**
1. Build a `ServiceRequest` with:
   - `status: "active"`
   - `intent: "order"`
   - `code.coding` using the medication’s NDC or SNOMED code (provided in task context).
   - `subject.reference` = `Patient/<MRN>`
   - `authoredOn` = current task time.
2. POST to `/fhir/ServiceRequest`.

```json
POST /fhir/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<NDC>" }] },
  "subject": { "reference": "Patient/S123456" },
  "authoredOn": "2023-11-13T10:15:00+00:00"
}
```

**Pattern 3: Create the follow‑up lab ServiceRequest**
1. Compute `occurrenceDateTime` = task time + 1 day, set hour to `08:00`.
2. Use the same lab `code` as the original observation.
3. Include a clear `note.text` indicating the purpose (e.g., "Repeat serum potassium for monitoring").
4. POST the second `ServiceRequest`.

```json
POST /fhir/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma" }] },
  "subject": { "reference": "Patient/S123456" },
  "authoredOn": "2023-11-13T10:15:00+00:00",
  "occurrenceDateTime": "2023-11-14T08:00:00+00:00",
  "note": { "text": "Repeat serum potassium for monitoring" }
}
```

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `/fhir/Observation?code=K&patient=S3228213` – retrieve bundle.
2. Select entry with latest `effectiveDateTime` (e.g., `2023-11-12T12:59:00+00:00`).
3. Extract `valueQuantity.value = 3.2`.
4. Compare to threshold `3.5` → low.
5. POST therapeutic `ServiceRequest` for potassium replacement (use NDC from task context).
6. Compute next‑day 08:00 (`2023-11-14T08:00:00+00:00`).
7. POST follow‑up `ServiceRequest` for serum potassium with `occurrenceDateTime` set.
8. FINISH([]).

## Success Indicators
- Two `POST /fhir/ServiceRequest` calls appear in the trace after the lab extraction.
- The first POST contains a medication code (NDC or SNOMED) and `subject` referencing the patient.
- The second POST contains the same lab `code` as the original observation and an `occurrenceDateTime` exactly one day later at 08:00.
- FINISH is called with an empty array (or a confirmation message) after the POSTs.

## Failure Indicators
- Only a `FINISH` with a textual answer and no POST calls.
- A single POST that creates the replacement but omits the follow‑up request.
- The posted `ServiceRequest` is missing required fields (`status`, `intent`, `subject`).
- The lab value is parsed as a string and the comparison always fails, preventing order creation.
