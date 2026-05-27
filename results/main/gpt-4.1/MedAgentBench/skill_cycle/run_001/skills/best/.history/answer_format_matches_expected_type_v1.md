---
description: Ensures the answer format matches the expected output type for lab values,
  ages, and similar queries.
name: answer_format_matches_expected_type
provenance:
  action: ADD
  epoch: 1
  fixes: 12
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - task10_15
  - task10_20
  - task4_10
  - task10_24
  - task4_6
  - task4_27
  - task9_27
  - task10_18
  - task10_12
  - task10_21
  update_cycle: 0
tags:
- formatting
- lab values
- age
- output type
- validation
version: 1
---

# Answer Format Matches Expected Type

## Pattern Description

When returning answers for structured queries (such as lab values, ages, or date-value pairs), you must ensure the output format matches the explicit requirements in the task instructions or context. This includes returning a single number, a specific string format, or a structured object, rather than a string in an array, a sentence, or a multi-element array unless explicitly requested. This pattern is critical for tasks where the downstream consumer expects a particular data type or structure for further processing or evaluation.

This skill changes behavior by requiring you to parse the instruction for the expected answer type and to format your FINISH output accordingly, rather than defaulting to a string, array, or free-text summary.

## When to Use This Skill

- When the task instruction specifies the answer should be a single number, a specific string format, or a structured object.
- When returning lab values (e.g., magnesium, HbA1C) or patient age.
- When the instruction or context explicitly states the required output type or format (e.g., "should be a single number", "should be -1 if not available").
- When the answer is used for downstream logic or automated evaluation.

## Common Failure Patterns

- Returning `["1.8"]` instead of `[1.8]` when a number is required.
- Returning `["5.9% on 2023-11-12T06:19:00+00:00"]` instead of `["5.9%","2023-11-12T06:19:00+00:00"]` or the required format.
- Returning `["The patient with MRN S1152319 is 86 years old."]` instead of `[86]`.
- Returning `["5.0%","2023-11-09T10:06:00+00:00"]` when a single formatted string is required, or vice versa.
- Returning a string in an array when a number is required, or vice versa.

## Recommended Patterns

**Pattern 1: Inspect Task for Explicit Output Format**
- Carefully read the instruction and context for explicit output requirements (e.g., "should be a single number", "should be -1 if not available").
- If the instruction says "the answer should be a single number", return `[number]` (e.g., `[1.8]`), not `["1.8"]` or `["1.8 mg/dL"]`.
- If the instruction says "return age as an integer", return `[86]`, not `["86"]` or `["The patient is 86 years old."]`.
- If the instruction requires a value and a date, return `[value, date]` (e.g., `["5.9%","2023-11-12T06:19:00+00:00"]`), unless a specific string format is required.

**Pattern 2: Type Conversion and Validation**
- Convert extracted values to the required type (number, string, etc.) before returning.
- Validate the output matches the expected type and structure before FINISH.

**Pattern 3: Fallback for Missing Data**
- If the instruction specifies a sentinel value (e.g., `-1` if not available), return `[ -1 ]` as a number, not `["-1"]` or `["No value found"]`.

## Example Application

**Task:** "What’s the most recent magnesium level of the patient S6227720 within last 24 hours? The answer should be a single number converted to a unit of mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step-by-step:**

1. Issue GET with exact parameters:
   `GET /Observation?code=MG&patient=S6227720&date=ge2023-11-12T10:15:00+00:00`
2. Extract the most recent value from `Observation.valueQuantity.value`.
3. Convert to number if necessary.
4. FINISH with `[1.8]` (number in array).

CORRECT output: `[1.8]`
WRONG output: `["1.8"]`, `["1.8 mg/dL"]`, `["The most recent magnesium is 1.8 mg/dL"]`

**Task:** "What's the age of the patient with MRN of S1152319? The answer should be rounded down to an integer."

1. Extract birthDate, compute age as integer.
2. FINISH with `[86]`.

CORRECT output: `[86]`
WRONG output: `["86"]`, `["The patient with MRN S1152319 is 86 years old."]`

**Task:** "What’s the last HbA1C value and when was it recorded?"

1. Extract value and date.
2. FINISH with `["5.9%","2023-11-12T06:19:00+00:00"]` if two-element array is required, or `["5.9% on 2023-11-12T06:19:00+00:00"]` if a single string is required (match instruction).

## Success Indicators

- The FINISH output matches the explicit type and structure required by the instruction (number, string, array, etc.).
- No extraneous text, units, or sentences are present unless required.
- Downstream logic or evaluation does not fail due to type mismatch.

## Failure Indicators

- The answer is rejected or marked incorrect due to type or format mismatch (e.g., string instead of number, array instead of string).
- The output contains extra text, units, or is wrapped in a sentence when only a value is required.
- Downstream tasks or checks fail due to unexpected output structure.
