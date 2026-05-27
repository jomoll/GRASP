---
description: "Extend numeric answer enforcement to lab\u2011check tasks with conditional\
  \ ordering"
name: answer_numeric_format
provenance:
  action: MODIFY
  epoch: 0
  fixes: 16
  parent_version: 1
  probe_score: 9
  regressions: 1
  triggering_sample_ids:
  - task8_9
  - task9_6
  - task9_28
  - task8_15
  - task8_26
  - task9_20
  - task9_27
  - task10_10
  - task9_22
  - task8_14
  update_cycle: 1
tags: []
version: 2
---

# answer_numeric_format

## Pattern Description
You must always return raw numeric values (or the sentinel `-1`/`[]` when no value is applicable) from a lab Observation instead of any human‑readable sentence. This applies not only to pure‑numeric queries (age, magnesium level, HbA1c) but also to tasks that *check* a lab value and then conditionally create orders (e.g., "Check potassium; if low, order replacement"). The decision logic should be based on the extracted number, and the final `FINISH` payload must be a JSON array containing **only** numbers, dates, or an empty array – never a descriptive string.

## When to Use This Skill
- When the instruction mentions "most recent <lab>" or "last <lab>" and includes a conditional clause such as "If low, then order...".
- When the expected answer is a numeric lab value, a date, a sentinel (`-1`), or an empty array indicating no action.
- When the task does **not** ask for a free‑text summary.

## Common Failure Patterns
- `FINISH(["Potassium 3.5 mmol/L is at goal; no replacement ordered."])` – string inside array.
- `FINISH(["No potassium replacement needed; latest level 4.3 mmol/L is above the 3.5 mmol/L goal."])` – descriptive sentence.
- Returning a mixed array like `["5.4", "2023-11-02T06:53:00+00:00"]` where the numeric value is a string instead of a number.
- Omitting the sentinel `-1` or empty array when the lab is missing.

## Recommended Patterns
**Pattern 1: Extract numeric value correctly**
1. Query the Observation with the appropriate `code` and `patient` parameters.
2. From the first entry in the Bundle, read `valueQuantity.value` **as a number** (do not concatenate the unit).
3. If the Bundle has `total = 0`, set `value = -1` (or `[]` when the task expects no action).

**Pattern 2: Apply conditional logic**
1. Compare the extracted `value` to the threshold defined in the instruction (e.g., `< 3.5` for potassium).
2. If the condition is met, perform the required POST (order, schedule) **before** calling `FINISH`.
3. If the condition is not met, skip the POST.

**Pattern 3: Format FINISH output**
- **When only a number is required**: `FINISH([value])` where `value` is a JSON number, e.g., `FINISH([3.5])`.
- **When a number and a date are required**: `FINISH([value, "YYYY-MM-DDThh:mm:ss+00:00"])` with the date as a string and the value as a number.
- **When no action is needed**: `FINISH([])`.
- **Never** place a full sentence or concatenate units inside the array.

## Example Application
**Task:** "Check patient S3241217's most recent potassium level. If low, then order replacement potassium ..."

**Step‑by‑step:**
1. `GET /Observation?code=K&patient=S3241217`
2. Extract `valueQuantity.value` → `4.3` (number).
3. Compare to threshold `3.5` → `4.3 >= 3.5` → condition false.
4. Skip any `POST` for replacement.
5. `FINISH([])` because no order is required.

**Correct output:** `FINISH([])`
**Incorrect output:** `FINISH(["No potassium replacement needed; latest level 4.3 mmol/L is above the 3.5 mmol/L goal."])`

## Success Indicators
- `FINISH` payload contains only numbers, dates, or is an empty array.
- Any required `POST` actions are executed **before** the `FINISH` call.
- No descriptive sentences appear inside the `FINISH` array.

## Failure Indicators
- `FINISH` contains a string sentence.
- Numeric values are quoted as strings.
- The sentinel `-1` or empty array is missing when the Observation bundle is empty.
- Conditional POST is performed when the numeric check fails, or omitted when it passes.
