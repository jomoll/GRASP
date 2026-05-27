---
description: Enforce integer array output for age queries, not string arrays or strings.
name: answer_format_enforcement_for_numeric_demographics
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 10
  regressions: 0
  triggering_sample_ids:
  - task5_17
  - task4_23
  - task10_13
  - task10_8
  - task2_6
  - task4_11
  - task10_24
  - task4_7
  - task9_28
  - task2_25
  update_cycle: 0
tags:
- format
- demographics
- age
- type-safety
- FHIR
version: 1
---

# Answer Format Enforcement for Numeric Demographics

## Pattern Description

When returning demographic values such as patient age, the answer must be formatted as an array containing a single integer (e.g., `[51]`), not as a string or an array of strings (e.g., `["51"]`). This ensures downstream consumers receive the correct data type and prevents subtle type errors in further processing or evaluation.

This pattern is especially important for age queries, where the agent may extract a string from the FHIR resource but must convert it to an integer before returning the answer. The agent should always check the type of the value before submitting the final answer.

## When to Use This Skill

- When answering questions about a patient's age (e.g., "What's the age of the patient with MRN of S2823623?").
- When the expected answer is a single integer value, such as age, and the instruction or context specifies integer output.
- When extracting a numeric demographic value from a FHIR resource (e.g., `Patient.birthDate`).

## Common Failure Patterns

- Returning `["51"]` (array of strings) instead of `[51]` (array of integers).
- Returning `"51"` (string) instead of `[51]` (array of integers).
- Returning `[51.0]` (float) instead of `[51]` (integer), when the instruction specifies integer and rounding down.
- Failing to round down the age to the nearest integer when required.

## Recommended Patterns

**Pattern 1: Extract and Convert to Integer**
- Extract the date of birth from `Patient.birthDate`.
- Calculate the age as the difference in years between the current date and the birth date, rounding down to the nearest integer.
- Ensure the value is an integer, not a string or float.
- Return the answer as an array containing the integer: `[age]`.

CORRECT: `[51]`
WRONG: `["51"]`, `"51"`, `[51.0]`

**Pattern 2: Verification Before FINISH**
- Before calling `FINISH`, check that the answer is an array of integers.
- If the value is a string, convert it to an integer.
- If the value is a float, round down and convert to integer.

**Pattern 3: Output Structure**
- The final output must be a JSON array with a single integer value, e.g., `[48]`.

## Example Application

**Task:** "What's the age of the patient with MRN of S0722219?"

**Step-by-step:**

1. Issue GET request: `GET /fhir/Patient?identifier=S0722219`
2. Extract `birthDate` from the Patient resource (e.g., `1975-11-13`).
3. Calculate age as of `2023-11-13T10:15:00+00:00` (current time): `2023 - 1975 = 48`.
4. Ensure the value is an integer: `48`.
5. Return the answer as `[48]`.

CORRECT output: `FINISH([48])`
WRONG output:   `FINISH(["48"])`, `FINISH("48")`, `FINISH([48.0])`

## Success Indicators

- The answer is a JSON array containing a single integer value (e.g., `[66]`).
- No string or float types are present in the output array.
- The value matches the expected integer age, rounded down if necessary.

## Failure Indicators

- The answer is an array of strings (e.g., `["51"]`).
- The answer is a string (e.g., `"51"`).
- The answer is a float (e.g., `[51.0]`).
- The answer is not wrapped in an array (e.g., `51`).
