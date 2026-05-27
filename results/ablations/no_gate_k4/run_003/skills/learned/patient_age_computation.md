---
description: "Fix age calculation to correctly compute whole\u2011year age from birthDate\
  \ and task current time"
name: patient_age_computation
provenance:
  action: MODIFY
  epoch: 0
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  - task5_16
  update_cycle: 1
tags: []
version: 2
---

# Patient Age Computation

## Pattern Description
You must compute a patient’s age in whole years using the `birthDate` field from the Patient resource and the *current time* supplied in the task context. The calculation must respect calendar dates (including leap years) and round **down** to the nearest integer, matching typical clinical age reporting. This skill is reusable for any task that asks for a patient’s age.

## When to Use This Skill
- When a task asks “What’s the age of the patient …?” and provides a current timestamp in the task description.
- When the task supplies a `Patient` bundle and you need to return an integer age.
- When the `birthDate` field is present but the agent previously returned an incorrect value (e.g., off by one year or using the wrong field).

## Common Failure Patterns
- Using `effectiveDateTime` or the time of the GET request instead of the task‑provided current time.
- Subtracting years directly (`currentYear - birthYear`) without adjusting for whether the birthday has occurred this year.
- Ignoring time‑zone offsets, leading to off‑by‑one‑day errors.
- Returning the raw string `birthDate` or a floating‑point age instead of an integer.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. From the Patient bundle, locate `entry[0].resource.birthDate` (ISO‑8601 date, e.g., `1975-04-23`).
2. Parse the task context to extract the current timestamp (e.g., `2023-11-13T10:15:00+00:00`).
3. Convert both strings to date objects (ignore the time component for the birth date; keep the full datetime for the current time).
4. Compute `age = currentYear - birthYear`.
5. If the current month‑day is **before** the birth month‑day, decrement `age` by 1.
6. Return `age` as an integer inside a JSON array: `FINISH([age])`.

**Pattern 2: Fallback / verification**
- If `birthDate` is missing, return `FINISH(["unknown"])` or raise a clear error.
- Verify that the computed `age` is non‑negative; if negative, treat as a data error and return `FINISH(["invalid"]`).

**Pattern 3: Formatting**
- Always output a JSON array with a single integer element, no extra text or units.
- Example correct output: `FINISH([45])`.
- Example wrong output: `FINISH(["45 years"])` or `FINISH([45.0])`.

## Example Application
**Task:** "What's the age of the patient with MRN of S1733937? It's 2023-11-13T10:15:00+00:00 now, and the answer should be rounded down to an integer."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S1733937`
2. Response contains `"birthDate":"1958-06-20"`.
3. Parse current time `2023-11-13T10:15:00+00:00` → year = 2023, month = 11, day = 13.
4. Compute preliminary age: `2023 - 1958 = 65`.
5. Since current month‑day (Nov 13) is **after** birth month‑day (Jun 20), keep `age = 65`.
6. `FINISH([65])`.

## Success Indicators
- The agent returns a single integer inside a JSON array.
- The integer matches manual calculation (e.g., using a calendar).
- No extra strings, units, or decimal points are present.

## Failure Indicators
- Output contains a string, unit, or decimal (e.g., `"65 years"`, `65.0`).
- Age is off by one year (often due to missing birthday‑adjustment).
- The agent uses the request timestamp instead of the task‑provided current time.
- The skill aborts without returning a value when `birthDate` exists.
