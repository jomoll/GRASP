---
description: "Create a ServiceRequest when a required lab result is missing, stale,\
  \ or a follow\u2011up lab is needed."
name: order_service_request_if_missing_or_stale
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task1_27
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task4_27
  - task5_7
  - task9_27
  update_cycle: 0
tags:
- ordering
- service_request
- lab
version: 1
---

# Order ServiceRequest When Result Is Missing, Stale, or Follow‑up Is Required

## Pattern Description
You must ensure that clinical workflows that depend on a lab result always have a valid ServiceRequest in place. When a GET /Observation returns no entries, or the most recent entry is older than a task‑specified freshness window, you must POST a ServiceRequest for the appropriate LOINC‑coded test. The same logic applies when a medication order includes a required follow‑up lab (e.g., a potassium replacement that must be re‑checked the next morning). This skill centralises the ordering decision, the construction of the ServiceRequest payload, and the verification that the request was sent.

## When to Use This Skill
- **Missing result**: `GET /Observation?code={LOINC}&patient={MRN}` returns `total: 0`.
- **Stale result**: The latest Observation’s `effectiveDateTime` is older than the task‑specified threshold (e.g., > 1 year for HbA1c, > 24 h for electrolytes).
- **Follow‑up lab required**: After posting a medication ServiceRequest, the task states a lab must be performed at a specific future time.
- **Any task that explicitly mentions ordering a lab when a condition is met**.

## Common Failure Patterns
- Returning only a FINISH string without creating a ServiceRequest.
- Using the wrong `code.coding.system` (should be `http://loinc.org` for labs).
- Omitting required fields: `status`, `intent`, `subject.reference`, `authoredOn`.
- Forgetting to set `occurrenceDateTime` for scheduled follow‑up labs.
- Posting the ServiceRequest but not checking the response before calling FINISH.

## Recommended Patterns
**Pattern 1: Detect missing or stale result**
1. Issue `GET {base}/Observation?code={LOINC}&patient={MRN}`.
2. If `total == 0`, treat as missing.
3. If `total > 0`, extract the entry with the greatest `effectiveDateTime`.
4. Parse the timestamp and compare to `now` (ISO‑8601). If the difference exceeds the task‑provided threshold, treat as stale.

**Pattern 2: Build the ServiceRequest payload**
```json
{
  "resourceType": "ServiceRequest",
  "code": {
    "coding": [{
      "system": "http://loinc.org",
      "code": "{LOINC}",
      "display": "{Lab display name}"
    }]
  },
  "status": "active",
  "intent": "order",
  "authoredOn": "{now}",
  "subject": { "reference": "Patient/{MRN}" },
  "note": { "text": "{optional free‑text from task}" }
}
```
- For a scheduled follow‑up lab, add `"occurrenceDateTime": "{scheduled_iso}"`.
- Use the exact LOINC code supplied in the task context (e.g., `4548-4` for HbA1c, `2823-3` for serum potassium).

**Pattern 3: POST and verify**
1. `POST {base}/ServiceRequest` with the payload above.
2. Wait for the server’s response. If the response status is not 201/200, raise an error and do **not** call FINISH.
3. After a successful POST, call `FINISH` with a concise confirmation string, e.g., `FINISH(["HbA1c order created for patient S1234567."])`.

## Example Application
**Task**: "What’s the last HbA1C value for patient S6550627 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step**:
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6550627`.
2. Response shows `total: 0` → missing result.
3. Build ServiceRequest payload using LOINC `4548-4` (HbA1c):
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": {"coding":[{"system":"http://loinc.org","code":"4548-4","display":"Hemoglobin A1c"}]},
     "status":"active",
     "intent":"order",
     "authoredOn":"2023-11-13T10:15:00+00:00",
     "subject":{"reference":"Patient/S6550627"}
   }
   ```
4. `POST http://localhost:8080/fhir/ServiceRequest` with the payload.
5. Verify POST succeeded, then `FINISH(["HbA1c order created for patient S6550627."])`.

## Success Indicators
- A ServiceRequest resource appears in the FHIR server for the correct patient and LOINC code.
- The FINISH output contains a short confirmation string, not a free‑text narrative.
- No subsequent task asks the same ordering question for the same patient.

## Failure Indicators
- FINISH is called without a preceding POST, or the POST response is ignored.
- The ServiceRequest payload is missing `code.coding.system` or uses an incorrect code system.
- The `occurrenceDateTime` is omitted when a future lab date is required.
- The confirmation string includes extraneous narrative (e.g., full lab value) instead of a concise order notice.

---
*Use this skill whenever a task requires you to ensure a lab order exists before answering.*
