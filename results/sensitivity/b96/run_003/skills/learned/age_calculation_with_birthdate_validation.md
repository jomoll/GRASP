---
description: Compute patient age only on explicit age queries, validate birthDate
  and return the age as a JSON array.
name: age_calculation_with_birthdate_validation
provenance:
  action: MODIFY
  epoch: 3
  fixes: 6
  parent_version: 2
  probe_score: 10
  regressions: 0
  triggering_sample_ids:
  - task2_26
  - task5_3
  - task9_11
  - task9_27
  - task10_8
  - task10_17
  - task9_20
  - task2_22
  - task2_28
  - task2_17
  update_cycle: 0
tags: []
version: 3
---

# Age Calculation with Birthdate Validation

## Pattern Description
You must compute a patient’s age **only** when the task explicitly asks for it (e.g., contains keywords like "age", "how old", "years old"). Before calculating, always verify that the `birthDate` field exists and is a valid ISO‑8601 date. The result must be returned as a JSON array containing a single integer (e.g., `FINISH([42])`). This ensures consistent answer formatting and prevents accidental use of raw integers.

## When to Use This Skill
- When a task description includes age‑related keywords and the instruction is to provide the patient’s age.
- The task provides a patient identifier (MRN) and expects a numeric age rounded down to the nearest year.
- The current time is supplied in the task context (e.g., `Current time: 2023-11-13T10:15:00+00:00`).

## Common Failure Patterns
- **Missing validation**: Using the `birthDate` without checking for its presence or format, leading to incorrect or undefined ages.
- **Wrong output type**: Returning a bare integer (`FINISH(42)`) instead of a JSON array (`FINISH([42])`).
- **Trigger missed**: Computing age for tasks that do not ask for it, causing unnecessary API calls.

## Recommended Patterns
**Pattern 1: Detect age query and validate birthDate**
1. Scan the task description for any of the keywords: `age`, `how old`, `years old`.
2. If none are found, **do not** apply this skill; let other skills handle the task.
3. Perform a `GET /Patient?identifier={MRN}`.
4. From the returned Bundle, locate the first entry’s `resource.birthDate`.
5. Verify that `birthDate` exists and matches the regex `^\d{4}-\d{2}-\d{2}$`.
6. If validation fails, abort the skill and let a fallback handle the request.

**Pattern 2: Compute age**
1. Parse the `birthDate` and the `Current time` from the task context as UTC dates.
2. Compute the difference in years, rounding down (i.e., `age = floor((current - birthDate) / 365.25 days)`).
3. Ensure the result is a non‑negative integer.

**Pattern 3: Return correctly formatted answer**
- Emit the result as a JSON array containing the integer: `FINISH([age])`.
- Do **not** include any surrounding text, units, or additional structure.

## Example Application
**Task:** "What's the age of the patient with MRN of S1152319?"

**Step‑by‑step:**
1. Detect the word "age" → trigger skill.
2. GET `http://localhost:8080/fhir/Patient?identifier=S1152319`.
3. Extract `birthDate` (e.g., `1957-04-12`).
4. Validate format – passes.
5. Compute age using context time `2023-11-13T10:15:00+00:00` → `66` years.
6. FINISH([66])

**CORRECT output:** `FINISH([66])`
**WRONG output:** `FINISH(66)` or `FINISH(["66"])`

## Success Indicators
- The agent returns `FINISH([<integer>])` with no extra characters.
- The integer matches the floor of the year difference between the provided current time and a valid `birthDate`.
- No age is computed for tasks lacking age‑related keywords.

## Failure Indicators
- Output is `FINISH(<integer>)` (bare integer) or includes quotes/strings.
- The skill runs but `birthDate` is missing or malformed, yet an age is still returned.
- Age is computed for a task that does not request it.
