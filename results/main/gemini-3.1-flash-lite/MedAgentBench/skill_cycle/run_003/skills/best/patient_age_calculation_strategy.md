---
description: Calculate patient age by subtracting birthDate from the current date
  and rounding down.
name: patient_age_calculation_strategy
provenance:
  action: ADD
  epoch: 0
  fixes: 7
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task2_16
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  - task2_9
  - task9_3
  update_cycle: 0
tags:
- patient
- calculation
- age
version: 1
---

## Skill Title
Patient Age Calculation Strategy

## Pattern Description
When a task requires the age of a patient, you must not rely on static or hallucinated values. Instead, you must retrieve the `birthDate` field from the `Patient` resource and calculate the age based on the current date provided in the task context.

Age is defined as the number of full years elapsed between the `birthDate` and the current date. You must round down to the nearest integer (floor function).

## When to Use This Skill
- When the task asks for a patient's age.
- When the task provides a current date in the context and requires an age calculation based on a `birthDate` found in a `Patient` resource.

## Common Failure Patterns
- Returning a static number or guessing based on appearance.
- Failing to account for the current date provided in the prompt.
- Incorrectly rounding up or using floating-point numbers instead of integers.

## Recommended Patterns

**Pattern 1: Data Retrieval**
1. Perform a `GET` request for the `Patient` resource using the provided MRN or identifier.
2. Extract the `birthDate` field (format: YYYY-MM-DD).

**Pattern 2: Calculation**
1. Identify the current date from the task context (e.g., 2023-11-13).
2. Calculate the difference in years: `Age = CurrentYear - BirthYear`.
3. If the current month/day is before the birth month/day, subtract 1 from the result.
4. Ensure the final result is an integer.

**Pattern 3: Completion**
1. Return the calculated integer as the final answer.

## Example Application

**Task:** "What's the age of the patient with MRN of S2703270?"

**Step-by-step:**
1. GET `http://localhost:8080/fhir/Patient?identifier=S2703270`
2. Extract `birthDate`: "1978-05-15".
3. Current date: "2023-11-13".
4. Calculation: 2023 - 1978 = 45. Since November is after May, the patient is 45.
5. Output: `FINISH([45])`

## Success Indicators
- The agent performs a GET request to retrieve the patient record.
- The final output is a single integer representing the correct age.

## Failure Indicators
- The agent returns a value that does not match the math based on the `birthDate`.
- The agent returns a string or a non-integer value.
