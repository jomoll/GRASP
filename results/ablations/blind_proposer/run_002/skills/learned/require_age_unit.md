---
description: "Enforce inclusion of the age unit (years) in answers to any patient\u2011\
  age query."
name: require_age_unit
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 1
  fixes_unused: 10
  probe_score_unused: -1
  regressions_unused: 4
  triggering_sample_ids:
  - task10_20
  - task4_15
  - task2_1
  - task8_21
  - task4_27
  - task2_25
  - task10_17
  - task1_11
  - task2_6
  - task10_10
  update_cycle: 0
tags: []
version: 1
---

# require_age_unit

## Pattern Description
You must always include an explicit unit when answering a question that asks for a patient’s age. The unit for human age is always **years**. Compute the integer age (rounded down) from the patient’s `birthDate` and then format the answer as a string that ends with the word `years`. This prevents ambiguous numeric answers and satisfies the strict answer format expectations.

## When to Use This Skill
- The task description contains the word **age** and asks for the patient’s age (e.g., "What’s the age of the patient with MRN of …?").
- The answer is expected to be a single integer rounded down, but the required output format is a string with a unit.
- The task provides a reference time (e.g., "It's 2023‑11‑13T10:15:00+00:00 now").

## Common Failure Patterns
- Returning `FINISH(["60"])` – missing the required unit.
- Returning a numeric type instead of a string (e.g., `FINISH([60])`).
- Adding extra text or punctuation (e.g., `FINISH(["60 years old"])`).

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Issue a `GET` request for the `Patient` resource using the identifier supplied in the task.
2. Extract the `birthDate` field from the returned patient resource.
3. Compute the age in whole years by subtracting the birth year from the reference year, adjusting for month/day if the birthday has not yet occurred this year.
4. Create a string `age_str = f"{age} years"`.
5. Return `FINISH([age_str])`.

**Pattern 2: Validation fallback**
- If the `birthDate` field is missing or cannot be parsed, respond with `FINISH(["Age not available"] )` (still a string, but without a numeric value).

**Pattern 3: Formatting guard**
- Ensure the final output array contains exactly one element, a string that matches the regex `^\d+ years$`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. From the response, read `birthDate": "1963-04-15"`.
3. Reference time is `2023-11-13T10:15:00+00:00`. Compute age: 2023‑1963 = 60 (birthday already passed this year).
4. Build `age_str = "60 years"`.
5. `FINISH(["60 years"])`.

**Correct output:** `FINISH(["60 years"])`
**Wrong output:** `FINISH(["60"])` or `FINISH([60])`

## Success Indicators
- The FINISH payload contains a single string ending with the word `years`.
- The numeric part matches the correctly calculated whole‑year age.

## Failure Indicators
- The FINISH payload is a bare number or lacks the `years` suffix.
- The payload contains extra wording (e.g., "years old").
- The age calculation is off by one year because the birthday check was omitted.
