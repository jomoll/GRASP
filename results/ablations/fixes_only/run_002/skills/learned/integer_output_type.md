---
description: Ensures numeric answers (e.g., ages) are returned as raw integers, not
  quoted strings.
name: integer_output_type
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 9
  regressions: 1
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
tags:
- formatting
- integer_output
version: 1
---

# Integer Output Type

## Pattern Description
You must always return numeric values (such as ages, counts, or scores) as raw integers inside the FINISH list, without surrounding quotation marks. This prevents downstream consumers from having to parse strings and guarantees type‑correct responses. The rule applies to any task that explicitly asks for a rounded‑down integer value.

## When to Use This Skill
- When the instruction asks for an age, count, or any integer‑type answer (e.g., "What's the age of the patient with MRN of S12345?").
- When the task context specifies that the answer should be "rounded down to an integer".
- When you have already retrieved the necessary data (e.g., a Patient resource) and are about to format the final answer.

## Common Failure Patterns
- Returning `FINISH(["60"])` – the integer is wrapped in a JSON string.
- Returning `FINISH(["42 years"])` – extra text or units are included.
- Returning a floating‑point number when the spec requires an integer (e.g., `FINISH([60.0])`).

## Recommended Patterns
**Pattern 1: Core integer conversion strategy**
1. After extracting the numeric value (e.g., age in years), ensure it is a Python/JS number, not a string.
2. If the value is a string, cast it: `age_int = int(float(value_string))`.
3. Apply `math.floor` (or integer division) to round down any fractional part.
4. Construct the FINISH payload using the raw integer:
   ```
   FINISH([{age_int}])
   ```
   *Correct:* `FINISH([60])`
   *Wrong:* `FINISH(["60"])` or `FINISH(["60 years"])`

**Pattern 2: Fallback when conversion fails**
- If the extracted field is missing or cannot be parsed, raise a clear error or return a predefined placeholder (e.g., `FINISH(["Data unavailable"])`) rather than guessing a stringified number.

**Pattern 3: Formatting rule**
- The FINISH list must contain **only** the integer value (or a single string placeholder). No additional text, units, or commas are allowed.

## Example Application
**Task:** "What's the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. From the returned Bundle, locate `entry[0].resource.birthDate` (e.g., `"1963-04-12"`).
3. Compute age using the current time provided in the task context (`2023-11-13T10:15:00+00:00`).
   ```
   from datetime import datetime
   birth = datetime.strptime(birthDate, "%Y-%m-%d")
   now = datetime.strptime(context_time, "%Y-%m-%dT%H:%M:%S%z")
   age = now.year - birth.year - ((now.month, now.day) < (birth.month, birth.day))
   ```
4. Cast and floor: `age_int = int(age)`.
5. Return `FINISH([{age_int}])`.

**Correct output:** `FINISH([60])`
**Wrong output:** `FINISH(["60"])`

## Success Indicators
- The FINISH payload contains a single integer without quotes.
- The integer matches the expected age when manually calculated from the birthDate and context time.
- No extra text or units appear in the output.

## Failure Indicators
- The output list contains a quoted string (e.g., `"60"`).
- The output includes units or explanatory text (e.g., `"60 years"`).
- The agent returns a floating‑point number when an integer is required.
