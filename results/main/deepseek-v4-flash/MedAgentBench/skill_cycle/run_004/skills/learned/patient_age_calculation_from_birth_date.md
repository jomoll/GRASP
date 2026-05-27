---
description: Calculate integer age from Patient.birthDate using the current date context
name: patient_age_calculation_from_birth_date
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 10
  regressions: 1
  triggering_sample_ids:
  - task9_22
  - task4_15
  - task1_12
  - task4_26
  - task9_3
  - task1_11
  - task2_16
  - task9_8
  - task1_15
  - task10_12
  update_cycle: 0
tags: []
version: 1
---

# Patient Age Calculation from Birth Date

## Pattern Description

When asked to compute a patient's age, you must calculate it from the patient's birth date (`birthDate` field in the Patient resource) using the current date provided in the task context. The age must be rounded down to an integer (floor), meaning you count only complete years. Do not use any pre-computed age field from the Patient resource, as such fields may be stale or absent. Always compute the age yourself using the birth date and the current date.

This skill applies whenever a task asks "What's the age of the patient..." or similar phrasing that requires computing a patient's age in years. The core lesson is: never trust a pre-computed age value; always compute it from `birthDate` and the current date, then floor to an integer.

## When to Use This Skill

- When the task instruction asks "What's the age of the patient with MRN of X?" or "How old is patient X?"
- When the task context provides a current timestamp (e.g., "Current time: 2023-11-13T10:15:00+00:00")
- When you have retrieved a Patient resource and need to report the patient's age in years
- When the task explicitly says "the answer should be rounded down to an integer"

## Common Failure Patterns

- Using a pre-computed `age` field from the Patient resource (e.g., `Patient.age` or `Patient.extension` containing age) instead of computing from `birthDate`
- Returning the birth year difference (e.g., `2023 - 1960 = 63`) without checking if the birthday has occurred yet in the current year
- Returning a string like `"66 years old"` instead of a plain integer `66`
- Using the current date from the system clock instead of the date provided in the task context
- Rounding up instead of down (e.g., returning 67 when the correct floor age is 66)

## Recommended Patterns

**Pattern 1: Compute age from birthDate using the context current date**
1. Extract `birthDate` from the Patient resource (format: "YYYY-MM-DD")
2. Use the current date from the task context (e.g., "2023-11-13T10:15:00+00:00")
3. Compute the difference in years: `current_year - birth_year`
4. If the current month-day is before the birth month-day, subtract 1 (birthday hasn't occurred yet this year)
5. Return the result as a plain integer, not a string or formatted sentence

CORRECT: `FINISH([66])`
WRONG:   `FINISH(["66"])` (string instead of number)
WRONG:   `FINISH(["66 years old"])` (formatted string)
WRONG:   `FINISH([67])` (not floored)

**Pattern 2: Verify the birthDate field exists**
If the Patient resource has no `birthDate` field, return an appropriate error or "Unknown" rather than guessing.

**Pattern 3: Output format**
The final answer must be a single integer wrapped in an array: `FINISH([age])`. Do not include units, labels, or explanatory text.

## Example Application

**Task:** "What's the age of the patient with MRN of S2119664?"
**Context:** "Current time: 2023-11-13T10:15:00+00:00"

**Step-by-step:**
1. Issue GET: `GET http://localhost:8080/fhir/Patient?identifier=S2119664`
2. Extract `birthDate` from the response Patient resource (e.g., `"birthDate": "1957-03-22"`)
3. Current date from context: 2023-11-13
4. Birth year: 1957, Current year: 2023 → difference = 66
5. Check birthday: March 22 is before November 13, so birthday has occurred → no subtraction
6. Age = 66
7. Output: `FINISH([66])`

CORRECT output: `FINISH([66])`
WRONG output:   `FINISH(["66"])` (string)
WRONG output:   `FINISH(["66 years old"])` (formatted)

## Success Indicators

- Agent issues a GET for the Patient resource by identifier
- Agent extracts `birthDate` from the response
- Agent computes age using the context current date, not system clock
- Agent returns a plain integer in an array: `FINISH([age])`
- The integer is floored (no decimal, no rounding up)

## Failure Indicators

- Agent returns a string instead of a number (e.g., `FINISH(["66"])`)
- Agent returns a formatted sentence (e.g., `FINISH(["Patient is 66 years old"])`)
- Agent returns a wrong integer because it didn't check if birthday passed (e.g., returns 67 when correct is 66)
- Agent uses a pre-computed age field from the Patient resource instead of computing from `birthDate`
- Agent uses the system clock instead of the context current date
