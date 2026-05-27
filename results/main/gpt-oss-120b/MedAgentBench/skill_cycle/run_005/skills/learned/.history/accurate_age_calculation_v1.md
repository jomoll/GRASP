---
description: Compute patient age correctly, handling birthdays that have not yet occurred
  this year
name: accurate_age_calculation
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task10_21
  - task1_7
  - task2_9
  - task10_13
  - task5_16
  - task9_9
  - task9_1
  - task9_14
  - task9_20
  - task1_15
  update_cycle: 0
tags:
- age
- date
- patient
- calculation
version: 1
---

# Accurate Age Calculation

## Pattern Description
You must calculate a patient’s age from the `birthDate` element of a `Patient` resource, using the reference time supplied in the task context (e.g. "It's 2023-11-13T10:15:00+00:00 now"). The calculation must round down to the nearest whole year and must subtract one year when the patient’s birthday for the current year has not yet occurred. This prevents the common off‑by‑one error that occurs when only the year difference is used.

## When to Use This Skill
- When a task asks *"What’s the age of the patient with MRN of <identifier>?"* and the context includes a current timestamp.
- When the task explicitly states that the answer should be an integer rounded down.
- When the `Patient` resource is retrieved via `GET .../Patient?identifier=<MRN>` and contains a `birthDate` field.

## Common Failure Patterns
- Using `currentYear - birthYear` without checking month/day, yielding an age that is one year too high.
- Returning the raw `age` field from a FHIR `Observation` (which may be absent) instead of computing it.
- Forgetting to parse the task‑provided current time, and defaulting to the system clock.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. After the `GET Patient` call, locate the `birthDate` string (format `YYYY-MM-DD`).
2. Extract the reference timestamp from the task context (the ISO‑8601 string after "now").
3. Parse both dates into year, month, day components.
4. Compute `age = currentYear - birthYear`.
5. If `(currentMonth, currentDay) < (birthMonth, birthDay)`, decrement `age` by 1.
6. Convert `age` to a string and place it inside the FINISH array.

**CORRECT** example: `FINISH(["47"])`
**WRONG** example: `FINISH(["48"])` when the birthday is after the current date.

**Pattern 2: Fallback / verification**
- If `birthDate` is missing, return `FINISH(["unknown"])` and log a warning.
- If the task context does not contain a timestamp, fall back to the system time but note the assumption.

**Pattern 3: Output formatting**
- The FINISH payload must be a JSON array containing a single string representing the integer age.
- Do **not** include additional text, units, or explanations.

## Example Application
**Task:** "What's the age of the patient with MRN of S0722219?"
**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S0722219`
2. From the response extract `"birthDate": "1975-12-01"`.
3. Task context provides current time `2023-11-13T10:15:00+00:00` → year=2023, month=11, day=13.
4. Compute `age = 2023 - 1975 = 48`. Since (11,13) < (12,01), decrement → `age = 47`.
5. `FINISH(["47"])`.

## Success Indicators
- The returned age matches manual calculation (e.g., 47 for the example above).
- No off‑by‑one values appear in the FINISH output for any age‑query task.

## Failure Indicators
- FINISH returns a number that is exactly one year higher than the correct age.
- The skill is skipped and the agent simply returns the year difference.
- The output contains extra text, units, or a non‑integer value.
