---
description: Create a ServiceRequest when a recent lab value is below a defined threshold.
name: order_service_request_on_low_lab
provenance:
  action: ADD
  epoch: 4
  fixes: 15
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_5
  - task10_10
  - task5_16
  - task9_9
  - task9_14
  update_cycle: 0
tags:
- lab-order
- decision-logic
- service-request
version: 1
---

# Order ServiceRequest on Low Lab Value

## Pattern Description
You must automatically generate a `ServiceRequest` (or `MedicationRequest` when appropriate) whenever a recent laboratory observation is present and its numeric result falls below a task‑specific low‑value threshold. The skill isolates the numeric `valueQuantity.value` from the Observation, compares it to the threshold supplied in the task context, and, if the condition is met, builds a POST body that references the correct medication or lab order code (LOINC for labs, NDC for medications) and the patient reference.

- The pattern is reusable for any lab where the instruction mentions "if low, then order ...".
- It ties the decision directly to the extracted numeric value, avoiding free‑text parsing or unit mismatches.

## When to Use This Skill
- When a task asks to "check the last <lab> level within last 24 hours. If low, then order replacement ...".
- After you have successfully retrieved a Patient resource and the relevant Observation bundle.
- When the Observation entry contains a `valueQuantity` with a numeric `value` field.

## Common Failure Patterns
- Returning only the raw Observation bundle without extracting `valueQuantity.value`.
- Comparing the whole Observation object (or a string) to the threshold, causing the condition to never fire.
- Posting a `ServiceRequest` with the wrong `code` system (e.g., using the observation code instead of the medication NDC).
- Omitting the `subject.reference` or using an incorrect patient identifier.

## Recommended Patterns
**Pattern 1: Extract numeric value and evaluate threshold**
1. Locate the first entry in the Observation bundle where `resource.resourceType == "Observation"`.
2. Read `resource.valueQuantity.value` as a number (ignore `unit`).
3. Compare to the low‑value threshold supplied in the task (e.g., `if value < 1.5`).

```json
CORRECT: 2.0   // numeric
WRONG:   "2.0 mg/dL"   // string with unit
```

**Pattern 2: Build ServiceRequest POST body**
- For medication replacement (e.g., IV magnesium):
  ```json
  {
    "resourceType": "ServiceRequest",
    "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<NDC>", "display": "IV Magnesium" }] },
    "authoredOn": "<current_time>",
    "status": "active",
    "intent": "order",
    "priority": "stat",
    "subject": { "reference": "Patient/<MRN>" },
    "note": { "text": "Order IV magnesium replacement per dosing instructions." }
  }
  ```
- For a lab order, use the appropriate LOINC code in `code.coding.system = "http://loinc.org"`.

**Pattern 3: Fallback / No‑order rule**
- If the Observation bundle is empty or the latest result is not within the required time window, skip the POST and finish with an empty list (`FINISH([])`).
- If the value is not below the threshold, also skip ordering.

## Example Application
**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium."

**Step‑by‑step:**
1. `GET /Patient?identifier=S1023381` → obtain patient reference.
2. `GET /Observation?code=MG&patient=S1023381&date=ge2023-11-12T10:15:00+00:00` → receive bundle.
3. Extract `valueQuantity.value` from the most recent entry (e.g., `2.0`).
4. Compare: `2.0 < 1.5` → false, so **no** ServiceRequest.
5. If the value were `1.2`, build the POST body shown in Pattern 2 with the NDC from task context and execute `POST /ServiceRequest`.
6. Call `FINISH([])` when no order is needed, or `FINISH(["ServiceRequest created"])` after a successful POST.

**CORRECT output when low:** `FINISH(["ServiceRequest created"])`
**WRONG output when not low:** `FINISH(["Magnesium low, ordered"] )` (should be empty).

## Success Indicators
- The agent posts a `ServiceRequest` only when the numeric lab value is below the threshold.
- The POST body contains the correct NDC (or LOINC) code, patient reference, and a timestamp.
- `FINISH` payload reflects whether an order was created (empty list for no order).

## Failure Indicators
- `FINISH` contains an order message despite the value being normal.
- No POST is made even though the value is below the threshold.
- The POST body uses the observation code (`MG`) instead of the medication NDC.
- The patient reference is missing or malformed.
