---
description: "Add correct low\u2011potassium threshold and paired ordering logic"
name: observation_value_extraction_and_recency_check
provenance:
  action: MODIFY
  epoch: 0
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  - task5_16
  update_cycle: 1
tags: []
version: 3
---

# Observation Value Extraction and Recency Check

## Pattern Description
You must extract the most recent Observation for a given LOINC or code, verify that the result is recent enough for the clinical question, and then apply clinical thresholds to decide whether an order is required. This skill also handles the special case of serum potassium where a low value triggers a replacement order **and** a follow‑up potassium measurement scheduled for the next morning at 08:00.

## When to Use This Skill
- When a task asks to "check the most recent *X* level" and conditionally order a replacement (e.g., potassium, magnesium, calcium).
- When the task specifies a time window (e.g., last 24 h) for the observation.
- When a low potassium result must be paired with a future serum potassium order at 08:00 the next day.

## Common Failure Patterns
- Using the wrong field (`effectiveDateTime` vs `issued`) causing stale dates to be considered recent.
- Returning the value as a string with units instead of a numeric value (`"3.8 mmol/L"`).
- Applying an incorrect low‑threshold (e.g., treating 3.8 mmol/L as normal).
- Omitting the required paired follow‑up order for potassium.

## Recommended Patterns
**Pattern 1: Core extraction and recency check**
1. Issue a GET request: `GET {base}/Observation?code={code}&patient={MRN}`.
2. From the returned Bundle, locate the entry with the highest `effectiveDateTime` (or `issued` if `effectiveDateTime` missing).
3. Extract `valueQuantity.value` as a **number** and `valueQuantity.unit` for unit verification.
4. Verify the observation date is within the required window (e.g., `now - 24h`).

**Pattern 2: Threshold evaluation (potassium example)**
- If `code == "K"` (or LOINC for potassium) **and** `value < 4.0` **mmol/L**, treat as low.
- For other electrolytes use their appropriate low thresholds (magnesium < 1.5 mg/dL, calcium < 8.5 mg/dL, etc.).

**Pattern 3: Paired ordering rule for low potassium**
1. Create a `ServiceRequest` for replacement potassium using the NDC supplied in the task context.
2. Immediately create a second `ServiceRequest` for a serum potassium measurement:
   ```json
   {
     "resourceType": "ServiceRequest",
     "status": "active",
     "intent": "order",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma" }] },
     "subject": { "reference": "Patient/{MRN}" },
     "authoredOn": "{now_plus_1day_T08:00:00Z}",
     "note": [{ "text": "Follow‑up serum potassium after replacement" }]
   }
   ```
3. Include both orders in the same transaction if the API supports bundles, otherwise issue sequential POSTs.

**Pattern 4: Formatting the final answer**
- If no action is needed: `FINISH(["Latest {code} = {value} {unit} on {date}. No replacement needed."])`
- If replacement is ordered: `FINISH(["Ordered replacement {code} and scheduled follow‑up potassium test for {date_plus_1day_08:00}."])`

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6309742`
2. Parse the Bundle, find the latest entry:
   - `valueQuantity.value = 3.8`
   - `valueQuantity.unit = "mmol/L"`
   - `effectiveDateTime = 2023-11-12T12:23:00+00:00`
3. Verify the date is within 24 h of the task's current time (2023‑11‑13T10:15:00+00:00) → **true**.
4. Apply potassium threshold: `3.8 < 4.0` → **low**.
5. POST replacement potassium `ServiceRequest` (using NDC from context).
6. POST follow‑up potassium `ServiceRequest` with `authoredOn` set to `2023-11-14T08:00:00+00:00`.
7. `FINISH(["Ordered replacement potassium and scheduled follow‑up serum potassium for 2023-11-14T08:00:00+00:00."])`

## Success Indicators
- The agent extracts a numeric value and correct unit.
- The agent compares the value against the proper low threshold.
- When low, two `POST /ServiceRequest` calls are made: one for replacement, one for follow‑up.
- The final FINISH output mentions both the order and the scheduled follow‑up.

## Failure Indicators
- The extracted value is still a string with units attached.
- The agent uses a threshold of 3.5 mmol/L (or any value that treats 3.8 mmol/L as normal).
- Only the replacement order is posted, missing the follow‑up potassium test.
- The FINISH output does not mention the follow‑up order or uses the wrong date/time.
