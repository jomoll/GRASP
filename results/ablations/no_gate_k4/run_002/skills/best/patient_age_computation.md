---
description: Compute patient age from birthDate after a verified Patient GET, handling
  rounding and missing data
name: patient_age_computation
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task4_27
  - task9_9
  - task5_16
  - task9_27
  - task2_26
  - task5_19
  - task2_16
  - task10_24
  - task9_14
  - task10_21
  update_cycle: 0
tags: []
version: 3
---

# Patient Age Computation (Robust)

## Pattern Description
You must calculate a patient’s age using the `birthDate` field from a **validated** Patient resource retrieved via a prior GET request. The calculation should use the task’s provided current timestamp, round down to the nearest whole year, and return the result as a scalar integer inside a JSON array.

## When to Use This Skill
- After a successful `GET .../Patient?...` that returns a Bundle with at least one Patient entry.
- When the task explicitly asks for the **age** of a patient identified by MRN or name/DOB.
- When the task supplies a reference current time (e.g., "It's 2023-11-13T10:15:00+00:00 now").

## Common Failure Patterns
- Using the wrong field (`effectiveDateTime`, `issued`) instead of `birthDate`.
- Returning the age as a quoted string or within a nested array.
- Failing to round down (e.g., returning a float or ceiling value).
- Computing age when the GET response contains no Patient entry.

## Recommended Patterns
**Pattern 1: Validate GET response**
1. Ensure the previous GET response is a Bundle with `total >= 1`.
2. Extract the first Patient resource: `patient = response.entry[0].resource`.
3. Verify `patient.birthDate` exists; if missing, abort with `FINISH(["Patient birthDate missing"])`.

**Pattern 2: Compute age**
1. Parse `patient.birthDate` (ISO‑8601 date).
2. Parse the task’s current time (provided in the context).
3. Calculate the difference in years, subtract one if the current month/day is before the birth month/day.
4. The result is an integer `age`.

**Pattern 3: Output formatting**
- Return exactly `FINISH([age])` where `age` is an integer, no quotes.
- Example CORRECT:
  ```
  FINISH([86])
  ```
- WRONG examples:
  ```
  FINISH(["86"])   // string instead of number
  FINISH([[86]])    // nested array
  FINISH([86.5])    // non‑integer
  ```

## Example Application
**Task:** "What's the age of the patient with MRN of S1152319?"

**Step‑by‑step:**
1. Prior GET confirmed a Patient with `birthDate = "1937-04-12"`.
2. Current time: `2023-11-13T10:15:00+00:00`.
3. Compute years: 2023‑1937 = 86; since 11‑13 is after 04‑12, no subtraction.
4. FINISH with `FINISH([86])`.

## Success Indicators
- Age is computed from `birthDate` and current time.
- Output is a single‑level array containing an integer.
- No extra quotes or nesting.

## Failure Indicators
- Age derived from any field other than `birthDate`.
- Output contains strings, floats, or nested arrays.
- FINISH is called despite a missing or empty Patient GET response.

---

**Integration Note:** This skill should be used **after** the enhanced `require_fhir_query_before_finish` ensures a proper Patient GET has occurred.
