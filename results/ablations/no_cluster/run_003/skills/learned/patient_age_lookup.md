---
description: "Extract a patient\u2019s age from the FHIR Patient resource and return\
  \ it as an integer"
name: patient_age_lookup
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - task9_22
  - task2_22
  - task9_1
  - task2_26
  - task2_1
  - task2_14
  - task2_6
  - task9_5
  - task2_9
  - task10_27
  update_cycle: 1
tags:
- age
- patient
- lookup
version: 1
---

# Patient Age Lookup

## Pattern Description
You must compute a patient’s age from the `birthDate` field of a FHIR `Patient` resource. The task will usually ask for the age of a patient identified by an MRN (or other identifier). Return the age as a plain integer (rounded down) inside a `FINISH([age])` call. This pattern isolates the date arithmetic from any downstream logic and guarantees a consistent numeric answer.

## When to Use This Skill
- When the instruction asks *"What’s the age of the patient with MRN of <identifier>?"*.
- When the instruction asks for a patient’s age based on a name + birthdate lookup that returns a `Patient` bundle.
- When the task expects a single integer answer (no surrounding text).

## Common Failure Patterns
- Using `effectiveDateTime` or `issued` instead of `birthDate`.
- Returning the age as a string (e.g., `FINISH(["45"])`).
- Including explanatory text in the `FINISH` payload.
- Forgetting to floor the result, yielding a fractional age.
- Not handling a missing `birthDate` field (should return `FINISH([-1])`).

## Recommended Patterns
**Pattern 1: Core age extraction**
1. Issue `GET {api_base}/Patient?identifier=<MRN>` (or the appropriate search parameters).
2. From the response bundle, locate the first entry’s `resource.birthDate` (ISO‑8601 date string, e.g., `1975-04-23`).
3. Parse the date and compute the difference in years between the current task time (provided in the task context) and the birth date.
4. Apply floor division to obtain an integer age.
5. Call `FINISH([age])` where `age` is the integer.

**CORRECT**: `FINISH([76])`
**WRONG**: `FINISH(["76"])` or `FINISH([76.4])`

**Pattern 2: Missing birthDate fallback**
- If the `Patient` resource does not contain a `birthDate`, call `FINISH([-1])` to signal that age cannot be computed.

**Pattern 3: Formatting rule**
- Ensure the `FINISH` payload is a JSON array containing a single numeric element, no extra whitespace or text.

## Example Application
**Task:** "What's the age of the patient with MRN of S2703270?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2703270`
2. Extract `birthDate` from `entry[0].resource.birthDate` → `1947-05-12`.
3. Current time from task context: `2023-11-13T10:15:00+00:00`.
4. Compute years: 2023 − 1947 = 76 (birthday already passed this year), floor → `76`.
5. `FINISH([76])`

## Success Indicators
- The agent outputs `FINISH([<integer>])` with no quotes around the number.
- The integer matches the calendar‑year difference rounded down.
- No additional text appears in the `FINISH` call.

## Failure Indicators
- The output contains a string or extra description (e.g., `FINISH(["76 years"])`).
- The age is off by one year because the birthday check was omitted.
- The skill returns `FINISH([-1])` when a valid `birthDate` is present.
