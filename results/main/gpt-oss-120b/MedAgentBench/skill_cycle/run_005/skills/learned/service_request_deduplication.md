---
description: "Avoid creating a second identical ServiceRequest for the same patient,\
  \ code, and free\u2011text note"
name: service_request_deduplication
provenance:
  action: ADD
  epoch: 4
  fixes: 11
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - task9_14
  - task1_13
  - task10_20
  - task9_20
  - task8_26
  - task1_23
  - task8_19
  - task1_27
  - task1_10
  - task1_20
  update_cycle: 0
tags:
- deduplication
- service-request
- order
version: 1
---

# Service Request Deduplication

## Pattern Description
You must ensure that a ServiceRequest is only created when no existing active request matches the same patient, service code, and free‑text note. Duplicate ServiceRequests cause downstream ordering errors and waste resources. The pattern is to perform a pre‑flight search for an identical request and skip the POST if one is found, otherwise create the request.

## When to Use This Skill
- When the task is to **order a ServiceRequest** (e.g., orthopedic referral, lab order) and the instruction includes a specific free‑text note.
- The agent is about to `POST` a `ServiceRequest` resource.
- The same patient may already have an active request with the same `code.coding[0].code` and identical `note.text`.

## Common Failure Patterns
- Two consecutive `POST /ServiceRequest` calls with identical payloads.
- No `GET` search for existing ServiceRequests before posting.
- Using a different JSON shape for `note` (object vs array) but same content, still creates a duplicate.
- Ignoring the `status` field; a completed request is still considered a duplicate if the intent is the same.

## Recommended Patterns
**Pattern 1: pre‑flight deduplication check**
1. Construct a GET query to search for existing ServiceRequests:
   ```
   GET {base}/ServiceRequest?subject=Patient/{MRN}&code={code}&_status=active,completed
   ```
   - `subject` = `Patient/{identifier}`
   - `code` = the exact SNOMED/LOINC code used in the new request.
2. Inspect the returned Bundle:
   - If `total > 0`, iterate entries and compare `note.text` (normalize whitespace).
   - If any entry has `note.text` exactly matching the new request's note, **skip the POST** and go directly to `FINISH` with the note text.
3. If no matching entry is found, proceed to POST the ServiceRequest.

**Pattern 2: consistent note representation**
- Always send `note` as a **single object** with a `text` field (not an array) to simplify comparison.
- Example CORRECT note payload:
  ```json
  "note": { "text": "Situation: ... Recommendation: ..." }
  ```
- WRONG payload (array) leads to mismatched comparison:
  ```json
  "note": [{ "text": "..." }]
  ```

**Pattern 3: post‑creation verification**
- After a successful POST, optionally re‑GET the created resource by its `id` to confirm it was stored.
- If the GET fails, log a warning but do not attempt a second POST.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S3241217 with free‑text note …"

**Step‑by‑step:**
1. Extract patient MRN (`S3241217`) and note text.
2. Build GET URL:
   ```
   GET http://localhost:8080/fhir/ServiceRequest?subject=Patient/S3241217&code=306181000000106&_status=active,completed
   ```
3. If the response Bundle `total` is 0, POST:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "306181000000106", "display": "Orthopedic surgery referral" }] },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/S3241217" },
     "note": { "text": "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations." }
   }
   ```
4. If a matching entry is found, skip POST and directly:
   ```
   FINISH(["Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."])
   ```

## Success Indicators
- Only one `POST /ServiceRequest` is issued for a given patient/code/note combination.
- The agent logs a deduplication check before posting.
- `FINISH` is called with the note text even when the request is skipped.

## Failure Indicators
- Two `POST /ServiceRequest` calls with identical payloads appear in the trace.
- The agent does not perform a GET search before posting.
- The note is sent as an array, causing the deduplication comparison to miss an existing request.
