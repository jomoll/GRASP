---
description: "Extract patient age from birthDate, with missing\u2011field handling\
  \ and rounding down."
name: extract_age_from_birthdate
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 12
  regressions: 0
  triggering_sample_ids:
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task3_3
  - task4_28
  - task4_7
  - task8_5
  - task10_8
  update_cycle: 0
tags: []
version: 1
---

# Extract Age From Patient BirthDate

## Pattern Description
You must compute a patient’s age by reading the `birthDate` element of a FHIR `Patient` resource. This pattern is reusable for any task that asks for the patient’s age, regardless of the identifier used (MRN, internal ID, etc.). Before performing any arithmetic, always verify that the `birthDate` field exists; if it is absent, treat the request as “age not available” and do not fabricate a value. Use the current time supplied in the task context (ISO‑8601) and round the result down to the nearest whole year.

## When to Use This Skill
- When a task asks “What is the age of the patient …” or similar phrasing.
- When the task provides a patient identifier (e.g., MRN) and expects a numeric age answer.
- When the `Patient` search response is a Bundle and you need to locate the patient resource inside `entry[0].resource`.

## Common Failure Patterns
- Using `effectiveDateTime` or `issued` instead of `birthDate`.
- Assuming `birthDate` is always present and computing age when the field is missing, leading to fabricated ages.
- Returning the raw `birthDate` string instead of an integer.
- Not rounding down (e.g., returning 45.7 instead of 45).
- Ignoring the task‑provided “current time” and using the system clock.

## Recommended Patterns
**Pattern 1: Core extraction and age calculation**
1. After a `GET /Patient?identifier=...` request, locate the patient resource:
   ```json
   patient = response["entry"][0]["resource"]
   ```
2. Check for the presence of `patient["birthDate"]`.
   - **If present**: parse the ISO‑8601 date.
   - **If missing**: go to Pattern 2 (fallback).
3. Parse the task context to obtain `current_time` (ISO‑8601 string).
4. Compute the difference in years, rounding down:
   ```python
   age = current_time.year - birthDate.year - ((current_time.month, current_time.day) < (birthDate.month, birthDate.day))
   ```
5. Return the age as an integer inside `FINISH([age])`.

**Pattern 2: Missing‑field fallback**
- Respond with a clear placeholder indicating the age is unavailable, e.g.: `FINISH(["Age not available"])`.
- Do **not** guess or use other fields such as `deceasedDateTime`.

**Pattern 3: Output formatting**
- The final output must be a JSON array containing a single integer (or the placeholder string).
- Do **not** embed explanatory text inside the array.

## Example Application
**Task:** "What's the age of the patient with MRN of S2863714?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2863714`
2. Extract `patient = response["entry"][0]["resource"]`.
3. Verify `patient["birthDate"]` exists (e.g., `"1978-04-12"`).
4. Parse task context `current_time = "2023-11-13T10:15:00+00:00"`.
5. Compute age → 45 (rounded down).
6. `FINISH([45])`

**CORRECT output:** `FINISH([45])`
**WRONG output:** `FINISH(["45 years old"])` or `FINISH(["1978-04-12"])`

## Success Indicators
- The agent returns a single integer inside the FINISH array.
- The integer matches the calendar‑year difference calculated from `birthDate` and the task’s current time, rounded down.
- If `birthDate` is missing, the placeholder string is returned and no age is fabricated.

## Failure Indicators
- Age is derived from any field other than `birthDate`.
- The agent returns a string with units or explanatory text.
- The agent returns a value when `birthDate` is absent.
- The computed age is not rounded down (e.g., includes a decimal).
