---
description: Compute patient age from birthDate using the task's current time context
name: accurate_age_calculation
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Accurate Age Calculation from Birthdate

## Pattern Description
You must derive a patient’s age by extracting the `birthDate` field from a FHIR `Patient` resource and calculating the difference to the *current time* supplied in the task context. This avoids hard‑coded or static ages and ensures the answer is always up‑to‑date. The calculation should be rounded **down** to the nearest whole year, matching typical clinical conventions.

## When to Use This Skill
- When the instruction asks *"What’s the age of the patient with MRN of <identifier>?"*.
- When the task context includes a line like `Current time: 2023-11-13T10:15:00+00:00` (or any ISO‑8601 timestamp).
- After you have performed a `GET {api_base}/Patient?identifier=<MRN>` and received a Bundle with a single Patient entry.

## Common Failure Patterns
- Returning a hard‑coded number (e.g., `FINISH(["50"])`).
- Using the wrong field such as `id` or `identifier` instead of `birthDate`.
- Ignoring the task‑provided current time and using the system clock.
- Outputting a narrative string instead of a plain integer array (e.g., `FINISH(["Patient is 50 years old"])`).

## Recommended Patterns
**Pattern 1: Extract and parse birthDate**
1. From the Bundle response, locate `entry[0].resource.birthDate` (ISO‑8601 date, e.g., `1973-04-22`).
2. Parse this string into a date object.
3. From the task context, extract the `Current time` timestamp (ISO‑8601, e.g., `2023-11-13T10:15:00+00:00`).
4. Parse the current time into a date object.
5. Compute the year difference: `age = current.year - birth.year`.
6. If `current.month < birth.month` **or** (`current.month == birth.month` **and** `current.day < birth.day`), decrement `age` by 1.
7. Ensure `age` is a non‑negative integer.

**Pattern 2: Fallback / verification**
- If `birthDate` is missing or not a valid date, abort with `FINISH(["Patient birth date unavailable"])`.
- If the task context does not contain a `Current time` line, fall back to the system clock but log a warning (still compute age).

**Pattern 3: Output formatting**
- Return the age as a JSON array containing a single stringified integer: `FINISH(["<age>"])`.
- Do **not** include any additional text, units, or narrative.

## Example Application
**Task:** "What's the age of the patient with MRN of S2863714?"
**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2863714`
2. Response contains `"birthDate":"1973-04-22"`.
3. Task context provides `Current time: 2023-11-13T10:15:00+00:00`.
4. Parse dates → birth = 1973‑04‑22, now = 2023‑11‑13.
5. `age = 2023 - 1973 = 50`. Since November (11) > April (4), no decrement.
6. `FINISH(["50"])`.

**Correct output:** `FINISH(["50"])`
**Incorrect output examples:**
- `FINISH(["Patient is 50 years old"])`
- `FINISH([50])` (missing quotes)
- `FINISH(["50.0"])` (non‑integer string)

## Success Indicators
- The agent extracts `birthDate` and uses the task‑provided current time.
- The final `FINISH` call contains a single quoted integer string.
- The computed age matches manual calculation.

## Failure Indicators
- The output contains extra words, units, or a numeric value without quotes.
- The age is static across different patients or tasks.
- The agent uses `id`, `identifier`, or any field other than `birthDate` for the calculation.

---
*Tags:* ["age","calculation","patient","birthDate"]
