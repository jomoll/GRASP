---
description: Add conditional ordering logic based on Observation value thresholds
  and result dates
name: action_generation_from_reasoning
provenance:
  action: MODIFY
  epoch: 3
  fixes: 12
  parent_version: 2
  probe_score: 8
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task8_5
  - task10_24
  - task9_5
  - task10_21
  - task3_30
  - task10_20
  - task3_27
  - task10_13
  - task10_17
  update_cycle: 0
tags:
- conditional-ordering
- observation-evaluation
- lab-reorder
version: 3
---

# Conditional Ordering Based on Observation Value and Date

## Pattern Description
You must evaluate the most recent Observation before deciding whether to create a new ServiceRequest.  This pattern applies whenever a task asks to *order a replacement medication if the lab value is low* or to *order a repeat lab only if the existing result is older than a given interval*.  By extracting both the numeric result and its `effectiveDateTime`, you can apply threshold or age checks and generate orders only when the condition truly warrants it.

## When to Use This Skill
- When the instruction says *"if low, then order replacement ..."* (e.g., potassium, magnesium, calcium).
- When the instruction says *"if the lab result date is greater than X, order a new test"* (e.g., HbA1c older than 1 year).
- When the task includes a follow‑up lab request that should be paired with the replacement order.

## Common Failure Patterns
- The agent returns `FINISH([value])` without creating the required ServiceRequest.
- The agent creates a ServiceRequest unconditionally, even when the result is within normal range or recent.
- The agent extracts only the numeric value and ignores `effectiveDateTime`, so it cannot evaluate age.

## Recommended Patterns
**Pattern 1: Extract value and timestamp**
1. `GET {base}/Observation?code={code}&patient={MRN}` (add `date=ge{now-1y}` only when a date check is required).
2. From the first entry in the Bundle, read:
   - `valueQuantity.value` **or** `valueString` (strip non‑numeric characters) → `obs_value`.
   - `effectiveDateTime` → `obs_date` (ISO‑8601).
3. Convert `obs_date` to a datetime object for comparison.

**Pattern 2: Apply low‑value threshold**
- Define low thresholds (example values, adjust per clinical policy):
  - Potassium (`K`): `< 3.5`
  - Magnesium (`MG`): `< 1.5`
  - Calcium (`CA`): `< 8.5`
- If `obs_value` meets the low‑value condition, proceed to Pattern 3.
- Otherwise, `FINISH([obs_value])` (or include the date if requested).

**Pattern 3: Apply age‑based re‑order rule**
- Compute `age_days = now - obs_date`.
- If `age_days > 365` (or the interval specified in the task), the result is considered stale.
- Only when the age condition is true should you create a new ServiceRequest.

**Pattern 4: Construct the ServiceRequest**
- Build a JSON body with:
  ```json
  {
    "resourceType": "ServiceRequest",
    "code": { "coding": [{ "system": "http://loinc.org", "code": "{order_loinc}", "display": "{order_display}" }] },
    "status": "active",
    "intent": "order",
    "priority": "stat",
    "authoredOn": "{now_iso}",
    "subject": { "reference": "Patient/{MRN}" },
    "note": { "text": "{optional_note}" },
    "occurrenceDateTime": "{optional_schedule}" 
  }
  ```
- For electrolyte replacement, use the NDC‑based medication code supplied in the task context.
- For a paired follow‑up lab (e.g., morning potassium), add `occurrenceDateTime` set to `now + 1 day` at `08:00`.
- POST to `{base}/ServiceRequest` and then `FINISH([obs_value])` (or include the date as required).

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium. Also schedule a morning serum potassium level for tomorrow at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3241217`
2. Extract `valueQuantity.value = 3.2` and `effectiveDateTime = 2023-11-10T09:00:00+00:00`.
3. Compare: `3.2 < 3.5` → low, so continue.
4. Build replacement order (use NDC from task context) and schedule follow‑up:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://ndc.org","code":"{NDC}","display":"Potassium chloride"}]},
     "status":"active","intent":"order","priority":"stat",
     "authoredOn":"2023-11-13T10:15:00+00:00",
     "subject":{"reference":"Patient/S3241217"},
     "note":{"text":"Replacement potassium ordered due to low level (3.2 mmol/L)."},
     "occurrenceDateTime":"2023-11-14T08:00:00+00:00"
   }
   ```
5. `POST` the ServiceRequest, then `FINISH([3.2])`.

**Task:** "If the last HbA1c is older than 1 year, order a new test."
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6500497`
2. Extract `valueQuantity.value = 5.2` and `effectiveDateTime = 2022-08-09T12:00:00+00:00`.
3. Compute age: >365 days → stale.
4. Build ServiceRequest with LOINC 4548‑4 and POST.
5. `FINISH([5.2, "2022-08-09"])`.

## Success Indicators
- The agent posts a ServiceRequest **only** when the low‑value or stale‑date condition is true.
- The posted ServiceRequest contains the correct `code`, `subject.reference`, `authoredOn`, and optional `occurrenceDateTime`.
- The final `FINISH` output includes the numeric value (and date if requested) and no superfluous text.

## Failure Indicators
- A ServiceRequest is posted when the observation is within normal range.
- No ServiceRequest is posted even though the low‑value or stale‑date condition is met.
- The posted ServiceRequest is missing required fields (e.g., `subject.reference` or `code`).
- The agent returns a free‑text answer instead of the numeric array.
