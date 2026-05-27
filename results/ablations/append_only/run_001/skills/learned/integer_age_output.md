---
description: Ensures ages are returned as raw integers, not JSON strings, for patient
  age queries.
name: integer_age_output
provenance:
  action: ADD
  epoch: 0
  fixes: 6
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  update_cycle: 1
tags:
- age
- integer_output
- formatting
version: 1
---

# Integer Age Output Formatting

## Pattern Description
You must return a patient’s age as a plain integer inside a FINISH call, **without** wrapping the number in quotes or an array of strings. This pattern applies to any task that asks for the age of a patient (e.g., "What’s the age of the patient with MRN of …?") where the context supplies the current date‑time. Compute the age by subtracting the patient’s `birthDate` from the provided current time, round down to the nearest whole year, and output the result as `FINISH([<age>])`.

## When to Use This Skill
- When a task description explicitly requests the patient’s age.
- When the task context includes a current timestamp (e.g., "It's 2023-11-13T10:15:00+00:00 now").
- When the agent has already performed a `GET /Patient?identifier=MRN` request and received a Bundle containing a `Patient` resource with a `birthDate` field.

## Common Failure Patterns
- Returning `FINISH(["75"])` – age wrapped in a JSON string.
- Returning `FINISH([75.0])` – floating‑point number instead of integer.
- Omitting the `FINISH` wrapper or returning a free‑text sentence.
- Using the wrong date field (e.g., `deceasedDateTime`) for age calculation.

## Recommended Patterns
**Pattern 1: Core age extraction and formatting**
1. Locate the `Patient` entry in the Bundle (`entry[0].resource`).
2. Read the `birthDate` string (format `YYYY-MM-DD`).
3. Parse the current time from the task context (ISO‑8601).
4. Compute the year difference, subtract one if the current month/day is before the birth month/day.
5. Ensure the result is an integer type.
6. Call `FINISH([<age>])` **without quotes**.

   CORRECT: `FINISH([75])`
   WRONG: `FINISH(["75"])` or `FINISH([75.0])`

**Pattern 2: Fallback when birthDate missing**
- If the `Patient` resource lacks a `birthDate`, respond with `FINISH(["unknown"])` (string is allowed only for the literal "unknown").

**Pattern 3: Validation before finishing**
- Verify that the computed age is a non‑negative integer.
- If the calculation yields a negative value, treat it as an error and return `FINISH(["invalid age"])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2450227?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2450227`
2. Receive Bundle; extract `birthDate` = `1948-04-12`.
3. Context provides current time `2023-11-13T10:15:00+00:00`.
4. Compute age: 2023‑1948 = 75; current month/day (Nov 13) is after Apr 12, so age = 75.
5. Output `FINISH([75])`.

**Correct output:** `FINISH([75])`
**Incorrect output:** `FINISH(["75"])`

## Success Indicators
- The FINISH call contains a single integer element, no quotes.
- The integer matches the expected age based on the supplied dates.
- No additional explanatory text is included in the FINISH payload.

## Failure Indicators
- FINISH payload contains a string representation of the number.
- The age is off by one year (incorrect handling of month/day).
- The agent returns free‑text instead of the FINISH call.
- The agent fails to call FINISH at all.
