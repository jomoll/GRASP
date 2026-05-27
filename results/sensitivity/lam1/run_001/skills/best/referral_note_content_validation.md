---
description: "Validate that a ServiceRequest referral note contains the required structured\
  \ free\u2011text sections"
name: referral_note_content_validation
provenance:
  action: ADD
  epoch: 3
  fixes: 5
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task9_9
  - task8_19
  - task9_28
  - task5_17
  - task9_3
  - task4_28
  - task9_14
  - task5_16
  - task9_6
  - task9_20
  update_cycle: 1
tags: []
version: 1
---

# Referral Note Content Validation

## Pattern Description
You must ensure that any `ServiceRequest` representing a referral includes a free‑text `note.text` that follows the exact structured template required by the task. The note should contain the four sections **Situation**, **Background**, **Assessment**, and **Recommendation** in that order, each beginning with the exact keyword followed by a colon (e.g., `Situation:`). This pattern prevents downstream reviewers from receiving incomplete or malformed referral narratives.

## When to Use This Skill
- The task description contains phrases like *"Specify within the free text of the referral"* or *"include the following free‑text"*.
- You are about to issue a `POST /ServiceRequest` whose `code.coding.display` or `code.coding.code` indicates a referral (e.g., contains the word *referral* or a known SNOMED referral code).
- The request body includes a `note` element with a `text` field.

## Common Failure Patterns
- `note.text` is missing one or more required sections (e.g., only `Situation:` present).
- Section headings are misspelled or lack the trailing colon (`Situation` instead of `Situation:`).
- Sections appear out of order or are concatenated without clear separation.
- The final `FINISH` payload is a generic success message (e.g., `"Referral created"`) without confirming that the note met the specification.

## Recommended Patterns
**Pattern 1: Verify required sections before POST**
1. Extract the string from `note.text`.
2. Define the ordered list `required = ["Situation:", "Background:", "Assessment:", "Recommendation:"]`.
3. For each element in `required`, check that the note contains the exact substring followed by a space or end‑of‑string.
4. Ensure the index of each required substring is increasing (preserves order).
5. If any check fails, abort the POST and `FINISH(["Referral note missing required section: <section>"])`.

**Pattern 2: Auto‑complete missing sections (optional fallback)**
- If the note is present but a section is missing, you may append a placeholder like `"<section> not provided"` before posting, then include a warning in the `FINISH` payload.

**Pattern 3: Post‑creation verification**
- After a successful POST, retrieve the created `ServiceRequest` (if the API supports a read) and re‑check the stored `note.text` to confirm it matches the required pattern. If it does not, log a warning and `FINISH(["Referral note stored incorrectly"])`.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6530813. Specify within the free text of the referral, \"Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations.\""

**Step‑by‑step:**
1. Build the `ServiceRequest` JSON with the `note.text` exactly as shown.
2. Run the verification loop from Pattern 1 – all four headings are present and in order.
3. Proceed with `POST /ServiceRequest`.
4. Optionally retrieve the created resource and re‑run the check (Pattern 3).
5. `FINISH(["Referral created with validated note"])`.

**Correct note:**
```
Situation: acute left knee injury, Background: radiology report indicates ACL tear. Assessment: ACL tear grade II. Recommendation: request for Orthopedic service to evaluate and provide management recommendations.
```
**Incorrect note example:**
```
Background: radiology report indicates ACL tear. Situation: acute left knee injury, Assessment: ACL tear grade II. Recommendation: request for Orthopedic service.
```
The above would trigger a failure because the order is wrong and `Situation:` is not first.

## Success Indicators
- The agent performs the section‑order check and proceeds to POST only when all checks pass.
- The final `FINISH` payload includes a message confirming note validation (e.g., `"Referral created with validated note"`).
- System logs show no warning about missing sections.

## Failure Indicators
- The agent posts a `ServiceRequest` without performing the section check.
- The `FINISH` payload is a generic success message without confirming note content.
- System note or log indicates the note was stored but did not contain all required sections.
