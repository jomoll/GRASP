---
description: Add correct spacing for percent units and ensure unit formatting consistency
name: append_units_to_quantity
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task4_4
  - task10_13
  update_cycle: 0
tags:
- units
- formatting
version: 2
---

# Append Units To Quantity

## Pattern Description
You must attach the proper unit to a numeric lab value **with a single space** separating the number and the unit. This includes special handling for percent (`%`) where a space is required before the symbol. The goal is a clean, machine‑readable string that downstream logic can compare reliably.

## When to Use This Skill
- After extracting a raw numeric value from `valueQuantity.value`.
- When the task specifies a unit (e.g., "%", "mg/dL", "mmol/L").
- Before passing the value to any comparison, ordering, or FINISH step.

## Common Failure Patterns
- Producing `"5.0%"` (no space) instead of `"5.0 %"`.
- Concatenating the unit without converting it to a string, yielding `5.0%` (type mismatch).
- Adding extra whitespace (`"5.0  %"`).

## Recommended Patterns
**Pattern 1: Core unit appending**
1. Receive `value` (number) and `unit` (string) from the previous extraction step.
2. Trim any surrounding whitespace from `unit`.
3. If `unit == "%"`, set `formatted = f"{value} %"`.
4. Otherwise, set `formatted = f"{value} {unit}"`.
5. Return `formatted` for the next step or FINISH.

**Pattern 2: Validation**
- Verify that `formatted` matches the regex `^\d+(\.\d+)?\s+\S+$`.
- If it does not, raise a warning and fall back to the raw value.

**Pattern 3: Integration with Value Extraction**
- Combine this skill directly after `value_only_extraction` when the unit is missing or needs correction.

## Example Application
**Task:** "What’s the last HbA1C value in the chart for patient S2823623 and when was it recorded?"

**Step‑by‑step:**
1. Extract `value = 5.0` and `unit = "%"` from the Observation.
2. Apply the rule: because `unit == "%"`, produce `"5.0 %"`.
3. FINISH(["5.0 %", "2023-11-09T10:06:00+00:00"]).

**Correct output:** `FINISH(["5.0 %", "2023-11-09T10:06:00+00:00"])`
**Incorrect output:** `FINISH(["5.0%", "2023-11-09T10:06:00+00:00"])`

## Success Indicators
- The returned string contains a single space before the percent sign.
- All other units also have exactly one space separating number and unit.
- Downstream comparisons (e.g., `< 7 %`) succeed without parsing errors.

## Failure Indicators
- Output like `"5.0%"` or `"5.0  %"` appears.
- The FINISH payload contains a number without a unit when the task expects one.
- Regex validation fails, indicating malformed formatting.
