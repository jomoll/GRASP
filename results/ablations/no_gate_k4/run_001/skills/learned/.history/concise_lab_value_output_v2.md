---
description: Force FINISH to return a single scalar lab value with unit instead of
  an array
name: concise_lab_value_output
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_16
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags:
- formatting
- lab_output
version: 2
---

# concise_lab_value_output

## Pattern Description
You must ensure that any lab Observation answer is emitted as a plain scalar string (e.g., `4.7 mmol/L`) rather than wrapped in a JSON array. This pattern applies to all tasks that request a lab value and expect the result to be directly consumable by downstream logic (e.g., threshold checks, order decisions). By normalising the output format you avoid type‑mismatch errors in later processing.

## When to Use This Skill
- When a task asks for "the most recent potassium level" or any other lab value.
- When the agent has already performed a GET /Observation and extracted `valueQuantity.value` and `valueQuantity.unit`.
- Immediately before calling `FINISH` with the lab result.

## Common Failure Patterns
- `FINISH(["4.7 mmol/L"])` – the value is inside an array.
- `FINISH([{"value":4.7,"unit":"mmol/L"}])` – complex object instead of plain string.
- Returning the raw `valueQuantity` object without converting to a readable string.

## Recommended Patterns
**Pattern 1: scalar output rule**
1. After extracting `valueQuantity.value` and `valueQuantity.unit`, concatenate them with a single space: `value_str = f"{value}{' ' if unit else ''}{unit}"`.
2. Call `FINISH([value_str])` **only if** `value_str` is a plain string, **not** an array of strings.
3. Verify the type: if the result is a list, flatten it to the first element before finishing.

**Pattern 2: fallback when extraction fails**
- If the Observation bundle has no entries, call the `missing_observation_placeholder` skill to produce a sentinel value (e.g., `-1` or `"no result"`).

**Pattern 3: formatting check**
- Ensure the final JSON sent to the user is exactly `FINISH(["<value> <unit>"])` with no extra whitespace or punctuation.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level."

**Step‑by‑step:**
1. `GET http://.../Observation?code=K&patient=S3228213`.
2. From the first entry, read `valueQuantity.value = 4.7` and `valueQuantity.unit = "mmol/L"`.
3. Build `result = f"{value} {unit}"` → `"4.7 mmol/L"`.
4. `FINISH([result])` → `FINISH(["4.7 mmol/L"])`.

**CORRECT output:** `FINISH(["4.7 mmol/L"])`
**WRONG output:** `FINISH(["[\"4.7 mmol/L\"]"])` (double‑wrapped array).

## Success Indicators
- The agent’s final `FINISH` call contains a single‑element JSON array whose element is a plain string with a numeric value and unit.
- Subsequent skills that read the result (e.g., threshold checks) can treat the payload as a string without type errors.

## Failure Indicators
- `FINISH` payload is an array of arrays or objects.
- The string includes extra brackets, quotes, or JSON‑encoded characters.
- Downstream logic raises a type‑mismatch exception when comparing the lab value.
