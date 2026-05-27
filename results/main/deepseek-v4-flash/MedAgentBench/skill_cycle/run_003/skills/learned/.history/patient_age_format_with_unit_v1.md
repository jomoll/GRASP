---
description: Format patient age with unit when answering age queries
name: patient_age_format_with_unit
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task5_16
  - task9_1
  - task2_25
  - task10_27
  - task3_16
  - task5_3
  - task4_26
  - task4_27
  - task10_18
  - task9_6
  update_cycle: 1
tags: []
version: 1
---

# Patient Age Format With Unit

## Pattern Description

When a task asks for a patient's age, you must compute the age from the Patient resource's `birthDate` field and return it as a string that includes the unit "years". The age must be rounded down to the nearest integer (floor). This skill ensures that age values are always returned with an explicit unit, preventing ambiguity between numeric age values and other numeric identifiers.

The core capability is computing age from a FHIR Patient resource and formatting the output correctly. The key behavior change is that you must never return a bare number for age — always include the unit "years".

## When to Use This Skill

- When the task asks "What's the age of the patient..." or any variation asking for a patient's age
- When the task context specifies "the answer should be rounded down to an integer"
- When you have retrieved a Patient resource and need to extract the patient's age
- When the task provides a current timestamp and asks for age calculation

## Common Failure Patterns

- Returning `FINISH(["51"])` instead of `FINISH(["51 years"])` — missing the unit
- Returning the raw `birthDate` string instead of computing the age
- Rounding up instead of down (floor) when the age is not an exact integer
- Using `Math.round()` instead of `Math.floor()` for age calculation
- Returning the age as a number type instead of a string with unit

## Recommended Patterns

**Pattern 1: Compute age from birthDate**
1. Extract `birthDate` from the Patient resource entry (field: `entry[0].resource.birthDate`)
2. Parse the current timestamp from the task context (e.g., "2023-11-13T10:15:00+00:00")
3. Calculate the difference in years: subtract birth year from current year, then subtract 1 if the current month/day is before the birth month/day
4. Apply `Math.floor()` to ensure the age is rounded down

CORRECT: `age = Math.floor(diffInYears)` where diffInYears is computed precisely
WRONG:   `age = Math.round(diffInYears)` — rounds up when fractional age >= 0.5

**Pattern 2: Format the output**
1. Convert the computed integer age to a string
2. Append " years" to the string
3. Return the result in the FINISH call as a single-element array containing the string

CORRECT: `FINISH(["51 years"])`
WRONG:   `FINISH(["51"])` — missing unit
WRONG:   `FINISH([51])` — number instead of string

## Example Application

**Task:** "What's the age of the patient with MRN of S2823623?"
Context: "It's 2023-11-13T10:15:00+00:00 now, and the answer should be rounded down to an integer."

**Step-by-step:**

1. Issue GET request: `GET http://localhost:8080/fhir/Patient?identifier=S2823623`
2. Extract `birthDate` from the response: `entry[0].resource.birthDate` (e.g., "1972-05-20")
3. Parse current time: `2023-11-13T10:15:00+00:00`
4. Compute age:
   - Birth year: 1972, Current year: 2023 → 51 years difference
   - Birth month: 5 (May), Current month: 11 (November) → no subtraction needed
   - Age = 51
5. Format: `"51 years"`
6. Return: `FINISH(["51 years"])`

CORRECT output: `FINISH(["51 years"])`
WRONG output:   `FINISH(["51"])`

## Success Indicators

- Agent returns age as a string with "years" unit (e.g., `"51 years"`)
- Agent uses `Math.floor()` for rounding down
- Agent correctly handles edge cases like birthdays that haven't occurred yet in the current year

## Failure Indicators

- Agent returns bare number without unit (e.g., `"51"`)
- Agent returns age as a number type instead of string
- Agent rounds up instead of down (e.g., returns `"52 years"` when actual age is 51.8)
- Agent returns the birthDate string instead of computed age
