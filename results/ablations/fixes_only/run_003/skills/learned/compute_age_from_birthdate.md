---
description: "Accurately compute a patient\u2019s age from the birthDate field given\
  \ a reference current time."
name: compute_age_from_birthdate
provenance:
  action: ADD
  epoch: 0
  fixes: 14
  probe_score: 9
  regressions: 2
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task1_6
  - task10_15
  - task9_11
  - task1_15
  - task4_11
  - task9_14
  - task9_27
  - task1_12
  update_cycle: 0
tags:
- age
- date
- patient
- calculation
version: 1
---

# Compute Age From Birthdate

## Pattern Description
You must reliably calculate a patient’s age whenever a task asks for it (e.g., “What’s the age of the patient with MRN …?”). The core reusable capability is to extract the `birthDate` from a `Patient` resource, parse it as an ISO‑8601 date, compare it to the *current time* supplied in the task context, and return the integer number of full years elapsed (rounded down). This pattern prevents off‑by‑one errors that arise from naïve year subtraction or from using the wrong date field.

## When to Use This Skill
- The task explicitly requests the patient’s age.
- The task provides a current timestamp in the context (e.g., `Current time: 2023-11-13T10:15:00+00:00`).
- You have already retrieved a `Patient` bundle that contains a `birthDate` element.

## Common Failure Patterns
- Subtracting only the year numbers (`2023 - 1940 = 83`) without considering month/day, leading to an age that is too high by one year.
- Using `effectiveDateTime` or another unrelated field instead of `birthDate`.
- Returning the age as a string with units (e.g., `"83 years"`) or as a JSON array of strings.
- Forgetting to floor the result, producing a fractional age (e.g., `83.7`).
- Ignoring the supplied current time and using the system clock, which may differ from the task’s reference time.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. Locate the patient entry in the returned Bundle (`entry[0].resource`).
2. Extract `birthDate` (e.g., `"1940-05-12"`).
3. Parse the task’s context string to obtain the reference current time (`2023-11-13T10:15:00+00:00`).
4. Convert both dates to a comparable date object (UTC).
5. Compute the difference in years:
   - If the current month/day is before the birth month/day, subtract one from the year difference.
   - Otherwise, use the plain year difference.
6. **Floor** the result to an integer.
7. Return the age as a numeric element inside a JSON array: `FINISH([age])`.

**Pattern 2: Fallback when birthDate is missing**
- If the `Patient` resource does not contain a `birthDate` field, respond with a clear message: `FINISH(["Birthdate not available"])`.

**Pattern 3: Output formatting**
- The final output must be a JSON array containing a single integer (or the fallback string). No extra commentary, units, or surrounding text.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"
**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
2. From the Bundle response, extract `entry[0].resource.birthDate` → `"1943-04-22"`.
3. Parse the context timestamp `2023-11-13T10:15:00+00:00`.
4. Year difference = 2023 − 1943 = 80. Since 11‑13 (Nov 13) is after 04‑22 (Apr 22), the age remains 80.
5. `FINISH([80])`.

**Correct output:** `FINISH([80])`
**Incorrect output examples:**
- `FINISH(["80 years"])`
- `FINISH([80.4])`
- `FINISH([81])` (off‑by‑one)

## Success Indicators
- The agent returns a single integer inside a JSON array.
- The integer matches manual calculation using the supplied current time.
- No extra text, units, or comments are present.

## Failure Indicators
- The returned age is off by one year.
- The output includes a string, units, or decimal values.
- The agent uses the wrong date field or ignores the task’s current time.
