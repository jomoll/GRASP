---
description: Extract patient age and return it as a bare integer, not a quoted string
name: return_age_as_number
provenance:
  action: ADD
  blind_select: random
  epoch: 2
  fixes_unused: 6
  probe_score_unused: 9
  regressions_unused: 1
  triggering_sample_ids:
  - task10_20
  - task10_27
  - task9_28
  - task9_27
  - task1_10
  - task5_17
  - task9_8
  - task3_12
  - task2_6
  - task4_11
  update_cycle: 0
tags: []
version: 1
---

# Return Patient Age as Number

## Pattern Description
You must compute a patient’s age from the `birthDate` field of a `Patient` resource and return the result as a plain numeric value (e.g., `FINISH([42])`).  The answer should never be wrapped in quotes or placed inside a string array.  This pattern is reusable for any task that asks for a patient’s age given an identifier (MRN, SSN, etc.).

## When to Use This Skill
- The task description contains phrases like *"What’s the age of the patient…"* or *"How old is the patient…"*.
- The task provides a patient identifier (e.g., `identifier=S1234567`).
- The context may specify rounding (usually round down to the nearest whole year).

## Common Failure Patterns
- Returning `FINISH(["39"])` – the age is a quoted string inside an array.
- Returning a free‑text sentence such as `FINISH(["Patient is 39 years old"])`.
- Omitting the `FINISH` wrapper or using a different JSON structure.

## Recommended Patterns
**Pattern 1: Core extraction and calculation**
1. Issue a GET request for the patient: `GET {api_base}/Patient?identifier={MRN}`.
2. From the first entry in the returned Bundle, read `entry[0].resource.birthDate` (ISO‑8601 date string).
3. Parse the current time supplied in the task context (e.g., `2023-11-13T10:15:00+00:00`).
4. Compute the age in whole years: `age = floor((currentDate - birthDate) / 365.25 days)`.
5. If `birthDate` is missing, set `age = -1`.
6. **Output** exactly as:
   ```
   FINISH([age])
   ```
   where `age` is an integer literal, **no quotes**.

**Pattern 2: Fallback when patient not found**
- If the Bundle `total` is `0` or the response is empty, output `FINISH([-1])`.

**Pattern 3: Formatting rule**
- Do not include any explanatory text, units, or additional array elements.
- Ensure the JSON array contains a single numeric element.

## Example Application
**Task:** "What's the age of the patient with MRN of S1733937?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S1733937`
2. Response contains `birthDate: "1984-07-22"`.
3. Current time from context: `2023-11-13T10:15:00+00:00`.
4. Compute age: 2023‑1984 = 39 (birthday already passed this year), so `age = 39`.
5. Return:
   ```
   FINISH([39])
   ```

## Success Indicators
- The final agent output is `FINISH([<integer>])` with the integer not quoted.
- The integer matches the floor of the year difference between the context time and the patient’s `birthDate`.

## Failure Indicators
- The output contains quotes around the number, e.g., `FINISH(["39"])`.
- The output includes extra text or units.
- The agent returns an empty array or a non‑numeric value.
