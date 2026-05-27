---
description: Include ServiceRequest note text in FINISH when a referral order is created
name: order_confirmation_output
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 2
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
tags: []
version: 3
---

# Order Confirmation Output (Enhanced)

## Pattern Description
When the agent creates a `ServiceRequest` (e.g., an orthopedic surgery referral) you must return a concise confirmation **and** surface any free‑text `note.text` that was part of the request, if present. The original skill suppressed the note, leading to the "referral_note_not_returned" failure. This enhanced pattern keeps the short confirmation for readability while still providing the note for downstream consumers.

## When to Use This Skill
- After a successful `POST /ServiceRequest` that includes a `note` element.
- When the task description expects the referral note to be echoed back (e.g., “Specify within the free text of the referral …”).
- For any other order types where a note is supplied and the caller may need it.

## Common Failure Patterns
- `FINISH(["Orthopedic surgery referral order created for patient S2863714."])` – note omitted.
- Returning only the note without a confirmation message.
- Mixing note text with unrelated data in the same array element.

## Recommended Patterns
**Pattern 1: Core confirmation with optional note**
1. After the POST succeeds, capture the request payload’s `note.text` (if it exists).
2. Build the confirmation string:
   ```text
   Orthopedic surgery referral order created for patient <MRN>.
   ```
3. If a note was supplied, append a second array element containing the note text **exactly** as provided.
   - **CORRECT**:
     ```
     FINISH([
       "Orthopedic surgery referral order created for patient S2863714.",
       "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."
     ])
     ```
   - **WRONG**: Only the first element, or a combined string that merges confirmation and note.

**Pattern 2: Fallback when no note is present**
- Return a single‑element array with just the confirmation string.

**Pattern 3: Formatting rule**
- Preserve the original whitespace and punctuation of the note; do not add extra quotes or escape characters beyond JSON string encoding.

## Example Application
**Task:** Order orthopedic surgery referral for patient S1023381 with a detailed note.

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S1023381` – confirm patient exists.
2. `POST http://localhost:8080/fhir/ServiceRequest` with the `note.text` payload.
3. On success, extract the note text from the request payload.
4. Call:
   ```
   FINISH([
     "Orthopedic surgery referral order created for patient S1023381.",
     "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."
   ])
   ```

**CORRECT output:** Two‑element array with confirmation and note.
**WRONG output:** Single‑element array without the note.

## Success Indicators
- `FINISH` returns an array of length 2 when a note was supplied.
- The second element matches the exact `note.text` from the ServiceRequest payload.
- Tests that verify the presence of the note pass.

## Failure Indicators
- Only one array element is returned despite a note being present.
- The note text is altered, truncated, or omitted.
- The confirmation message is missing or malformed.
