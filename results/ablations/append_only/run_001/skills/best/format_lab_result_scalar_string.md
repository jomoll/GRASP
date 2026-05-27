---
description: "Force scalar\u2011string FINISH output for lab\u2011value queries (e.g.,\
  \ HbA1c, potassium) and embed any follow\u2011up action in the same string."
name: format_lab_result_scalar_string
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task3_14
  - task4_11
  update_cycle: 0
tags:
- lab_result
- output_format
- scalar_string
version: 1
---

# Format Lab Result as Scalar String

## Pattern Description
You must always return a **single string** inside the FINISH call when answering a question that asks for the most recent laboratory value (e.g., HbA1c, potassium, magnesium). The string should contain the numeric result, its unit (or % for HbA1c), the date it was recorded, and, if the task requires a follow‑up order, a concise statement of that order. This prevents the agent from emitting a list of strings, which the evaluation framework treats as the wrong answer type.

## When to Use This Skill
- When a task asks for the *last* value of a lab Observation and the date it was recorded.
- When the same task also instructs you to place a new ServiceRequest if the result is older than a threshold.
- Applicable to any Observation where the value is stored in `valueQuantity.value` (or `valueString` for non‑numeric results) and the date is in `effectiveDateTime` or `issued`.

## Common Failure Patterns
- `FINISH(["5.8%", "2022-09-09"])` – list of two strings instead of one.
- `FINISH(["5.8% recorded on 2022-09-09"])` – list containing a single string.
- Including extra commentary or unrelated fields inside the list (e.g., `FINISH(["Result is high", "Order placed"])`).
- Omitting the unit or date, or swapping `effectiveDateTime` with `issued`.

## Recommended Patterns
**Pattern 1: Core extraction and scalar formatting**
1. From the Observation bundle, locate the entry with the most recent `effectiveDateTime` (or `issued`).
2. Extract:
   - `valueQuantity.value` (numeric) **or** `valueString` (text).
   - `valueQuantity.unit` if present; for HbA1c the unit is "%".
   - `effectiveDateTime` (ISO‑8601 date).
3. Build a string:
   - For numeric results: `"{value}{unit} on {date}"` (e.g., `"5.8% on 2022-09-09"`).
   - For string results: `"{valueString} on {date}"`.
4. If the task requires ordering a new test, append a short clause separated by a space: `"; new HbA1c test ordered"` or `"; potassium replacement ordered"`.
5. Call FINISH with **exactly one element**:
   ```
   FINISH(["5.8% on 2022-09-09; new HbA1c test ordered."])
   ```

**Pattern 2: Fallback when no Observation found**
- If the search returns `total: 0`, construct a string that states the absence and any required action, e.g., `"No HbA1c result found; new HbA1c test ordered."` and FINISH with a single‑element list.

**Pattern 3: Formatting consistency**
- Do **not** include surrounding brackets or extra commas inside the string.
- Do **not** wrap the string in another list; the outer list is the FINISH argument only.
- Keep the sentence concise; avoid verbose explanations.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6521727 and when was it recorded? If the result is >1 year old, order a new test."

**Step‑by‑step:**
1. GET `Observation?code=A1C&patient=S6521727`.
2. Identify the Observation with the greatest `effectiveDateTime` (e.g., `2022-09-09`).
3. Extract `valueQuantity.value = 5.8` and `unit = "%"`.
4. Compare the date to the current time (`2023-11-13`). It is older than 1 year → need new test.
5. Build the string: `"5.8% on 2022-09-09; new HbA1c test ordered."`
6. FINISH:
   ```
   FINISH(["5.8% on 2022-09-09; new HbA1c test ordered."])
   ```

**Correct output:** `FINISH(["5.8% on 2022-09-09; new HbA1c test ordered."])`
**Wrong output:** `FINISH(["5.8%", "2022-09-09"])`

## Success Indicators
- FINISH is called with a list containing exactly one string.
- The string follows the `{value}{unit} on {date}` pattern and, if required, ends with a concise order clause.
- No extra commas, brackets, or explanatory text appear inside the string.

## Failure Indicators
- FINISH receives a list with more than one element.
- The output string is missing the unit or date.
- The order clause is placed in a separate list element.
- The string contains unrelated commentary (e.g., "The most recent…").
