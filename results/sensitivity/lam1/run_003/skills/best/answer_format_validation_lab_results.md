---
description: "Enforce structured FINISH payloads for lab\u2011result queries (value\
  \ list, no units or free text)."
name: answer_format_validation_lab_results
provenance:
  action: ADD
  epoch: 3
  fixes: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task5_7
  - task9_14
  - task5_16
  - task9_8
  - task10_20
  - task9_6
  - task10_24
  - task9_3
  - task10_13
  - task10_10
  update_cycle: 1
tags:
- formatting
- lab_results
- validation
version: 1
---

# Answer Format Validation for Lab Result Tasks

## Pattern Description
You must guarantee that any task asking for a laboratory or vital‑sign result returns a **structured JSON array** via `FINISH` and never free‑text sentences.  The array should contain only the raw numeric value (as a number, not a quoted string) and, when the instruction requests a timestamp, the ISO‑8601 datetime string as the second element.  Strip any units, percent signs, or explanatory text before placing the value in the array.

## When to Use This Skill
- When the task description says *"most recent potassium level"*, *"last HbA1C value and when it was recorded"*, *"magnesium level"*, or any similar phrasing that expects a numeric result.
- When the expected answer format is explicitly a list, e.g. `FINISH([value])` or `FINISH([value, "timestamp"])`.
- When the agent has already retrieved the Observation resource but is about to call `FINISH`.

## Common Failure Patterns
- `FINISH(["Potassium level is 3.9 mmol/L, which is above the threshold."])` – free‑text string inside the array.
- `FINISH([4.7])` – missing required timestamp for tasks that ask for a date.
- `FINISH(["5.7%", "2023-07-07T11:27:00+00:00"])` – value kept as a string and includes a percent sign.
- `FINISH(["6.5","2022-03-08T08:14:00+00:00"])` – numeric value is quoted as a string.

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Identify the Observation entry that matches the requested code (e.g., `code=K` for potassium, `code=A1C` for HbA1c, `code=MG` for magnesium).
2. From the chosen entry, read `valueQuantity.value` **or** `valueQuantity.value` inside `component` if needed.  If the value is stored as a string with units, use a regular expression to capture the leading number.
3. Convert the captured string to a Python `float` (or integer when appropriate).  **Do not** keep the unit or the percent sign.
4. If the task also asks for the collection date, read `effectiveDateTime` (or `issued` when `effectiveDateTime` is absent) and keep it exactly as the ISO‑8601 string.
5. Build the FINISH payload:
   - For a single‑value answer: `FINISH([value])`
   - For value + timestamp: `FINISH([value, "timestamp"])`

**CORRECT**
```json
FINISH([3.9, "2023-11-12T08:45:00+00:00"])   // numeric, no units, timestamp string
```
**WRONG**
```json
FINISH(["Potassium level is 3.9 mmol/L"])   // free text, units present
FINISH(["5.7%", "2023-07-07T11:27:00+00:00"])   // value quoted and contains %
FINISH([4.7])   // missing required timestamp when asked for date
```

**Pattern 2: Fallback when extraction fails**
- If no Observation entry is found, call `FINISH([-1])` for single‑value tasks or `FINISH([-1, ""])` for value‑plus‑date tasks, matching the expected array length.
- Log a brief comment (internal, not part of FINISH) indicating "no recent result found".

**Pattern 3: Verification before FINISH**
- Immediately before issuing `FINISH`, assert:
  - The payload is a list.
  - The first element is a number (`int` or `float`).
  - If a second element is required, it is a non‑empty string matching the ISO‑8601 pattern `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}`.
- If any assertion fails, raise an internal error and fall back to the pattern‑2 fallback.

## Example Application
**Task:** "What’s the last HbA1C value in the chart for patient S0658561 and when was it recorded?"

**Step‑by‑step:**
1. `GET /Patient?identifier=S0658561`
2. `GET /Observation?code=A1C&patient=S0658561`
3. From the returned Bundle, pick the entry with the highest `effectiveDateTime`.
4. Extract `valueQuantity.value` → `5.4` (strip any trailing `%`).
5. Extract `effectiveDateTime` → `"2023-11-02T06:53:00+00:00"`.
6. `FINISH([5.4, "2023-11-02T06:53:00+00:00"])`

## Success Indicators
- The FINISH payload is a JSON array of the exact length required by the task.
- The first element is a numeric type, not a quoted string.
- No unit symbols or percent signs appear in the output.
- When a timestamp is required, it is present and correctly formatted.

## Failure Indicators
- FINISH contains a free‑text sentence or explanatory wording.
- Numeric values are quoted as strings or include units/percent signs.
- The array length does not match the task specification (e.g., missing timestamp).
- The timestamp does not conform to ISO‑8601.
