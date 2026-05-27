---
description: "Calculate a patient\u2019s age from MRN by extracting birthDate and\
  \ using the task\u2019s current time"
name: compute_patient_age
provenance:
  action: ADD
  epoch: 0
  fixes: 13
  probe_score: 8
  regressions: 1
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task3_14
  - task4_11
  update_cycle: 0
tags: []
version: 1
---

# Compute Patient Age from MRN

## Pattern Description
You must determine a patient’s age when a task asks for it by MRN (Medical Record Number). The reusable pattern is: fetch the Patient resource, extract the `birthDate` field, compute the difference in whole years between the task’s `current time` (provided in the task context) and the birth date, and return the integer age. If the patient cannot be found, answer "Patient not found".

## When to Use This Skill
- When the instruction is *"What’s the age of the patient with MRN of <MRN>?"*.
- When the task context includes a `current time` timestamp (e.g., `2023-11-13T10:15:00+00:00`).
- When the agent has already performed a `GET /Patient?identifier=<MRN>` request.

## Common Failure Patterns
- Returning a hard‑coded number without parsing the `birthDate`.
- Using the `id` or other field as the age.
- Forgetting to round down to the nearest whole year.
- Not handling the case where the search returns `total: 0` (patient not found).

## Recommended Patterns
**Pattern 1: Core age‑calculation workflow**
1. **GET the patient**: `GET {api_base}/Patient?identifier=<MRN>`.
2. Verify the response bundle:
   - `total` must be `1`.
   - The patient resource is at `entry[0].resource`.
3. Extract `birthDate` (e.g., `"1975-04-22"`).
4. Parse the task’s `current time` from the instruction context (ISO‑8601 string).
5. Compute the year difference:
   ```
   age = floor((current_time - birthDate) / 365.2425 days)
   ```
6. **FINISH** with a JSON array containing the integer age: `FINISH([<age>])`.

**Pattern 2: Fallback when patient not found**
- If `total` is `0`, call `FINISH(["Patient not found"])`.

**Pattern 3: Output formatting**
- The final output must be a JSON array with a single integer (or the string "Patient not found").
- Do **not** include any explanatory text, units, or extra brackets.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
2. Response bundle shows `total: 1` and `birthDate: "1948-06-15"`.
3. Task context provides `current time: 2023-11-13T10:15:00+00:00`.
4. Compute age: from 1948‑06‑15 to 2023‑11‑13 is 75 years (rounded down).
5. `FINISH([75])`

**CORRECT output:** `FINISH([75])`
**WRONG output:** `FINISH(["75 years"])` or `FINISH(["Patient age is 75"])`

## Success Indicators
- The agent returns a single integer inside a JSON array.
- The integer matches the calendar‑year difference between the provided `current time` and the patient’s `birthDate`.
- When the patient does not exist, the agent returns `"Patient not found"`.

## Failure Indicators
- Output contains text, units, or extra punctuation.
- Age is off by one year because the birthday has not yet occurred in the current year.
- The agent returns a placeholder or static value without performing the calculation.
- No check for `total: 0` leading to a crash or incorrect answer.
