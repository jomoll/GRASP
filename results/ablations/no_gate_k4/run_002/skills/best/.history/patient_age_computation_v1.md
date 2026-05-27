---
description: "Compute a patient\u2019s age from the birthDate field using the current\
  \ time context"
name: patient_age_computation
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task3_14
  update_cycle: 0
tags:
- age
- patient
- date
version: 1
---

# Patient Age Computation from Birthdate

## Pattern Description
You must derive a patient’s age by extracting the `birthDate` element from a FHIR `Patient` resource and calculating the full years elapsed relative to the *current time* supplied in the task context. This reusable pattern replaces any ad‑hoc or hard‑coded age look‑ups and guarantees that the age is rounded down to the nearest integer, correctly handling month and day boundaries.

## When to Use This Skill
- When a task asks for "the age of the patient" (or similar phrasing) and provides an MRN or other identifier.
- When the task context includes a concrete current timestamp (e.g., `2023-11-13T10:15:00+00:00`).
- When the `Patient` resource returned by the API contains a `birthDate` field.

## Common Failure Patterns
- Using only the year difference (`2023 - 1975 = 48`) without checking if the birthday has occurred this year, leading to an off‑by‑one error.
- Reading a non‑standard field such as `age` or `extension` that may be present but is not guaranteed to be accurate.
- Returning the age as a free‑form sentence or with extra explanatory text.
- Returning the age as a list of strings instead of a scalar integer string.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. After the `GET /Patient?...` call, locate the `birthDate` element in the first entry of the returned Bundle (e.g., `entry[0].resource.birthDate`).
2. Parse the ISO‑8601 date string (e.g., `1975-04-22`).
3. Parse the current time supplied in the task context (the `context` field of the task JSON).  Use the same timezone offset.
4. Compute the year difference: `age = currentYear - birthYear`.
5. If `currentMonthDay < birthMonthDay`, subtract 1 from `age` (birthday not yet reached this year).
6. Convert `age` to a string and **return it as a scalar list**: `FINISH(["{age}"])`.

**Pattern 2: Fallback when birthDate is missing**
- If the `birthDate` element is absent or empty, respond with `FINISH(["unknown"])` and optionally log a note.

**Pattern 3: Output formatting rule**
- The final answer must be a JSON list containing a single string that is the integer age (e.g., `["52"]`).
- Do **not** include any additional words, sentences, or units.

## Example Application
**Task:** "What's the age of the patient with MRN of S2863714?"
**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2863714`
2. Extract `birthDate` → `1978-06-15`.
3. Current time from context → `2023-11-13T10:15:00+00:00`.
4. Year diff = 2023‑1978 = 45. Since 11‑13 (Nov 13) is after 06‑15 (June 15), birthday has passed → age = 45.
5. `FINISH(["45"])`.

## Success Indicators
- The agent finishes with `FINISH(["<integer>"])` where the integer matches manual calculation.
- No extra text, no list of strings, and the value is rounded down.

## Failure Indicators
- The returned age is off by one year.
- The output contains explanatory sentences or units (e.g., `"45 years"`).
- The agent returns a placeholder like `-1` or an empty list.
- The agent uses a field other than `birthDate` for the calculation.
