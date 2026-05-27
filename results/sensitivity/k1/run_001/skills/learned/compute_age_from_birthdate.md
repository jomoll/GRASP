---
description: "Derive a patient\u2019s age from the Patient.birthDate field using the\
  \ task\u2019s current time context"
name: compute_age_from_birthdate
provenance:
  action: ADD
  epoch: 2
  fixes: 7
  probe_score: 5
  regressions: 3
  triggering_sample_ids:
  - task2_1
  - task4_27
  - task8_26
  - task2_16
  - task5_19
  - task2_14
  - task4_20
  - task1_12
  - task1_20
  - task1_11
  update_cycle: 1
tags:
- age
- patient
- birthdate
version: 1
---

# Compute Age From Birthdate

## Pattern Description
You must calculate a patient’s age instead of using a hard‑coded placeholder. After a successful `GET /Patient?identifier=MRN` request, locate the `birthDate` element in the returned Patient resource. Use the `current time` supplied in the task context (e.g., `2023-11-13T10:15:00+00:00`) to compute the integer age rounded down (i.e., floor of the year difference, adjusting for whether the birthday has occurred yet this year). This pattern applies to any task that asks for the patient’s age.

## When to Use This Skill
- When the instruction explicitly asks for the **age** of a patient identified by MRN or other identifier.
- When the task context includes a `current time` value.
- After you have retrieved a Patient bundle and the bundle contains a `birthDate` field.

## Common Failure Patterns
- Returning a static number or placeholder instead of computing from `birthDate`.
- Using `effectiveDateTime` or `lastUpdated` instead of `birthDate` for age calculation.
- Ignoring the `current time` from the task context, leading to age that is off by a year.
- Failing to floor the result (e.g., returning a decimal or rounding up).

## Recommended Patterns
**Pattern 1: Core age computation**
1. Issue `GET {api_base}/Patient?identifier=MRN` (or appropriate search).
2. Parse the response JSON. Locate `entry[0].resource.birthDate` (ISO‑8601 date, e.g., `1978-04-22`).
3. Extract the `current time` string from the task context (e.g., `2023-11-13T10:15:00+00:00`).
4. Convert both dates to year, month, day components.
5. Compute `age = current_year - birth_year`.
6. If `(current_month, current_day) < (birth_month, birth_day)`, decrement `age` by 1.
7. Ensure `age` is an integer (floor).
8. Return the answer with `FINISH([age])`.

**Pattern 2: Fallback / verification**
- If the Patient bundle is empty or `birthDate` is missing, call `FINISH(["Patient birth date not available"])` or raise a clear error instead of guessing.
- If the `current time` cannot be parsed, fall back to the system clock but log the discrepancy.

**Pattern 3: Output formatting**
- The final output must be a JSON array containing a single integer, e.g., `FINISH([42])`.
- Do **not** embed explanatory text, units, or additional fields.

## Example Application
**Task:** "What's the age of the patient with MRN of S2119664?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2119664`
2. Response contains `"birthDate":"1957-08-15"`.
3. Task context provides `current time: 2023-11-13T10:15:00+00:00`.
4. Compute: 2023‑1957 = 66; since 11‑13 is after 08‑15, age remains 66.
5. `FINISH([66])`

**Correct output:** `FINISH([66])`
**Wrong output examples:**
- `FINISH(66)` (missing array brackets)
- `FINISH(["66 years"])` (extra string)
- `FINISH([67])` (incorrect rounding)

## Success Indicators
- The agent performs a Patient GET, extracts `birthDate`, computes age, and returns `FINISH([integer])`.
- No hard‑coded numbers appear in the answer.
- The computed age matches manual calculation using the provided current time.

## Failure Indicators
- The answer is a plain number, a string, or contains explanatory text.
- The agent returns a value without having performed a Patient GET or without using `birthDate`.
- The computed age is off by one year because the birthday check was omitted.
- The output format deviates from `FINISH([age])`.
