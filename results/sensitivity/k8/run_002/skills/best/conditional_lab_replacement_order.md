---
description: "Add ordering logic for low lab values and schedule required follow\u2011\
  up tests"
name: conditional_lab_replacement_order
provenance:
  action: MODIFY
  epoch: 2
  fixes: 12
  parent_version: 1
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task4_10
  - task4_28
  - task9_1
  - task2_14
  - task2_22
  - task9_5
  - task9_20
  - task1_23
  - task10_10
  - task1_15
  update_cycle: 0
tags: []
version: 2
---

# Conditional Lab Replacement and Follow‑up Ordering

## Pattern Description
You must decide whether a replacement medication (or electrolyte) needs to be ordered based on the most recent lab value and, if an order is required, also create a follow‑up lab request. The skill first fetches the latest Observation for the specified code, extracts the numeric `valueQuantity.value`, compares it to a **low‑threshold** defined for that lab, and then:
1. Posts a `ServiceRequest` for the replacement product (using the NDC supplied in the task context).
2. Posts a second `ServiceRequest` for a repeat measurement at the time specified in the task (e.g., “next day at 8 am”).
3. Returns the numeric value (and optionally the date) via `FINISH`.

## When to Use This Skill
- When a task asks to *check a lab value and, if low, order replacement and a repeat test* (e.g., potassium, magnesium, calcium).
- When the task provides:
  - `code` for the lab (e.g., "K" for potassium).
  - Low‑threshold value (implicit in clinical guidance; use common defaults: K < 3.5 mmol/L, Mg < 1.5 mg/dL).
  - NDC or LOINC for the replacement medication.
  - Desired timing for the follow‑up lab (e.g., “next day at 8 am”).

## Common Failure Patterns
- Returning only the numeric value without posting any `ServiceRequest`.
- Posting the replacement order but omitting the follow‑up lab request.
- Using the wrong field (`effectiveDateTime` instead of `valueQuantity.value`).
- Posting a `ServiceRequest` with an incorrect `code.coding.code` (e.g., using the lab LOINC instead of the medication NDC).

## Recommended Patterns
**Pattern 1: fetch and evaluate the lab**
1. `GET {base}/Observation?code={labCode}&patient={mrn}`
2. From the first entry in the Bundle, read `entry[0].resource.valueQuantity.value` as a number.
3. Compare to the low‑threshold for that lab.
   - `K` low < 3.5
   - `MG` low < 1.5
   - (extendable for other labs).

**Pattern 2: order replacement when low**
```json
POST {base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "priority": "stat",
  "code": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<NDC_FROM_CONTEXT>" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "authoredOn": "<CURRENT_TIME>"
}
```

**Pattern 3: schedule follow‑up lab**
```json
POST {base}/ServiceRequest
{
  "resourceType": "ServiceRequest",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "code": { "coding": [{ "system": "http://loinc.org", "code": "<LOINC_FOR_LAB>" }] },
  "subject": { "reference": "Patient/<MRN>" },
  "occurrenceTiming": {
    "repeat": { "frequency": 1, "period": 1, "periodUnit": "d" },
    "code": { "text": "next day at 08:00" }
  },
  "authoredOn": "<CURRENT_TIME>"
}
```

**Pattern 4: final output**
- If a replacement was ordered, still return the numeric value (and date if needed):
  `FINISH([value, "<effectiveDateTime>"])`
- If the value is not low, simply return the value (or `-1` when no recent observation).

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, order replacement potassium (NDC 12345‑6789) and schedule a morning serum potassium test for the next day at 08:00."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
2. Extract `valueQuantity.value` → `3.2`.
3. `3.2 < 3.5` → low, so:
   - POST replacement `ServiceRequest` with NDC `12345-6789`.
   - POST follow‑up `ServiceRequest` with LOINC `2823-3` (serum potassium) and timing "next day at 08:00".
4. `FINISH([3.2, "2023-11-12T09:45:00+00:00"])`

**Correct output:** `FINISH([3.2, "2023-11-12T09:45:00+00:00"])`
**Wrong output:** `FINISH([3.2])` (no orders) or `FINISH(["Potassium is low"] )` (wrong format).

## Success Indicators
- A `POST /ServiceRequest` appears for the replacement medication **and** another `POST` for the follow‑up lab when the value is below the threshold.
- `FINISH` returns a numeric array (and optional date) rather than a string.

## Failure Indicators
- Only the numeric value is returned and no `POST` requests are made despite the value being low.
- The replacement `ServiceRequest` uses the lab LOINC code instead of the medication NDC.
- The follow‑up lab request is missing or has an incorrect timing.
