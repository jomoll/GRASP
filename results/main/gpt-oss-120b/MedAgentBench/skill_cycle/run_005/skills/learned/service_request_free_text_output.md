---
description: "Ensure FINISH returns the required free\u2011text note when ordering\
  \ a ServiceRequest that demands a referral text."
name: service_request_free_text_output
provenance:
  action: ADD
  epoch: 3
  fixes: 13
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task5_7
  - task9_28
  - task8_26
  - task9_6
  - task10_18
  - task10_24
  update_cycle: 0
tags:
- order
- servicerequest
- free_text
- mandatory_output
version: 1
---

# ServiceRequest Order with Mandatory Free‑Text Output

## Pattern Description
You must guarantee that any task which asks you to *order* a `ServiceRequest` (e.g., a referral) **and** explicitly says to *"Specify within the free text of the referral"* returns that free‑text string as the final answer. The capability is reusable for any `ServiceRequest` that carries a `note.text` payload, not just orthopaedic referrals.

## When to Use This Skill
- When the instruction contains the phrase **"Specify within the free text"** (or synonyms like *"include the following text"*) while creating a `ServiceRequest`.
- When the `ServiceRequest` payload you build includes a `note` (either an object with `text` or an array of objects with `text`).
- After you have successfully POSTed the `ServiceRequest` and received confirmation, you must still produce a non‑empty `FINISH` output.

## Common Failure Patterns
- `FINISH([])` – the agent posts the request but returns an empty answer array.
- The free‑text is placed in `note` but never echoed back to the user.
- Using `note` as an array vs. object inconsistently, causing downstream validation to miss the text.
- Forgetting to wrap the free‑text in an array when calling `FINISH` (e.g., `FINISH("text")`).

## Recommended Patterns
**Pattern 1: Capture and embed the required free‑text**
1. Parse the instruction to extract the exact free‑text string that follows the phrase *"Specify within the free text of the referral"* (or similar).
2. Build the `ServiceRequest` JSON:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "...", "display": "..." }] },
     "authoredOn": "2023-11-13T10:15:00+00:00",
     "status": "active",
     "intent": "order",
     "priority": "stat",
     "subject": { "reference": "Patient/<MRN>" },
     "note": { "text": "<EXTRACTED_FREE_TEXT>" }
   }
   ```
3. POST the `ServiceRequest`.
4. Immediately call `FINISH(["<EXTRACTED_FREE_TEXT>"])`.

**Pattern 2: Consistent `note` structure**
- Prefer the object form `{ "note": { "text": "..." } }` for simplicity; if the API requires an array, use `"note": [{ "text": "..." }]`.
- Verify the note field exists before finishing.

**Pattern 3: Verification fallback**
- If the POST response does not confirm success, retry the POST before calling `FINISH`.
- If the free‑text cannot be parsed, abort with a clear error rather than returning an empty array.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S123456. Specify within the free text of the referral, \"Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations.\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S123456`
2. Extract the quoted free‑text after *"Specify within the free text of the referral"*.
3. POST `ServiceRequest` with `note.text` set to the extracted string.
4. `FINISH(["Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."])`

## Success Indicators
- The final `FINISH` call returns an array containing exactly the free‑text required by the instruction.
- The `ServiceRequest` POST includes a correctly‑structured `note` field.

## Failure Indicators
- `FINISH` returns an empty array or a value that does not match the required free‑text.
- The `note` field is missing or malformed, leading to the downstream check failing.
- The agent posts the request but never calls `FINISH` with the extracted text.
