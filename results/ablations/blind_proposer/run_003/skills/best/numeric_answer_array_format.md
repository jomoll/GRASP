---
description: Ensures numeric answers are returned as JSON numbers, not quoted strings
name: numeric_answer_array_format
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 0
  fixes_unused: 13
  probe_score_unused: 12
  regressions_unused: 4
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task2_16
  - task3_1
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  update_cycle: 0
tags: []
version: 1
---

# Numeric Answer Array Format

## Pattern Description
You must guarantee that whenever a task asks for a numeric result—such as an age, a lab measurement, or any quantitative value—the final `FINISH` call returns a JSON array containing raw numbers (or a single number) rather than strings. This changes the agent’s answer‑formatting behavior by converting extracted numeric strings to proper JSON numeric types before finishing.

## When to Use This Skill
- The task description explicitly requests an integer or decimal value (e.g., "age", "value", "level", "mg/dL", "mmol/L").
- The expected answer is a single numeric value or a list of numeric values.
- The agent has already retrieved the relevant FHIR resource and extracted a value that can be parsed as a number.

## Common Failure Patterns
- `FINISH(["66"])` – age returned as a quoted string.
- `FINISH(["5.2"])` – lab value returned as a string.
- `FINISH(["-1"])` – sentinel for “not found” returned as a string.
- Mixing numbers and strings in the same array, e.g., `FINISH(["6.5%", "2022-03-08T08:14:00+00:00"])` when only the numeric part is required.

## Recommended Patterns
**Pattern 1: Core numeric conversion**
1. After extracting the value, attempt to parse it as a float/int.
2. If parsing succeeds, store the result in a variable `num_value` as a numeric type.
3. Call `FINISH([num_value])` (or `FINISH([num_value, other_numeric])` if multiple numbers are required).

CORRECT: `FINISH([66])`
WRONG:   `FINISH(["66"])`

**Pattern 2: Fallback sentinel handling**
- If the numeric value cannot be found, use the agreed sentinel (e.g., `-1`) **as a number**: `FINISH([-1])`.

**Pattern 3: Mixed numeric‑string responses**
- When a task also requires a date or unit string, separate the numeric and non‑numeric parts. Return only the numeric part in the array; include other data in a separate field or note, not as a quoted number.

## Example Application
**Task:** "What's the age of the patient with MRN of S2119664?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2119664`
2. Extract `birthDate` from the returned Patient resource.
3. Compute age = floor(current_date - birthDate in years) → `66` (numeric).
4. `FINISH([66])`

**Correct output:** `FINISH([66])`
**Wrong output:** `FINISH(["66"])`

## Success Indicators
- The `FINISH` payload contains numbers without surrounding quotes.
- No string literals appear where a numeric value is expected.
- The agent’s logs show a successful numeric parsing step before `FINISH`.

## Failure Indicators
- The `FINISH` payload shows quoted numbers (e.g., `"66"`).
- The agent reports a type‑mismatch error from downstream validation.
- The numeric sentinel (`-1`) appears as a string.
