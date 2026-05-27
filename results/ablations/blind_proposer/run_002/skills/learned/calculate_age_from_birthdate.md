---
description: "Derive a patient\u2019s age in whole years from the Patient.birthDate\
  \ field and the current time."
name: calculate_age_from_birthdate
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 1
  fixes_unused: 5
  probe_score_unused: -3
  regressions_unused: 4
  triggering_sample_ids:
  - task10_27
  - task8_14
  - task1_16
  - task10_12
  - task9_1
  - task2_22
  - task10_13
  - task10_18
  - task1_15
  - task4_10
  update_cycle: 1
tags:
- age
- patient
- calculation
version: 1
---

# Calculate Age from Patient.birthDate

## Pattern Description
You must compute the patient’s age at the moment the task is executed instead of using a hard‑coded value. Extract the `birthDate` string from the `Patient` resource, parse it as an ISO‑8601 date, and subtract it from the current timestamp supplied in the task context (or the system clock). Round the result down to the nearest integer and always append the unit "years".

## When to Use This Skill
- When a task asks *"What is the age of the patient ..."* or any similar age‑related query.
- When the task provides a current time in the context (e.g., `2023-11-13T10:15:00+00:00`).
- After you have performed a `GET` request that returns a `Patient` bundle containing a `birthDate` element.

## Common Failure Patterns
- Returning a static or previously‑seen age value (e.g., `"82 years"`).
- Using the `age` field from a different resource instead of calculating from `birthDate`.
- Omitting the unit or using the wrong unit (e.g., `"82"` or `"82 months"`).
- Performing the calculation with the wrong timezone or including time‑of‑day, leading to off‑by‑one errors.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. Locate the patient entry in the returned `Bundle` (`entry[0].resource`).
2. Read `resource.birthDate` (e.g., `"1945-09-20"`).
3. Parse the birth date as a date‑only value (ignore time).  
4. Obtain the current datetime from the task context (`Current time: 2023-11-13T10:15:00+00:00`).
5. Compute the difference in years:
   ```
   age = current_year - birth_year
   if (current_month, current_day) < (birth_month, birth_day):
       age -= 1
   ```
6. Convert the integer to a string and append a space and the word `years`.

**Pattern 2: Fallback / verification**
- If `birthDate` is missing or not a valid ISO‑8601 date, call `FINISH(["unknown"] )` or raise a clear error.
- Verify that the computed age is non‑negative; if negative, treat as an error.

**Pattern 3: Output formatting**
- The final answer must be a JSON array with a single string element, e.g., `FINISH(["45 years"])`.
- Do **not** include any extra text, brackets, or explanations.

## Example Application
**Task:** "What's the age of the patient with MRN of S2119664?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2119664`
2. Response contains `"birthDate":"1957-04-12"`.
3. Current time from context: `2023-11-13T10:15:00+00:00` → year 2023, month 11, day 13.
4. Compute: `2023 - 1957 = 66`. Since (11,13) ≥ (4,12), age stays 66.
5. Output: `FINISH(["66 years"])`.

## Success Indicators
- The agent issues a `GET` for the patient, extracts `birthDate`, performs the year‑difference logic, and returns `FINISH(["<age> years"])`.
- The returned age matches manual calculation for the given birthDate and current time.

## Failure Indicators
- The agent returns a hard‑coded age or omits the "years" unit.
- The agent fails to parse `birthDate` and still returns a value.
- The output contains extra text, numbers without units, or a JSON structure other than a single‑element array.
