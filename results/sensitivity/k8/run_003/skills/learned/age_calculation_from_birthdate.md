---
description: Compute patient age from birthDate using the task's reference time, rounding
  down to an integer
name: age_calculation_from_birthdate
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 13
  regressions: 2
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task2_16
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  - task2_9
  update_cycle: 0
tags: []
version: 1
---

# Age Calculation from Patient Birthdate

## Pattern Description
You must calculate a patient’s age by extracting the `birthDate` field from a `Patient` resource and comparing it to the reference date supplied in the task context (e.g., "Current time: 2023-11-13T10:15:00+00:00"). The result must be an integer representing full years elapsed, rounded down. This pattern replaces any ad‑hoc or hard‑coded age logic and guarantees that the same reference time is used for every age query.

## When to Use This Skill
- When the instruction asks *"What’s the age of the patient with MRN of <identifier>?"* and the task context includes a `Current time` timestamp.
- After you have performed a `GET /Patient?identifier=<MRN>` and received a Bundle containing a `Patient` resource.
- When the `Patient` resource includes a `birthDate` element (format `YYYY‑MM‑DD`).

## Common Failure Patterns
- Using the system clock instead of the `Current time` supplied in the task, leading to off‑by‑one errors.
- Treating `birthDate` as a string and returning it directly (e.g., `FINISH(["1943-05-20"])`).
- Performing simple subtraction of years without accounting for month/day, producing ages that are too high.
- Returning the age as a string inside an array of strings (e.g., `FINISH(["80"])`) instead of a numeric array (e.g., `FINISH([80])`).

## Recommended Patterns
**Pattern 1: Core age calculation**
1. Locate the patient entry: `bundle.entry[0].resource`.
2. Extract `birthDate` (e.g., `patient.birthDate`).
3. Parse the reference timestamp from the task context string. Look for the substring `"Current time: "` and parse the following ISO‑8601 datetime.
4. Convert both dates to a comparable date object (ignore time‑zone offsets for year/month/day comparison).
5. Compute the year difference: `refYear - birthYear`.
6. If `refMonthDay` is before `birthMonthDay`, subtract 1.
7. The final integer is the patient’s age.

**Pattern 2: Fallback / verification**
- If `birthDate` is missing, return `FINISH(["unknown"])`.
- If the task context does not contain a `Current time`, fall back to the system’s current UTC time but log a warning.

**Pattern 3: Output formatting**
- Return the age as a numeric array: `FINISH([<age>])`.
- Do **not** wrap the number in quotes.
- Example correct output: `FINISH([80])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"
**Context:** "It's 2023-11-13T10:15:00+00:00 now, and the answer should be rounded down to an integer."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Receive Bundle → `patient = bundle.entry[0].resource`.
3. `birthDate = patient.birthDate` → "1943-05-20".
4. Parse reference time → `2023-11-13T10:15:00+00:00`.
5. Year diff = 2023‑1943 = 80.
6. Reference month/day (Nov 13) is after birth month/day (May 20) → no subtraction.
7. Output: `FINISH([80])`.

## Success Indicators
- The FINISH payload is a single‑element numeric array.
- The number matches manual age calculation using the supplied reference date.
- No warning about missing `birthDate` or reference time is logged.

## Failure Indicators
- FINISH returns a string array (e.g., `FINISH(["80"])`).
- Age is off by one because month/day was ignored.
- The system clock was used instead of the task’s `Current time`.
- The skill aborts without returning an answer when `birthDate` is present.
