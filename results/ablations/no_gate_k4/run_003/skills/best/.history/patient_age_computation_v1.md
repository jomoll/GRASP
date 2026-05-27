---
description: "Compute a patient\u2019s age in whole years from the birthDate field\
  \ and the task\u2019s current time."
name: patient_age_computation
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Patient Age Computation from Birthdate

## Pattern Description
You must derive a patient’s age by extracting the `birthDate` element from a FHIR `Patient` resource and calculating the number of full years elapsed between that date and the reference time supplied in the task context. This reusable pattern replaces any hard‑coded or guessed age values and guarantees that the answer is always consistent with the patient’s actual birthdate and the current timestamp.

## When to Use This Skill
- When the task asks *"What’s the age of the patient with MRN of <identifier>?"*.
- When the task provides a *current time* in the context (e.g., `2023-11-13T10:15:00+00:00`).
- After you have performed a `GET /Patient?identifier=<MRN>` and received a Bundle containing a `Patient` resource.

## Common Failure Patterns
- Returning a static number (e.g., `FINISH(["80"])`) without looking at the patient’s `birthDate`.
- Using the wrong field such as `age` or `period` that does not exist on the Patient resource.
- Forgetting to round down to the nearest whole year, resulting in a fractional age.
- Ignoring the task‑provided current time and using the system clock, which may differ from the expected reference.

## Recommended Patterns
**Pattern 1: Extract and parse birthDate**
1. From the Bundle response, locate the first entry’s `resource.birthDate` (ISO‑8601 date string, e.g., `1945-09-20`).
2. Parse the string into a date object.
3. Retrieve the reference time from the task context (`Current time: <ISO‑timestamp>`). Parse it as a date‑time.
4. Compute the difference in years:
   - If the month/day of the reference time is before the month/day of the birthDate, subtract one year.
   - Otherwise, use the simple year difference.
5. **Output** the integer as a JSON string inside `FINISH(["<age>"])`.

**Pattern 2: Fallback when birthDate missing**
- If `birthDate` is absent or not a valid ISO date, respond with `FINISH(["unknown"])` and optionally log a note.

**Pattern 3: Formatting rule**
- The final answer must be a JSON array containing a single string representing the integer age, e.g., `FINISH(["57"])`.
- Do **not** include any extra text, units, or explanations.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"
**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Response contains `"birthDate":"1963-04-12"`.
3. Task context supplies `Current time: 2023-11-13T10:15:00+00:00`.
4. Year difference = 2023 − 1963 = 60. Since 11‑13 (Nov 13) is after 04‑12 (Apr 12), age = 60.
5. `FINISH(["60"])`.

## Success Indicators
- The agent extracts `birthDate` from the Patient resource.
- The computed age matches a manual calculation using the same reference time.
- The output format is exactly `FINISH(["<integer>"])`.

## Failure Indicators
- The agent returns a hard‑coded number or any value not derived from `birthDate`.
- The output contains extra words, units, or is not a JSON array of a single string.
- The computed age is off by one year because the month/day comparison was omitted.
