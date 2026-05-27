---
description: Require age answer be returned as a JSON array, not a raw number
name: ensure_patient_query_for_age
provenance:
  action: MODIFY
  epoch: 4
  fixes: 8
  parent_version: 1
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - task2_1
  - task2_16
  - task8_5
  - task10_24
  - task10_20
  - task2_6
  update_cycle: 0
tags: []
version: 2
---

# ensure_patient_query_for_age

## Pattern Description
You must ensure that any task asking for a patient’s age (identified by MRN) returns the age wrapped in a JSON array. The skill already enforces a Patient GET before the calculation; this edit adds the final‑output rule so the agent never emits a bare number.

## When to Use This Skill
- When the task description explicitly asks for the patient’s age and mentions the answer should be an integer (e.g., "What's the age of the patient with MRN of S12345?").
- When the task context includes a current timestamp for rounding down the age.

## Common Failure Patterns
- `FINISH(60)` – raw number, no array brackets.
- `FINISH(["60"])` – string inside array, not a numeric value.
- Omitting the `FINISH` wrapper entirely.

## Recommended Patterns
**Pattern 1: core extraction and calculation**
1. Issue `GET {api_base}/Patient?identifier={MRN}`.
2. From the returned Bundle, locate the first entry’s `resource.birthDate`.
3. Compute the age by subtracting the birth year from the current year (round down).
4. Ensure the result is a plain integer (no quotes).

**Pattern 2: output formatting rule**
- **Correct:** `FINISH([age])` where `age` is an integer, e.g., `FINISH([60])`.
- **Wrong:** `FINISH(age)` (no brackets) or `FINISH(["age"])` (string inside array).

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Extract `birthDate` (e.g., `1963-01-29`).
3. Current time is `2023-11-13`; compute `2023 - 1963 = 60`.
4. Output `FINISH([60])`.

**Correct output:** `FINISH([60])`
**Wrong output:** `FINISH(60)`

## Success Indicators
- The agent performs a Patient GET before any age calculation.
- The final `FINISH` call contains a single‑element JSON array with an integer.

## Failure Indicators
- The `FINISH` call contains a raw number or a quoted string.
- No Patient GET is observed before the age extraction.
