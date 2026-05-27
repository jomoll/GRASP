---
description: Enforce that ServiceRequest.note is an array of Annotation objects
name: require_service_request_note_array
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 2
  fixes_unused: 14
  probe_score_unused: -3
  regressions_unused: 5
  triggering_sample_ids:
  - task10_13
  - task8_26
  - task10_18
  - task8_13
  - task9_3
  - task8_21
  - task10_27
  - task10_15
  update_cycle: 1
tags:
- FHIR
- ServiceRequest
- note
- array
version: 1
---

# ServiceRequest Note Array Requirement

## Pattern Description
You must always represent the `note` element of a `ServiceRequest` as a JSON array of Annotation objects, even when there is only a single free‑text note. The FHIR specification defines `ServiceRequest.note` as a repeatable element, and sending it as a solitary object leads to validation warnings and potential storage failures. By consistently using an array, the agent produces compliant resources and avoids the "service_request_note_not_array" failure mode.

## When to Use This Skill
- When constructing a **ServiceRequest** (or any resource that includes a `note` field) that contains free‑text commentary.
- When the task explicitly asks to embed a paragraph of text inside the referral, order, or any other request.
- Whenever you see a requirement like "Specify within the free text of the referral...".

## Common Failure Patterns
- `"note": { "text": "..." }` – note is an object, not an array.
- Omitting the `note` field entirely when a note is required.
- Providing `note` as a string directly (e.g., `"note": "..."`).
- Supplying multiple notes but still using a single object (e.g., `"note": { "text": "First" , "text2": "Second" }`).

## Recommended Patterns
**Pattern 1: Single note**
```json
"note": [
  {
    "text": "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."
  }
]
```
**Pattern 2: Multiple notes**
```json
"note": [
  { "text": "First note content" },
  { "text": "Second note content" }
]
```
**Pattern 3: Fallback verification**
- After building the POST body, inspect the `note` field.
- If `note` is not an array, wrap the existing object in an array.
- If `note` is missing but the task mentions free‑text, raise a warning and add an empty array placeholder.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6547257. Specify within the free text of the referral, \"Situation: acute left knee injury, ...\""

**Step‑by‑step:**
1. Retrieve the patient with `GET /Patient?identifier=S6547257`.
2. Build the ServiceRequest payload.
3. Insert the free‑text into the `note` element **as an array**:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "306181000000106", "display": "Orthopedic surgery referral" }] },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/S6547257" },
     "note": [
       { "text": "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations." }
     ]
   }
   ```
4. POST the payload to `/ServiceRequest`.
5. Call `FINISH([...])` with the appropriate answer.

**CORRECT output:** `FINISH(["Referral created"])`
**WRONG output:** `FINISH([])` with a POST body where `note` is an object.

## Success Indicators
- The POST body contains `"note": [ { "text": "..." } ]`.
- The system log shows no "ServiceRequest POST accepted but resource not found" warning related to note structure.
- The agent proceeds to `FINISH` with the expected answer.

## Failure Indicators
- The POST body shows `"note": { "text": "..." }` (object instead of array).
- System note warns: "ServiceRequest POST accepted but resource not found on retrieval – may not have been stored correctly."
- The agent finishes with an empty array or incorrect answer because the resource was rejected.
