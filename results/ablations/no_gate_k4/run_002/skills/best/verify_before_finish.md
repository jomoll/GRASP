---
description: "Require FINISH to echo free\u2011text notes from ServiceRequest orders"
name: verify_before_finish
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 6
  triggering_sample_ids:
  - task9_9
  - task10_15
  - task1_7
  - task4_21
  - task4_10
  - task10_16
  - task2_6
  - task4_26
  - task2_26
  - task4_11
  update_cycle: 1
tags: []
version: 7
---

# Verify ServiceRequest Note Inclusion

## Pattern Description
When you create a `ServiceRequest` that contains a `note.text` element, you must reflect that free‑text note in the final `FINISH` output. This guarantees that downstream consumers see the clinical rationale that was required by the task description. Omitting the note leads to `verify_before_finish` failures.

## When to Use This Skill
- After a `POST /ServiceRequest` that includes a `note` object.
- The task explicitly asks for specific wording inside the referral or order note.
- Before calling `FINISH` for any task that involved an order with a note.

## Common Failure Patterns
- `FINISH(["orthopedic surgery referral ordered"])` – note text missing.
- Returning only the note without confirming the order succeeded.
- Using a different key (e.g., `description`) instead of `note.text`.

## Recommended Patterns
**Pattern 1: Capture and echo note**
1. After the POST, store the exact string sent in `note.text` (e.g., `capturedNote`).
2. Verify the POST response indicates success (status 201 or equivalent).
3. Call `FINISH(["<order confirmation>", capturedNote])`.

   **CORRECT**: `FINISH(["orthopedic surgery referral ordered", "Situation: acute left knee injury, ..."] )`
   **WRONG**: `FINISH(["orthopedic surgery referral ordered"])`

**Pattern 2: Fallback when note is empty**
- If `note.text` is empty or not provided, simply confirm the order without a second element.

**Pattern 3: Validation before finish**
- Ensure the FINISH array length is 2 when a note was sent, and that the second element exactly matches the original note string.

## Example Application
**Task:** Order orthopedic surgery referral for patient S3241217 with a detailed free‑text note.

**Step‑by‑step:**
1. `POST /ServiceRequest` with `note.text = "Situation: acute left knee injury, ..."`.
2. Receive successful POST acknowledgment.
3. Store the note string.
4. `FINISH(["orthopedic surgery referral ordered for patient S3241217", "Situation: acute left knee injury, ..."])`.

**CORRECT output:** `FINISH(["orthopedic surgery referral ordered for patient S3241217", "Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations."])`
**WRONG output:** `FINISH(["orthopedic surgery referral ordered for patient S3241217"])`

## Success Indicators
- FINISH contains two elements: a concise confirmation and the exact note text.
- The note text matches character‑for‑character what was sent in the POST.
- No extra whitespace or formatting changes are introduced.

## Failure Indicators
- FINISH has only one element despite a note being present.
- The note element is altered, truncated, or missing.
- The order confirmation string is absent or malformed.
