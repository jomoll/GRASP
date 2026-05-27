---
description: Generate a ServiceRequest for electrolyte replacement when a recent lab
  value is below the therapeutic threshold.
name: electrolyte_replacement_service_request
provenance:
  action: ADD
  blind_select: random
  epoch: 1
  fixes_unused: 4
  probe_score_unused: -3
  regressions_unused: 3
  triggering_sample_ids:
  - task10_15
  - task10_20
  - task4_10
  - task10_24
  - task5_17
  - task9_6
  - task4_6
  - task4_27
  - task5_7
  - task9_27
  update_cycle: 0
tags:
- electrolyte
- servicerequest
- order_generation
version: 1
---

# Electrolyte Replacement ServiceRequest Generation

## Pattern Description
You must automatically create a **ServiceRequest** for an electrolyte replacement medication (e.g., IV magnesium, oral potassium) whenever a task asks you to check a recent lab value and order the replacement if the result is low. The skill isolates two reusable steps: (1) numeric extraction and threshold comparison, and (2) construction of a FHIR ServiceRequest with the correct code, patient reference, dosage instructions, and optional follow‑up test order. By separating the decision from the posting logic, the agent avoids simply returning the lab value and forgetting to act.

## When to Use This Skill
- The task description contains phrases like *"if low, then order replacement"* or *"order replacement according to dosing instructions"*.
- The task involves an Observation lookup for an electrolyte (e.g., magnesium, potassium, calcium) and provides a numeric threshold either explicitly or via context.
- After extracting the numeric value you have determined that the value is **below** the therapeutic threshold.
- The task may also request a repeat test (e.g., "pair this order with a morning serum potassium level").

## Common Failure Patterns
- Agent finishes with only the lab value (`FINISH(["2.1 mg/dL"])`) and never issues a POST.
- Agent posts a ServiceRequest but omits required fields (`code.coding`, `subject.reference`, `dosageInstruction`).
- Agent uses the wrong resource type (`MedicationRequest` instead of `ServiceRequest`).
- Agent posts a ServiceRequest for the wrong patient or with an incorrect NDC code.

## Recommended Patterns
**Pattern 1: Extract, compare, and decide**
1. Perform the GET Observation query as usual.
2. From the first entry, read `valueQuantity.value` (or `valueString` if numeric) and convert to a number.
3. Compare the number to the threshold supplied in the task context (e.g., `low if < 1.7 mg/dL`).
4. If the value is **not** low, call `FINISH(["value within normal range"])` and stop.

**Pattern 2: Build the ServiceRequest**
- Required fields:
  ```json
  {
    "resourceType": "ServiceRequest",
    "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "<NDC_OR_SCT_CODE>", "display": "<Medication name>" }] },
    "status": "active",
    "intent": "order",
    "subject": { "reference": "Patient/<MRN>" },
    "authoredOn": "<CURRENT_ISO_TIME>",
    "dosageInstruction": [{ "text": "<dosing instructions from task>" }]
  }
  ```
- If the task also asks for a repeat test, add a second ServiceRequest with `code.coding` for the appropriate lab (e.g., potassium) and set `occurrenceTiming.repeat` to the next day at 08:00.

**Pattern 3: Post and confirm**
1. POST the JSON to `POST {api_base}/ServiceRequest`.
2. If the POST succeeds, call `FINISH(["<Medication> replacement order placed for patient <MRN>"])`.
3. If the POST fails, fallback to `FINISH(["Failed to place replacement order"])`.

## Example Application
**Task:** "Check patient S0581164's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0581164&date=ge2023-11-12T10:15:00`
2. Extract `valueQuantity.value = 1.5` (mg/dL).
3. Compare to threshold `1.7 mg/dL` → low.
4. Build ServiceRequest:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "12345678", "display": "IV Magnesium" }] },
     "status": "active",
     "intent": "order",
     "subject": { "reference": "Patient/S0581164" },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "dosageInstruction": [{ "text": "Give 2 g magnesium sulfate IV over 30 min" }]
   }
   ```
5. `POST http://localhost:8080/fhir/ServiceRequest` with the body above.
6. On success, `FINISH(["IV magnesium replacement order placed for patient S0581164"])`.

## Success Indicators
- A `POST /ServiceRequest` call appears in the trace before the final `FINISH`.
- The `FINISH` output contains a short confirmation string, not the raw lab value.

## Failure Indicators
- The trace ends with `FINISH(["<value>"])` and no preceding ServiceRequest POST.
- The ServiceRequest JSON is missing `code.coding` or `subject.reference`.
- The POST returns an error and the agent does not report the failure.
