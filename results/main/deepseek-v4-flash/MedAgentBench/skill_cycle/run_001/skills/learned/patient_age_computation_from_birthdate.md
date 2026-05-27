---
description: Compute patient age correctly using date difference, not year subtraction
name: patient_age_computation_from_birthdate
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 8
  regressions: 0
  triggering_sample_ids:
  - task5_19
  - task1_20
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  - task5_16
  update_cycle: 1
tags:
- age_computation
- patient_demographics
- date_arithmetic
version: 1
---

# Patient Age Computation from BirthDate

## Pattern Description

When asked to compute a patient's age, you must calculate the full year difference between the current date and the patient's `birthDate`, accounting for whether the birthday has occurred yet in the current year. Simply subtracting the birth year from the current year (e.g., `2023 - 1948 = 75`) is incorrect because it ignores the month and day. The correct age is the number of full years elapsed, rounded down to the nearest integer.

This skill applies whenever you need to answer "What's the age of the patient..." or similar questions that require computing age from a FHIR Patient resource's `birthDate` field. The current time is always provided in the task context (e.g., "Current time: 2023-11-13T10:15:00+00:00").

## When to Use This Skill

- When the task asks "What's the age of the patient..." and you have retrieved a Patient resource with a `birthDate` field
- When the task context provides a current timestamp and specifies the answer should be "rounded down to an integer"
- When you need to compute age for any clinical decision that depends on patient age (e.g., medication dosing, screening recommendations)

## Common Failure Patterns

- Subtracting only the birth year from the current year: `2023 - 1948 = 75` — this ignores month and day, producing an age that is off by 1 for patients whose birthday hasn't occurred yet this year
- Using `Math.floor((currentYear - birthYear))` without checking month/day — same failure
- Extracting the wrong date field (e.g., `meta.lastUpdated` instead of `birthDate`)
- Returning the age as a string like `"75 years old"` instead of a plain integer
- Forgetting to parse the `birthDate` string into year, month, and day components

## Recommended Patterns

**Pattern 1: Compute age using full date comparison**

1. Extract the patient's `birthDate` from the Patient resource (format: `YYYY-MM-DD`)
2. Parse the current date from the task context (e.g., `2023-11-13T10:15:00+00:00`)
3. Compute the age as follows:
   - Let `birthYear`, `birthMonth`, `birthDay` be the components of `birthDate`
   - Let `currentYear`, `currentMonth`, `currentDay` be the components of the current date
   - Set `age = currentYear - birthYear`
   - If `currentMonth < birthMonth` OR (`currentMonth == birthMonth` AND `currentDay < birthDay`), then subtract 1 from `age`
4. Return the age as a plain integer

CORRECT: For birthDate `1948-05-11` and current date `2023-11-13`: `2023 - 1948 = 75`, then check month: November (11) >= May (5), so no subtraction. Age = 75.

CORRECT: For birthDate `1948-12-25` and current date `2023-11-13`: `2023 - 1948 = 75`, then check month: November (11) < December (12), so subtract 1. Age = 74.

WRONG: `2023 - 1948 = 75` without month/day check — produces 75 when the correct answer is 74.

**Pattern 2: Verify the birthDate field**

- The `birthDate` field is a string in the Patient resource at `entry[0].resource.birthDate`
- Format is always `YYYY-MM-DD` (e.g., `"1948-05-11"`)
- Do not confuse with `meta.lastUpdated` or other timestamps

**Pattern 3: Format the output**

- Return the age as a plain integer inside an array: `FINISH([75])`
- Do not include units, labels, or explanatory text
- Do not round up — always round down (floor)

## Example Application

**Task:** "What's the age of the patient with MRN of S2450227?"
Context: "It's 2023-11-13T10:15:00+00:00 now, and the answer should be rounded down to an integer."

**Step-by-step:**

1. Issue GET request: `GET http://localhost:8080/fhir/Patient?identifier=S2450227`
2. Extract `birthDate` from response: `entry[0].resource.birthDate` = `"1948-05-11"`
3. Parse current date: year=2023, month=11, day=13
4. Parse birth date: year=1948, month=5, day=11
5. Compute: `age = 2023 - 1948 = 75`
6. Check: current month (11) >= birth month (5) → no subtraction needed
7. Result: age = 75

CORRECT output: `FINISH([75])`
WRONG output: `FINISH(["75"])` or `FINISH([75.0])` or `FINISH(["75 years old"])`

## Success Indicators

- The agent extracts `birthDate` from the Patient resource, not from other fields
- The agent computes age using month/day comparison, not just year subtraction
- The output is a plain integer inside an array: `FINISH([age])`
- The age matches the correct value when verified manually

## Failure Indicators

- The agent returns an age that is off by 1 (too high) for patients whose birthday hasn't occurred yet this year
- The agent returns the age as a string or with units
- The agent uses `Math.floor((currentYear - birthYear))` without month/day check
- The agent extracts the wrong date field (e.g., `meta.lastUpdated` instead of `birthDate`)
