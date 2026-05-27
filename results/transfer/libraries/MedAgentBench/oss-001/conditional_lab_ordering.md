---
description: "Detect low lab values and automatically create replacement orders with\
  \ optional follow\u2011up"
name: conditional_lab_ordering
provenance:
  action: ADD
  epoch: 7
  fixes: 11
  probe_score: 7
  regressions: 0
  triggering_sample_ids: []
  update_cycle: 0
tags:
- lab
- ordering
- conditional
version: 1
---

# Conditional Lab Ordering Based on Observation Value

## Pattern Description
You must handle tasks that ask you to *check a recent laboratory result* and *order a replacement medication or a follow‑up test* only when the result is below a clinically‑relevant threshold. The pattern is reusable for any lab (e.g., potassium, magnesium, hemoglobin A1c) that appears with a conditional phrase such as “if low, then order …”, “when the value is below …”, or “should a low result be found, place an order”. First retrieve the observation, extract the numeric value, compare it to the threshold (either explicitly given in the task or using a sensible default), and then issue the appropriate `POST /ServiceRequest` (or other order resource). If the task also requests a paired future lab, create a second `ServiceRequest` with the specified timing.

## When to Use This Skill
- When a task mentions a lab code (e.g., `code=K`, `code=MG`, `code=A1C`) **and** includes a conditional clause like *"if low, then order…"* or *"when the result is below X, place a replacement"*.
- When the task asks for a *paired* order (e.g., “order replacement potassium and schedule a morning serum potassium level for tomorrow at 8 am”).
- When the task does **not** simply request the raw value but expects a decision/action based on that value.

## Common Failure Patterns
- Returning only the numeric value (or an empty list) without creating any `ServiceRequest`.
- Extracting the value as a string with units (e.g., `"3.5 mmol/L"`) and failing the numeric comparison.
- Ignoring the conditional cue and always ordering, or never ordering even when the value is low.
- Missing the follow‑up order when the task explicitly requests a future lab.

## Recommended Patterns
**Pattern 1: Retrieve and extract the recent observation**
1. Build a GET URL that includes the lab `code=` and a 24‑hour date filter **if the task mentions “within last 24 hours”**.
2. From the returned Bundle, locate the first entry with `resourceType: "Observation"`.
3. Extract the numeric result from `valueQuantity.value` (ignore `valueQuantity.unit`).
4. Store the value in a variable `lab_value`.

**Pattern 2: Compare to the appropriate threshold**
- Use the threshold supplied in the task text if present (e.g., "below 3.5 mmol/L").
- If no explicit threshold, fall back to sensible defaults:
  - Potassium (K): `< 3.5 mmol/L`
  - Magnesium (MG): `< 1.5 mg/dL`
  - HbA1c (A1C): `> 9.0 %` for ordering a repeat test.
5. If `lab_value` meets the “low” condition, proceed to Pattern 3; otherwise FINISH with the numeric value only.

**Pattern 3: Create the replacement order**
1. POST a `ServiceRequest` with:
   - `code.coding[0].system` set to the appropriate coding system (e.g., SNOMED or NDC).
   - `code.coding[0].code` set to the replacement medication’s NDC (provided in the task context).
   - `subject.reference` = `Patient/<MRN>`.
   - `authoredOn` = current task time.
   - `status` = "active", `intent` = "order", `priority` = "stat".
2. Capture the returned resource ID and return it via `FINISH(["ServiceRequest <id> created"])`.

**Pattern 4: Create a paired follow‑up lab order (optional)**
1. If the task asks for a future lab (e.g., “morning serum potassium level to be completed the next day at 8 am”), POST a second `ServiceRequest`:
   - Same `code` as the original lab (e.g., LOINC for potassium).
   - `occurrenceDateTime` = `<current date + 1 day> T08:00:00+00:00`.
2. Include a note describing the purpose.
3. Return both confirmations in the FINISH payload.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=K&patient=S3228213&date=ge2023-11-12T10:15:00+00:00&date=le2023-11-13T10:15:00+00:00`.
2. Extract `lab_value = 3.2` from `valueQuantity.value`.
3. Compare: `3.2 < 3.5` → condition true.
4. POST replacement order:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://ndc.org","code":"<K_REPLACEMENT_NDC>","display":"Potassium chloride"}]},
     "authoredOn":"2023-11-13T10:15:00+00:00",
     "status":"active","intent":"order","priority":"stat",
     "subject":{"reference":"Patient/S3228213"},
     "note":{"text":"Order replacement potassium as per dosing instructions."}
   }
   ```
5. POST follow‑up lab order:
   ```json
   {
     "resourceType":"ServiceRequest",
     "code":{... same LOINC for potassium ...},
     "authoredOn":"2023-11-13T10:15:00+00:00",
     "occurrenceDateTime":"2023-11-14T08:00:00+00:00",
     "status":"active","intent":"order","priority":"routine",
     "subject":{"reference":"Patient/S3228213"},
     "note":{"text":"Morning serum potassium level for follow‑up."}
   }
   ```
6. FINISH(["ServiceRequest <id1> created", "ServiceRequest <id2> created"]).

## Success Indicators
- The FINISH payload contains confirmation messages for one or more `ServiceRequest` resources.
- The POST bodies include the correct `code.coding` (NDC or SNOMED) and reference the patient MRN.
- When the lab value is not low, FINISH returns only the numeric value (or `-1` if unavailable) and no order is created.

## Failure Indicators
- FINISH returns an empty list or only the numeric value despite the condition being met.
- The posted `ServiceRequest` lacks the required `code.coding` or `subject.reference` fields.
- The follow‑up order is missing or has an incorrect `occurrenceDateTime`.
- Units are concatenated with the numeric value, causing the comparison to fail.
