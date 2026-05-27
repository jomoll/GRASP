---
description: Calculate patient age by comparing birthDate to the current date provided
  in the task context.
name: patient_age_calculation_strategy
provenance:
  action: ADD
  epoch: 1
  fixes: 3
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task2_30
  - task9_22
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  - task2_26
  - task2_1
  - task2_14
  - task2_6
  update_cycle: 1
tags:
- patient
- calculation
- fhir
version: 1
---

## Skill Title
Patient Age Calculation Strategy

## Pattern Description
When a task requires the age of a patient, you must not rely on external knowledge or assume the age is static. You must retrieve the `birthDate` from the `Patient` resource and calculate the age by comparing the year, month, and day of birth against the current date provided in the task context.

Always round the result down to the nearest integer (floor) to represent the completed years of age.

## When to Use This Skill
- When the task asks for a patient's age.
- When the task provides a current date context and an MRN or patient identifier.

## Common Failure Patterns
- Guessing the age based on the current year without accounting for the birth month and day.
- Failing to use the `birthDate` field from the FHIR `Patient` resource.
- Rounding to the nearest integer instead of rounding down (floor).

## Recommended Patterns

**Pattern 1: Data Retrieval**
1. Perform a `GET` request to `Patient?identifier={MRN}`.
2. Extract the `birthDate` field (format: YYYY-MM-DD).

**Pattern 2: Calculation**
1. Identify the current date from the task context (e.g., 2023-11-13).
2. Calculate the difference in years: `current_year - birth_year`.
3. If the current month/day is before the birth month/day, subtract 1 from the year difference.

**Pattern 3: Output**
1. Return the final integer age using `FINISH([age])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step-by-step:**
1. GET `http://localhost:8080/fhir/Patient?identifier=S2703270`.
2. Receive `birthDate: "1943-05-20"`.
3. Current date is `2023-11-13`.
4. 2023 - 1943 = 80. Since Nov 13 is after May 20, the age is 80.
5. Output: `FINISH([80])`.

## Success Indicators
- The agent retrieves the `birthDate` before calculating.
- The final output is a single integer representing the age.

## Failure Indicators
- The agent returns a string or a non-integer value.
- The age is off by one year due to ignoring the month/day component.
