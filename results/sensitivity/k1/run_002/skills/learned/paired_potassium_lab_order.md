---
description: "Always create a next\u2011day serum potassium lab request paired with\
  \ the potassium management decision."
name: paired_potassium_lab_order
provenance:
  action: ADD
  epoch: 0
  fixes: 0
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task4_26
  - task9_28
  - task2_9
  - task5_17
  - task3_10
  - task9_3
  - task4_23
  - task9_27
  - task2_15
  - task2_6
  update_cycle: 1
tags:
- paired_order
- potassium
- lab_request
version: 1
---

# Paired Serum Potassium Lab Order

## Pattern Description
You must always generate a follow‑up serum potassium **ServiceRequest** when a task asks to "check potassium and pair the order with a morning serum potassium level". The lab order is required **regardless of the current potassium value** – even if the level is normal and no replacement medication is ordered. The request should be scheduled for the next calendar day at 08:00 local time.

## When to Use This Skill
- Task description contains the phrase *"pair this order with a morning serum potassium level"*.
- After you have retrieved the most recent potassium Observation (code `K`).
- Whether you decide to order replacement potassium or not, a paired lab order must be created.

## Common Failure Patterns
- No ServiceRequest is POSTed for the repeat potassium lab.
- The lab order is created but the `occurrenceDateTime` is missing or set to the current time instead of next‑day 08:00.
- The wrong LOINC code is used (e.g., using the observation code `K` instead of the lab code `2823-3`).
- The lab order is omitted when the potassium level is normal.

## Recommended Patterns
**Pattern 1: Determine next‑day 08:00 timestamp**
```python
from datetime import datetime, timedelta
now = datetime.fromisoformat(context_time)  # e.g., "2023-11-13T10:15:00+00:00"
next_day = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
occurrence = next_day.isoformat()
```

**Pattern 2: Build the ServiceRequest body**
```json
{
  "resourceType": "ServiceRequest",
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "2823-3",
      "display": "Serum potassium"
    }]
  },
  "authoredOn": "{{now_iso}}",
  "occurrenceDateTime": "{{occurrence}}",
  "status": "active",
  "intent": "order",
  "priority": "routine",
  "subject": { "reference": "Patient/{{patient_id}}" },
  "note": [{ "text": "Paired repeat potassium lab as requested." }]
}
```
Replace `{{now_iso}}` with the current timestamp and `{{patient_id}}` with the MRN.

**Pattern 3: POST the request**
```
POST http://localhost:8080/fhir/ServiceRequest
{...body from Pattern 2...}
```
If the POST fails, retry once and log the error.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium ... Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=K&patient=S3228213`.
2. Extract the most recent value from `entry[0].resource.valueQuantity.value` and compare to the 3.5 mmol/L threshold.
3. If value < 3.5, POST a replacement potassium MedicationRequest (outside this skill).
4. **Regardless of step 3**, compute `occurrenceDateTime` for next day 08:00.
5. POST the ServiceRequest body from Pattern 2 with the computed timestamps.
6. FINISH with a summary that includes both the potassium assessment and confirmation that the paired lab order was placed.

**CORRECT output example:**
```
FINISH(["Potassium 3.2 mmol/L → replacement ordered. Paired serum potassium lab scheduled for 2023-11-14T08:00:00+00:00."])
```
**WRONG output example:**
```
FINISH(["Potassium 3.2 mmol/L → replacement ordered. No follow‑up lab needed."])
```

## Success Indicators
- A POST to `/fhir/ServiceRequest` is observed with `code.coding[0].code == "2823-3"`.
- The `occurrenceDateTime` field equals *next day at 08:00*.
- The final FINISH message mentions that a "paired serum potassium lab" was scheduled.

## Failure Indicators
- No ServiceRequest POST appears after the potassium check.
- The POST uses the wrong LOINC code or omits `occurrenceDateTime`.
- The FINISH output does not reference a paired lab order.
