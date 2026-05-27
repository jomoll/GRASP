---
description: Enforce that age answers contain only the integer value, no unit text
name: age_answer_numeric_only
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 2
  fixes_unused: 13
  probe_score_unused: 9
  regressions_unused: 3
  triggering_sample_ids:
  - task10_24
  - task4_23
  - task4_10
  - task2_25
  - task9_22
  - task4_28
  - task9_28
  - task9_1
  - task4_27
  - task2_30
  update_cycle: 0
tags: []
version: 1
---

# Age Answer Numeric Only

## Pattern Description
You must return a patient’s age as a plain integer without any trailing unit or explanatory text. This pattern applies to any task that asks for the age of a patient (e.g., "What’s the age of the patient with MRN …?"). The goal is to keep the FINISH payload minimal and type‑consistent so downstream processing can treat the value as a number.

## When to Use This Skill
- When the task explicitly requests the patient’s age.
- When the task description includes phrases like "age of the patient" or "how old is the patient".
- When the expected answer type is a list containing a single numeric element (e.g., `FINISH([51])`).

## Common Failure Patterns
- Returning `"51 years"` instead of `51`.
- Returning a string array with the unit: `FINISH(["51 years"])`.
- Including additional words or punctuation (e.g., `FINISH(["Age: 51 years"])`).

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Use the `calculate_age_from_birthdate` skill to compute the age in whole years.
2. Ensure the result is a plain integer (no quotes, no unit).
3. Wrap the integer in a JSON array for the FINISH call.

   **CORRECT**: `FINISH([51])`
   **WRONG**: `FINISH(["51 years"])`
   **WRONG**: `FINISH(["Age: 51"])`

**Pattern 2: Verification fallback**
- After extracting the age, double‑check that the value is of type `int` (or can be safely cast to int). If it is a string, strip any non‑numeric characters and re‑cast.
- If the age cannot be determined, return an empty list `FINISH([])` rather than a descriptive error string.

**Pattern 3: Integration with strict answer format**
- Apply this skill *before* the generic `strict_answer_format` skill so that the latter sees a correctly typed payload.

## Example Application
**Task:** "What's the age of the patient with MRN of S2823623?"

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Patient?identifier=S2823623`.
2. Locate the `birthDate` field in the returned Patient resource.
3. Call `calculate_age_from_birthdate` to obtain the integer age (e.g., `51`).
4. Output `FINISH([51])`.

**CORRECT output:** `FINISH([51])`
**WRONG output:** `FINISH(["51 years"])`

## Success Indicators
- FINISH payload is a JSON array containing a single integer.
- No alphabetic characters appear inside the array element.
- Subsequent skills that expect a numeric age (e.g., dosing calculations) receive a proper integer.

## Failure Indicators
- FINISH contains a string with the word "years" or any other unit.
- The array element is quoted, making it a string rather than a number.
- The agent returns an explanatory sentence instead of the bare integer.
