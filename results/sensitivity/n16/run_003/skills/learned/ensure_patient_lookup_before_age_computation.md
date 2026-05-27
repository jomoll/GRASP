---
description: "Guarantee a Patient GET lookup and correct age calculation for MRN\u2011\
  based age queries"
name: ensure_patient_lookup_before_age_computation
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task4_28
  - task9_28
  - task4_15
  - task9_22
  - task4_23
  - task2_25
  - task10_10
  - task2_28
  update_cycle: 0
tags: []
version: 1
---

# Ensure Patient Lookup Before Age Computation

## Pattern Description
You must always retrieve the patient resource before trying to compute an age. The MRN is an identifier, not the FHIR resource ID, so a direct lookup (`GET /Patient?identifier=MRN`) is required. After obtaining the `birthDate` field you can calculate the age relative to the task‑provided current time, rounding down to an integer. This pattern prevents "answer_not_generated" failures caused by missing patient data.

## When to Use This Skill
- When the task asks *"What's the age of the patient with MRN of X?"* (or any variant that requires age from an identifier).
- When the task provides a reference time (e.g., "It's 2023-11-13T10:15:00+00:00 now").
- When the MRN is the only piece of patient information supplied.

## Common Failure Patterns
- No `GET /Patient` request is issued before attempting to compute age.
- Agent tries to compute age from the MRN string itself.
- Agent extracts `birthDate` from a previously cached response that may not exist.
- FINISH is called with an empty payload or a textual explanation instead of an integer.

## Recommended Patterns
**Pattern 1: Core lookup and age calculation**
1. Issue `GET {api_base}/Patient?identifier={MRN}`.
2. If the response `Bundle.total == 0`, FINISH(["Patient not found"]).
3. From the first entry, read `entry[0].resource.birthDate` (ISO‑date string).
4. Parse the task‑provided current time (or use system time if not given).
5. Compute `age = floor((currentDate - birthDate) / 365.25 days)`.
6. FINISH([age]) – the payload must be a JSON array containing a single integer.

**Pattern 2: Fallback when birthDate missing**
- If `birthDate` field is absent, FINISH(["Patient birthdate unavailable"]).

**Pattern 3: Output formatting**
- ALWAYS return a JSON array with a single numeric element, e.g. `FINISH([76])`.
- Do NOT wrap the number in a string or add explanatory text.

## Example Application
**Task:** "What's the age of the patient with MRN of S0611496?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S0611496`
2. Response contains `birthDate: "1947-11-13"`.
3. Task context gives current time `2023-11-13T10:15:00+00:00`.
4. Compute age: 2023‑1947 = 76 (rounded down).
5. `FINISH([76])`

**Correct output:** `FINISH([76])`
**Incorrect output:** `FINISH(["Patient is 76 years old"])`

## Success Indicators
- A `GET /Patient` request appears in the action log before any FINISH.
- The FINISH payload is a JSON array with a single integer.
- The integer matches the expected age based on the supplied current time.

## Failure Indicators
- No GET request for the patient identifier is observed.
- FINISH payload contains text, a list of strings, or an empty array.
- The returned number is off by more than one year (indicating wrong date arithmetic).
