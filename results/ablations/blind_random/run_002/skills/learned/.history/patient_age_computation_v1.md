---
description: "Compute a patient\u2019s age from birthDate using the provided current\
  \ time context"
name: patient_age_computation
provenance:
  action: ADD
  blind_select: random
  epoch: 0
  fixes_unused: 3
  probe_score_unused: 5
  regressions_unused: 0
  triggering_sample_ids:
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task4_28
  - task4_7
  - task10_8
  - task10_15
  - task4_15
  update_cycle: 0
tags:
- age
- patient
- computation
version: 1
---

# Patient Age Computation from birthDate

## Pattern Description
You must derive a patient’s age dynamically instead of using hard‑coded placeholders.  The reusable capability is to read the `birthDate` field from a FHIR `Patient` resource, compare it to the *current time* supplied in the task context, and return the age rounded **down** to the nearest whole year.  This pattern applies to any task that asks for a patient’s age given an MRN (or other identifier) and provides a reference timestamp.

## When to Use This Skill
- When the instruction is "What’s the age of the patient with MRN of <identifier>?" **and** the task context includes a line like `It's <ISO‑timestamp> now`.
- When the agent has already performed a `GET .../Patient?identifier=<id>` and received a Bundle containing a `Patient` resource with a `birthDate` element.
- When the expected answer format is a JSON array containing a single integer string, e.g. `FINISH(["45"])`.

## Common Failure Patterns
- Returning a static placeholder age (e.g., `"82"`) regardless of the patient’s actual `birthDate`.
- Using the wrong field such as `age` or `period` instead of `birthDate`.
- Forgetting to round down (e.g., returning `45.9` or a string with a decimal).
- Ignoring the task‑provided current time and using the system clock instead.

## Recommended Patterns
**Pattern 1: Core age calculation**
1. **Locate the Patient resource** – In the Bundle response, find the first entry where `resource.resourceType == "Patient"`.
2. **Extract `birthDate`** – Read `entry.resource.birthDate` (ISO‑8601 date, e.g., `1950-04-23`).
3. **Parse the current time** – From the task context string, extract the ISO‑8601 timestamp after the phrase `It's` (e.g., `2023-11-13T10:15:00+00:00`).
4. **Compute the year difference**:
   ```
   age = current_year - birth_year
   if (current_month, current_day) < (birth_month, birth_day):
       age -= 1
   ```
5. **Round down** – The integer `age` is already floored by the step above.
6. **Return** – Call `FINISH(["{age}"])` where `{age}` is the integer converted to a string.

**Pattern 2: Fallback / verification**
- If the Bundle has `total == 0` or the `Patient` entry lacks a `birthDate`, abort with `FINISH(["Patient birth date not available"])`.
- If the task context does not contain a parsable timestamp, fall back to the system clock but log a warning.

**Pattern 3: Output formatting**
- The final JSON array must contain **exactly one string element** representing the integer age.
- Do **not** include units, explanatory text, or additional fields.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"
**Context:** "It's 2023-11-13T10:15:00+00:00 now."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Response Bundle contains:
   ```json
   {"resourceType":"Patient","birthDate":"1963-01-29"}
   ```
3. Extract `birthDate = 1963-01-29`.
4. Current time = `2023-11-13T10:15:00+00:00` → year 2023, month 11, day 13.
5. Compute age:
   - 2023 - 1963 = 60
   - (11,13) is after (1,29) → no decrement.
   - Age = **60**.
6. `FINISH(["60"])`

**Correct output:** `FINISH(["60"])`
**Incorrect output examples:**
- `FINISH(["82"])` – static placeholder.
- `FINISH(["60 years"])` – extra text.
- `FINISH([60])` – not a string.

## Success Indicators
- The agent returns `FINISH(["<integer>"])` where the integer matches the calculated age.
- No placeholder numbers appear in the output.
- The calculation respects the task‑provided current timestamp.

## Failure Indicators
- Output contains a hard‑coded number unrelated to the patient’s `birthDate`.
- The result is not a string or includes units/text.
- The agent skips the age calculation and returns immediately after the GET.
