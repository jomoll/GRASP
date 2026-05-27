---
description: "Return extracted lab values as plain numeric results with correct unit,\
  \ no free\u2011text."
name: format_quantity_with_unit
provenance:
  action: MODIFY
  epoch: 4
  fixes: 12
  parent_version: 1
  probe_score: 10
  regressions: 1
  triggering_sample_ids:
  - task9_5
  - task10_24
  - task2_28
  - task10_15
  - task8_26
  - task9_6
  - task9_14
  - task9_1
  - task4_26
  - task9_27
  update_cycle: 1
tags: []
version: 2
---

# format_quantity_with_unit

## Pattern Description
You must extract a quantitative lab result from a FHIR Observation and return **only the raw numeric value** (optionally accompanied by its unit) in the FINISH payload. The skill is reusable for any lab observation where the value is stored in `valueQuantity.value` and the unit in `valueQuantity.unit`. Do **not** embed the value in a sentence, include dates, or add explanatory text. This ensures downstream logic receives a predictable data type for comparisons and ordering decisions.

## When to Use This Skill
- When a task asks for "the last *X* value" and expects a numeric answer (e.g., potassium, HbA1c, magnesium).
- After a GET request to `/Observation` that returns a Bundle with at least one entry containing `valueQuantity`.
- When the task may also require the observation date, return a two‑element array `[numericValue, isoDate]`.

## Common Failure Patterns
- Returning a free‑text sentence such as `"Latest potassium is 4.7 mmol/L on 2023‑11‑12"`.
- Returning the value as a string with unit (`"4.7 mmol/L"`) instead of a number.
- Omitting the numeric part and returning only the unit or an empty array.
- Including additional commentary or formatting (e.g., brackets inside a string).

## Recommended Patterns
**Pattern 1: Core extraction**
1. Locate the first Observation entry that matches the requested code.
2. Read `valueQuantity.value` → store as `numericValue` (float or int).
3. Read `valueQuantity.unit` → store as `unit` (string).
4. If the task only needs the number, `FINISH([numericValue])`.
5. If the task also needs the timestamp, read `effectiveDateTime` and `FINISH([numericValue, effectiveDateTime])`.

**CORRECT**: `FINISH([4.7])`  (or `FINISH([4.7, "2023-11-12T09:30:00+00:00"])`)
**WRONG**: `FINISH(["Latest potassium is 4.7 mmol/L on 2023-11-12"])`

**Pattern 2: Unit conversion fallback**
- If the required unit differs from the stored unit, convert using a simple factor table (e.g., `mmol/L → mg/dL` for potassium: multiply by 38.66).
- Return the converted numeric value, still without any text.

**Pattern 3: Missing value handling**
- If the Bundle has `total = 0` or the entry lacks `valueQuantity`, return `FINISH([-1])` (or `FINISH([-1, null])` when a date is also expected).

## Example Application
**Task:** "Check patient S1311412's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. `GET /Observation?code=K&patient=Patient/S1311412`
2. From the first entry, extract `valueQuantity.value = 3.5` and `valueQuantity.unit = "mmol/L"`.
3. No conversion needed; output `FINISH([3.5])`.
4. Agent logic compares `3.5` to the low‑threshold (e.g., `<3.5`). Since it meets the goal, no order is placed.

**CORRECT output:** `FINISH([3.5])`
**WRONG output:** `FINISH(["Latest potassium level is 3.5 mmol/L, within goal."])`

## Success Indicators
- FINISH payload contains a JSON array whose first element is a number (not a string).
- When a date is required, the second element is an ISO‑8601 timestamp string.
- No extra words or punctuation appear inside the array elements.

## Failure Indicators
- FINISH payload contains a single string or a sentence.
- The numeric value is embedded in text, causing downstream numeric comparisons to fail.
- The unit is concatenated to the number (e.g., `"4.7 mmol/L"`).
- The agent proceeds to order medication based on a mis‑formatted value.
