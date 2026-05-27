---
description: Extend handling to observations that exist but lack a usable numeric
  value
name: handle_missing_observation_numeric_placeholder
provenance:
  action: MODIFY
  epoch: 2
  fixes: 6
  parent_version: 1
  probe_score: 7
  regressions: 2
  triggering_sample_ids:
  - task10_20
  - task10_27
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task2_6
  - task5_16
  - task9_11
  update_cycle: 0
tags:
- observation
- numeric_extraction
- missing_value
version: 2
---

# Handle Missing or Non‑numeric Observation Values

## Pattern Description
You must ensure that any lab Observation you query returns a clean numeric result for downstream decision logic. If the Observation bundle is empty **or** the first matching Observation does not contain a parsable numeric value (e.g., missing `valueQuantity.value`, `valueDecimal`, or the value is a string), you should substitute the sentinel value **-1**. This prevents later steps from mis‑interpreting missing data as a valid measurement.

## When to Use This Skill
- When a task asks for the most recent numeric lab value (e.g., magnesium, potassium, HbA1c) within a time window.
- When the GET `/Observation` response has `total > 0` but the Observation resource lacks a numeric field or the field is not a number.
- When the task’s logic branches on the numeric result (e.g., “if low then order replacement”).

## Common Failure Patterns
- `total = 1` but `valueQuantity` is absent, resulting in `undefined`.
- `valueQuantity.value` is a string like `"2.1 mg/dL"` instead of a number.
- Observation uses `valueString` for a lab result, which the agent treats as non‑numeric.
- Empty bundle (`total = 0`) – already covered by the original rule.

## Recommended Patterns
**Pattern 1: Primary numeric extraction**
1. Inspect the first entry in the Bundle (`bundle.entry[0].resource`).
2. If `valueQuantity` exists and `valueQuantity.value` is a number, use that value.
3. Else if `valueDecimal` exists and is a number, use that value.
4. Else if `valueString` exists, attempt to parse a leading numeric token; if parsing succeeds, use the number.
5. If none of the above yield a valid number, set the result to **-1**.

**Pattern 2: Empty bundle fallback**
1. If `bundle.total == 0`, directly set the result to **-1**.

**Pattern 3: Output formatting**
- Return the numeric result inside a JSON array: `FINISH([value])` where `value` is either the extracted number or `-1`.

## Example Application
**Task:** "Check patient S0581164's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded, don't order anything."

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S0581164&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Receive a Bundle with `total = 1`.
3. Examine the Observation:
   - `valueQuantity` is missing.
   - `valueString` = `"Not reported"` (non‑numeric).
4. No parsable numeric value → set `magnesium = -1`.
5. `FINISH([-1])` (the downstream logic will interpret -1 as “no recent value”).

**CORRECT output:** `FINISH([-1])`
**WRONG output:** `FINISH(["Not reported"])` or `FINISH([])`

## Success Indicators
- The agent returns a single numeric element (or -1) inside the FINISH array.
- No string or empty array is returned for numeric‑required tasks.
- Subsequent decision branches correctly treat -1 as “no recent measurement”.

## Failure Indicators
- FINISH returns an empty array or a string when a numeric value is required.
- The agent proceeds to order medication based on a non‑numeric placeholder.
- The numeric placeholder is omitted, causing downstream errors.
