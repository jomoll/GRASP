---
description: "Order potassium replacement and a next\u2011day follow\u2011up test\
  \ when a recent potassium value is low"
name: low_potassium_replacement_order
provenance:
  action: ADD
  epoch: 4
  fixes: 9
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_5
  - task2_28
  - task3_3
  - task2_14
  - task9_14
  - task3_19
  - task9_1
  - task8_19
  update_cycle: 1
tags:
- potassium
- lab_replacement
- order_logic
version: 1
---

# Low Potassium Replacement Ordering

## Pattern Description
You must automatically order a potassium replacement medication and schedule a follow‑up serum potassium test when a patient’s most recent potassium result is below a clinically‑defined low threshold. This pattern is triggered after you have successfully retrieved the latest potassium Observation, extracted the numeric value, and determined that it is low. The ordering logic is independent of other lab‑replacement rules and includes a paired follow‑up test to re‑check the level the next morning.

## When to Use This Skill
- The task explicitly asks to *check the most recent potassium level* and *order replacement potassium if low*.
- You have already performed a `GET /Observation?code=K&patient={MRN}` and received a Bundle containing at least one Observation with a `valueQuantity.value` field.
- The extracted numeric value is **< 3.5** (mmol/L) – the commonly used low‑potassium cutoff (adjustable per institution).
- The task also requests a *morning serum potassium* test to be performed the next day at 08:00.

## Common Failure Patterns
- Returning `FINISH([value])` without creating any ServiceRequest.
- Comparing the wrong field (e.g., `valueQuantity.unit` or `effectiveDateTime`) instead of the numeric value.
- Using the wrong coding system for the replacement medication (e.g., missing the required NDC or LOINC code).
- Forgetting to schedule the follow‑up potassium test.
- Posting duplicate ServiceRequests because duplicate‑prevention logic was not applied.

## Recommended Patterns
**Pattern 1: Detect low potassium and order replacement**
1. **Extract the numeric result**: `value = observation.entry[0].resource.valueQuantity.value` (must be a number).
2. **Check the threshold**: `if value < 3.5:`
3. **Build the replacement ServiceRequest** using the NDC provided in the task context (or a default coding):
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "{NDC_FOR_POTASSIUM}", "display": "Potassium replacement" }] },
     "subject": { "reference": "Patient/{MRN}" },
     "authoredOn": "{CURRENT_TIME}"
   }
   ```
4. **POST** the ServiceRequest to `/fhir/ServiceRequest`.

**Pattern 2: Schedule next‑day serum potassium test**
1. Compute the follow‑up datetime: `follow_up = now + 1 day` and set time to `08:00`.
2. Build a second ServiceRequest for the lab test using the LOINC code for serum potassium (e.g., `2823-3`):
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "priority": "routine",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Serum potassium" }] },
     "subject": { "reference": "Patient/{MRN}" },
     "occurrenceDateTime": "{follow_up_iso}",
     "authoredOn": "{CURRENT_TIME}"
   }
   ```
3. **POST** this ServiceRequest as well.

**Pattern 3: Prevent duplicate orders**
- Before posting each ServiceRequest, run a `GET /ServiceRequest?patient=Patient/{MRN}&code={code}&status=active`.
- If the response Bundle has `total > 0`, skip the POST for that request.

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597`
2. Parse the Bundle, extract `valueQuantity.value` → `4.7`.
3. Compare: `4.7 >= 3.5` → **not low** → **no ServiceRequest** is created; simply `FINISH([4.7])`.
---
If the value had been `3.2`:
1. Detect low → build replacement ServiceRequest (using the NDC from task context).
2. Build follow‑up serum potassium ServiceRequest with `occurrenceDateTime` set to tomorrow at `08:00`.
3. Perform duplicate checks, then POST both resources.
4. Call `FINISH([-1])` (sentinel indicating ordering was performed).

## Success Indicators
- One or two `POST /fhir/ServiceRequest` calls appear in the trace (replacement and optional follow‑up).
- The POST bodies match the JSON structures shown above.
- The final `FINISH` call returns `[-1]` (or another sentinel defined by the task) after successful ordering.

## Failure Indicators
- Only a `FINISH([value])` call with no preceding POSTs.
- POST body uses the wrong `code` system or omits the NDC/LOINC.
- Follow‑up test ServiceRequest is missing or has an incorrect `occurrenceDateTime`.
- Duplicate ServiceRequests are posted despite an existing active request.
