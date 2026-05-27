---
description: "Add low\u2011value detection and paired follow\u2011up order for potassium/magnesium\
  \ replacement"
name: electrolyte_replacement_order_logic
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 1
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
tags:
- electrolyte
- order_logic
- low_threshold
version: 2
---

# Electrolyte Replacement Order Logic

## Pattern Description
You must automatically create a replacement order when a serum electrolyte (potassium **K** or magnesium **MG**) is below its clinical low‑threshold and, when required, schedule a follow‑up lab draw. The skill isolates three reusable steps: (1) extract the most recent numeric value, (2) compare it to the substance‑specific low‑threshold, and (3) issue a `ServiceRequest` for the replacement medication **and** a paired `ServiceRequest` for a repeat lab at the requested time.

## When to Use This Skill
- When a task asks to *"check the most recent potassium/magnesium level and order replacement if low"*.
- When the task also specifies a *paired follow‑up lab* (e.g., "order a morning serum potassium level tomorrow at 8 am").
- When the observation bundle may contain multiple entries; you must select the most recent one within any date‑range filter.

## Common Failure Patterns
- Returning only the lab value without creating any `ServiceRequest`.
- Using the wrong field (`valueString` or `valueQuantity.unit`) causing the numeric comparison to fail.
- Missing the low‑threshold check (e.g., treating any value as acceptable).
- Forgetting to add the paired repeat lab `ServiceRequest` when the instruction requires it.
- Posting the order but not confirming success before calling `FINISH`.

## Recommended Patterns
**Pattern 1: Extract numeric value and timestamp**
1. From the GET response bundle, locate the entry with the highest `effectiveDateTime`.
2. Read `valueQuantity.value` as a number; ignore `valueQuantity.unit` (assume mmol/L for K, mg/dL for MG).
3. Store the timestamp from `effectiveDateTime` for later use.

**Pattern 2: Low‑threshold decision**
- Potassium low‑threshold: **3.5 mmol/L**.
- Magnesium low‑threshold: **1.7 mg/dL**.
```python
if code == "K" and value < 3.5:
    need_order = True
elif code == "MG" and value < 1.7:
    need_order = True
else:
    need_order = False
```

**Pattern 3: Create replacement `ServiceRequest`**
- Use the NDC supplied in the task context (e.g., `NDC_K_REPLACEMENT` or `NDC_MG_REPLACEMENT`).
- Build a minimal `ServiceRequest`:
```json
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<NDC>" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>"
}
```
- POST to `/fhir/ServiceRequest` and verify a 201/200 response before proceeding.

**Pattern 4: Paired follow‑up lab request (optional)**
- If the task mentions a repeat lab time, construct a second `ServiceRequest` with `code` set to the appropriate LOINC (e.g., `2951-2` for serum potassium) and `occurrenceDateTime` set to the requested datetime.
- Include `basedOn` referencing the replacement order for traceability.

**Pattern 5: Confirmation output**
- After successful POST(s), return a concise confirmation:
```
FINISH(["Potassium replacement ordered for patient S123456; follow‑up potassium draw scheduled for 2023‑11‑14T08:00:00+00:00."])
```
- If no replacement is needed, return the numeric value only (handled by `concise_lab_value_output`).

## Example Application
**Task:** "Check patient S1311412's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET /Observation?code=K&patient=S1311412` → bundle with latest entry `valueQuantity.value = 3.4`.
2. Extract `3.4` (mmol/L) → below 3.5 → `need_order = True`.
3. Build replacement order using NDC from task context and POST.
4. Build follow‑up lab order with LOINC `2951-2` and `occurrenceDateTime = 2023-11-14T08:00:00+00:00` and POST.
5. Verify both POSTs succeeded.
6. `FINISH(["Potassium replacement ordered for patient S1311412; follow‑up potassium draw scheduled for 2023‑11‑14T08:00:00+00:00."])

## Success Indicators
- A `ServiceRequest` POST is made **after** the low value is detected.
- The POST response status is 200/201 and the agent waits for confirmation before `FINISH`.
- The final `FINISH` output contains a short confirmation string, not just the lab value.

## Failure Indicators
- The agent calls `FINISH` immediately after extracting the value, without any POST.
- The confirmation string is missing or contains the raw lab value only.
- The POST request is issued but the agent does not check the response and still finishes.
- The follow‑up lab `ServiceRequest` is omitted when the task explicitly asks for it.
