---
description: Strip trailing percent signs from Observation values and return a plain
  numeric result
name: percent_value_stripping
provenance:
  action: ADD
  blind_select: random
  epoch: 4
  fixes_unused: 3
  probe_score_unused: 0
  regressions_unused: 0
  triggering_sample_ids:
  - task10_13
  - task8_19
  - task9_5
  - task8_21
  - task2_17
  - task9_22
  - task5_7
  - task8_13
  - task5_3
  - task8_7
  update_cycle: 1
tags: []
version: 1
---

# Percent Value Stripping for Observation Results

## Pattern Description
You must treat any Observation result that is presented as a string containing a trailing percent sign (e.g., "5.7 %") as a plain numeric value. The clinical task often expects the value without the unit, so you should remove the percent sign and any surrounding whitespace, then convert the remaining text to a number (or a string representation of the number) before using it in the answer or downstream logic. This pattern applies to any lab or vital sign where the unit is expressed as a percent sign in the `valueString` or `valueQuantity.value` field.

## When to Use This Skill
- When a task asks for a numeric lab value (e.g., HbA1c, %FEV1, etc.) and the Observation payload contains a `valueString` like `"5.7 %"`.
- When the expected answer format is a bare number (or a JSON number) and the agent would otherwise return the string with the percent sign.
- When the Observation uses `valueQuantity.value` together with `valueQuantity.unit` set to "%" and the task expects only the numeric component.

## Common Failure Patterns
- Returning `FINISH(["5.7 %", "2023-07-07"])` instead of `FINISH([5.7, "2023-07-07"])`.
- Including the percent sign in the numeric field, causing type mismatches in downstream checks.
- Leaving whitespace (e.g., `"5.7 %"` → `"5.7 "`) which still fails strict numeric validation.

## Recommended Patterns
**Pattern 1: Core extraction and stripping**
1. Locate the Observation entry that matches the requested code.
2. Prefer `valueQuantity.value` if present; otherwise use `valueString`.
3. If the extracted text ends with a `%` (optionally preceded/followed by whitespace), remove the `%` and trim whitespace.
4. Convert the cleaned string to a number (e.g., `float(cleaned)`).
5. Use this numeric value in the answer array.

```text
CORRECT:  value = float(observation["valueString"].replace("%", "").strip())
WRONG:    value = observation["valueString"]   # leaves "%" intact
```

**Pattern 2: Fallback verification**
- If the Observation does not contain a `%` sign, fall back to the existing quantity extraction logic (e.g., `include_units_in_quantity_extraction`).
- If both `valueQuantity` and `valueString` are missing, raise a placeholder error and let the higher‑level task decide.

**Pattern 3: Formatting the final output**
- Construct the FINISH payload as a JSON array where the first element is the numeric value (no quotes) and the second element is the ISO‑8601 date string.
- Do **not** embed any unit text or extra explanatory strings.

## Example Application
**Task:** "What’s the last HbA1c (hemoglobin A1C) value in the chart for patient S6545016 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6545016`
2. From the returned Bundle, pick the most recent `entry.resource`.
3. Extract `valueString` → `"5.7 %"`.
4. Strip `%` and whitespace → `"5.7"` → `float(5.7)`.
5. Extract `effectiveDateTime` → `"2023-07-07"`.
6. `FINISH([5.7, "2023-07-07"])`.

**CORRECT output:** `FINISH([5.7, "2023-07-07"])`
**WRONG output:** `FINISH(["5.7 %", "2023-07-07"])`

## Success Indicators
- The FINISH array contains a bare number (no quotes) as the first element.
- No `%` character appears anywhere in the answer payload.
- Subsequent logic that checks numeric thresholds (e.g., >7.0) works without type errors.

## Failure Indicators
- The answer still includes the `%` sign or is a string instead of a number.
- The agent returns a mixed‑type array (e.g., `"5.7 %"` and date) causing downstream validation failures.
- The skill is not invoked when the Observation payload uses `valueQuantity.unit` = "%".

---
**Tags:** ["observation", "value_extraction", "percent", "lab"]
