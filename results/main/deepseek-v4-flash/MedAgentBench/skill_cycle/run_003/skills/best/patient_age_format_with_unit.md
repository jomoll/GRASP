---
description: Return patient age as integer only, not as string with unit
name: patient_age_format_with_unit
provenance:
  action: MODIFY
  epoch: 1
  fixes: 10
  parent_version: 1
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task10_17
  - task2_17
  - task4_28
  - task9_28
  - task9_22
  - task2_25
  - task2_9
  - task10_10
  - task5_17
  update_cycle: 0
tags: []
version: 2
---

# Patient Age Format as Integer

## Pattern Description

When answering age queries, you must return the age as a plain integer number, not as a string with the unit "years" appended. The task context explicitly states the answer should be rounded down to an integer. Returning a string like "76 years" instead of the number 76 causes the answer to be marked incorrect.

This skill teaches you to extract the patient's birth date from the Patient resource, compute the age in years by comparing to the current time, round down to an integer, and return only that integer value in the FINISH array.

## When to Use This Skill

- When the task asks "What's the age of the patient..." or similar age queries
- When the task context says "the answer should be rounded down to an integer"
- When you have retrieved a Patient resource and need to compute age from `birthDate`

## Common Failure Patterns

- Returning `["76 years"]` instead of `[76]` — the unit string causes incorrect answer format
- Returning `["76"]` (string) instead of `[76]` (number) — wrong data type
- Including explanatory text like `["The patient is 76 years old"]` instead of just the number
- Not rounding down to an integer (e.g., returning 76.3 instead of 76)

## Recommended Patterns

**Pattern 1: Compute and return age as integer**
1. Extract `birthDate` from the Patient resource (format: "YYYY-MM-DD")
2. Use the current time provided in the task context (e.g., "2023-11-13T10:15:00+00:00")
3. Calculate age in years by subtracting birth year from current year, then subtract 1 if the current month/day is before the birth month/day
4. Round down to an integer (floor division)
5. Return ONLY the integer in the FINISH array — no strings, no units, no extra text

CORRECT: `FINISH([76])`
WRONG:   `FINISH(["76 years"])`
WRONG:   `FINISH(["76"])`
WRONG:   `FINISH([76.3])`

**Pattern 2: Verify output format before FINISH**
Before calling FINISH, check that your answer is a plain number (integer) inside the array, not a string. If you see quotes around the number, remove them.

## Example Application

**Task:** "What's the age of the patient with MRN of S0611496?"
**Context:** "It's 2023-11-13T10:15:00+00:00 now, and the answer should be rounded down to an integer."

**Step-by-step:**

1. Issue GET to find patient: `GET http://localhost:8080/fhir/Patient?identifier=S0611496`
2. Extract `birthDate` from response (e.g., "1947-05-22")
3. Current time is 2023-11-13. Birth year is 1947.
4. Age = 2023 - 1947 = 76. Since current month/day (Nov 13) is after birth month/day (May 22), no subtraction needed.
5. Return just the integer: `FINISH([76])`

CORRECT output: `FINISH([76])`
WRONG output:   `FINISH(["76 years"])`

## Success Indicators

- FINISH array contains a single integer number (e.g., `[76]`)
- No string quotes around the number
- No unit text like "years" in the output
- Age is rounded down to the nearest whole year

## Failure Indicators

- FINISH array contains a string like `"76 years"` or `"76"`
- FINISH array contains a decimal number like `76.3`
- FINISH array contains explanatory text
- Age calculation is off by one year due to not checking month/day
