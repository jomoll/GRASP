---
description: Ensures FINISH output for order tasks is a concise confirmation string,
  not a full sentence
name: enforce_short_confirmation_answer
provenance:
  action: ADD
  epoch: 2
  fixes: 2
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task8_7
  - task8_29
  - task9_27
  - task5_17
  - task9_8
  - task5_16
  - task9_11
  - task9_14
  - task5_7
  update_cycle: 0
tags:
- answer_format
- finishing
- confirmation
version: 1
---

# Enforce Short Confirmation Answer for FINISH

## Pattern Description
You must limit the FINISH payload for tasks that involve creating a FHIR resource (e.g., ServiceRequest, MedicationRequest, Observation) to a **single short confirmation string**. The answer should be a brief acknowledgment—typically the resource type and a verb—without explanatory clauses, punctuation, or extra wording. This keeps the response schema consistent and prevents the "answer_format_explanatory_sentence" failure.

## When to Use This Skill
- After a successful POST of any FHIR resource where the task only asks for confirmation (e.g., "Order orthopedic surgery referral").
- When the task description does **not** request a detailed report, just a confirmation of the action.
- Whenever you are about to call `FINISH` and the expected answer is a short acknowledgment rather than a narrative sentence.

## Common Failure Patterns
- `FINISH(["Referral order placed successfully"])` – full sentence, extra words.
- `FINISH(["Blood pressure recorded successfully."])` – contains period and unnecessary adjectives.
- `FINISH([])` – missing confirmation.
- `FINISH([-1])` – wrong data type.
- `FINISH(["Referral placed for patient S123"])` – more than three words.

## Recommended Patterns
**Pattern 1: Core short confirmation**
1. Verify the POST request succeeded (status 200/201).
2. Construct a confirmation string of **≤3 words**, capitalized, no punctuation.
   - CORRECT: `"Referral placed"`
   - CORRECT (including identifier): `"Referral S123 placed"`
   - WRONG: `"Referral order placed successfully"`
3. Call `FINISH([<confirmation_string>])`.

**Pattern 2: Fallback when identifier is unknown**
- Use only the resource type and verb: `"Referral placed"`.

**Pattern 3: Formatting rule**
- Do **not** add periods, commas, or explanatory clauses.
- The payload must be a JSON array containing exactly one string.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S3241217. ..."

**Step‑by‑step:**
1. `GET http://.../Patient?identifier=S3241217` – confirm patient exists.
2. `POST http://.../ServiceRequest { … }` – create the referral.
3. Verify POST success.
4. `FINISH(["Referral placed"])`.

**CORRECT output:** `FINISH(["Referral placed"])`
**WRONG output:** `FINISH(["Referral order placed successfully"])`

## Success Indicators
- The agent emits `FINISH` with an array of one short string (≤3 words, no punctuation).
- No explanatory sentence or extra wording appears in the FINISH payload.
- The response matches the task’s expectation for a simple acknowledgment.

## Failure Indicators
- FINISH payload contains a full sentence, period, or more than three words.
- FINISH payload is empty, contains a number, or uses the wrong JSON type.
- The answer includes patient identifiers when the task does not request them (unless explicitly needed).
