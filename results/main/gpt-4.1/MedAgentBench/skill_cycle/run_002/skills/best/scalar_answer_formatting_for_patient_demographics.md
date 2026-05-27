---
description: Enforce scalar (not string or list) output for direct demographic queries
  like patient age or MRN.
name: scalar_answer_formatting_for_patient_demographics
provenance:
  action: ADD
  epoch: 1
  fixes: 16
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_26
  update_cycle: 0
tags:
- formatting
- demographics
- FHIR
- answer-structure
version: 1
---

# Scalar Answer Formatting for Patient Demographics

## Pattern Description

When answering direct demographic queries such as patient age or medical record number (MRN), you must output the answer as a scalar value (number or string), not as a string inside a list or as a formatted sentence. This ensures downstream systems and evaluators can reliably parse and use the answer. This pattern applies to any task where the answer is a single value, not a narrative or explanation.

## When to Use This Skill

- When the task asks for a patient's age, MRN, or other single demographic field.
- When the instruction specifies the answer should be a number or string, not a sentence or explanation.
- When the answer is derived from a FHIR Patient resource field (e.g., `birthDate`, `identifier`).

## Common Failure Patterns

- Returning `FINISH(["69"])` instead of `FINISH([69])` for age queries (number as string).
- Returning `FINISH(["S6530532"])` instead of `FINISH([S6530532])` for MRN queries (MRN as string in a list).
- Returning `FINISH(["The patient's age is 69."])` (sentence instead of scalar).
- Returning a list of length >1 when only a single value is expected.

## Recommended Patterns

Pattern 1: Scalar Extraction and Formatting
- Extract the required field (e.g., calculate age as an integer, extract MRN as a string).
- Output the value as a scalar inside a single-element array: `[69]` or `["S6530532"]`.
- Do not wrap the value in a sentence or explanation.
- Do not use a list of strings unless the task explicitly requests multiple values.

CORRECT: `FINISH([69])` for age, `FINISH(["S6530532"])` for MRN
WRONG:   `FINISH(["69"])`, `FINISH(["The patient's age is 69."])`, `FINISH(["S6530532"])` (if MRN is not meant to be a string)

Pattern 2: Type Enforcement
- For age, ensure the value is an integer (not a string): `[69]` not `["69"]`.
- For MRN, use a string if the MRN contains non-numeric characters, but do not wrap in extra quotes or explanations.

Pattern 3: Output Structure
- Always use a single-element array for scalar answers: `[value]`.
- Never use a sentence or explanatory text unless the task explicitly requests it.

## Example Application

**Task:** "What's the age of the patient with MRN of S6530532?"

**Step-by-step:**

1. Issue GET: `GET /fhir/Patient?identifier=S6530532`
2. Extract `birthDate` from the Patient resource.
3. Calculate age as of the current date, rounding down to an integer.
4. Output: `FINISH([69])`

CORRECT output: `FINISH([69])`
WRONG output:   `FINISH(["69"])`, `FINISH(["The patient's age is 69."])`

**Task:** "What’s the MRN of the patient with name Denise Dunlap and DOB of 1945-09-20?"

1. Issue GET: `GET /fhir/Patient?given=Denise&family=Dunlap&birthdate=1945-09-20`
2. Extract MRN from the `identifier` field.
3. Output: `FINISH(["S3228213"])`

## Success Indicators

- The FINISH action contains a single-element array with a scalar value (number or string), not a sentence.
- The value matches the expected type (integer for age, string for MRN).
- No extraneous formatting, explanations, or list-of-strings.

## Failure Indicators

- The FINISH action contains a string inside a list for a number (e.g., `["69"]`).
- The output is a sentence or explanation instead of a scalar.
- The output is a list of multiple values when only one is expected.
- Downstream systems or evaluators reject the answer due to type or format mismatch.
