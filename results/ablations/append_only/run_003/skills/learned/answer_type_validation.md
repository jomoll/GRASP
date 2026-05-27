---
description: "Enforce that FINISH output matches the expected data\u2011type schema\
  \ for each task."
name: answer_type_validation
provenance:
  action: ADD
  epoch: 1
  fixes: 16
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task9_27
  - task9_14
  - task9_20
  - task10_18
  - task5_16
  update_cycle: 0
tags:
- validation
- output-format
version: 1
---

# Answer Type Validation

## Pattern Description
You must verify that the value you pass to `FINISH` conforms to the data‑type contract implied by the task description.  Many tasks expect a JSON array containing numbers, ISO‑8601 timestamps, or a sentinel value (e.g., `-1`).  Returning free‑text strings or mixing types causes the agent to be marked incorrect even when the underlying logic is sound.  This skill adds a lightweight type‑check step before finalising the answer and normalises the payload when possible.

## When to Use This Skill
- After extracting a lab or vital value and before calling `FINISH`.
- When the task explicitly states the answer format (e.g., "return a single number", "return `[value, date]`", "return `-1` if no recent measurement").
- Whenever the agent is about to `FINISH` with a JSON array that may contain strings instead of numbers or dates.

## Common Failure Patterns
- `FINISH(["5.2 %", "2022-08-09"])` – value and date are strings, not a numeric value and ISO datetime.
- `FINISH(["Blood pressure recorded successfully."])` – single descriptive string where a numeric array is required.
- `FINISH(["-1"])` – sentinel `-1` wrapped in a string.
- Missing array entirely, e.g., `FINISH([])` when a numeric result is expected.
- Date strings not in ISO‑8601 format (e.g., `"08/09/2022"`).

## Recommended Patterns
**Pattern 1: type inspection and conversion**
1. Identify the expected schema from the task description.
2. For each element in the candidate result array:
   - If the schema expects a number and the element is a string that can be parsed, convert with `float(element)`.
   - If the schema expects an ISO datetime and the element is a string, attempt to parse with `datetime.fromisoformat`; if it fails, re‑format from known patterns.
   - If the schema expects the sentinel `-1`, ensure the result is the integer `-1` (not a string).
3. Assemble a new array `validated_result` with the corrected types.
4. If any element cannot be coerced, fall back to the task‑specified fallback (e.g., `[-1]` or `[]`).

**Pattern 2: schema‑driven guard**
- Define a small schema map in the skill, e.g.:
  ```json
  {
    "HbA1c": ["number", "datetime"],
    "magnesium": ["number"],
    "potassium": ["number"],
    "age": ["integer"]
  }
  ```
- Look up the task keyword (HbA1c, magnesium, etc.) and apply the corresponding type list.

**Pattern 3: final output formatting**
- Call `FINISH(validated_result)` **only** after the conversion step.
- Do **not** embed explanatory text inside the array; keep the array pure data.

## Example Application
**Task:** "What’s the last HbA1C value and when was it recorded? Return `[value, date]` where value is a number and date is ISO‑8601."

**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S12345`.
2. Extract `valueQuantity.value` → `"5.2 %"` (string) and `effectiveDateTime` → `"2022-08-09"` (string).
3. Convert value: `float("5.2")` → `5.2`.
4. Verify date is ISO‑8601; it already is.
5. Build `validated = [5.2, "2022-08-09T00:00:00+00:00"]`.
6. `FINISH(validated)`.

**CORRECT output:** `FINISH([5.2, "2022-08-09T00:00:00+00:00"])`
**WRONG output:** `FINISH(["5.2 %", "2022-08-09"])`

## Success Indicators
- `FINISH` is called with an array whose elements match the expected primitive types.
- No free‑text strings appear inside the result array.
- Sentinel values appear as raw integers, not quoted strings.

## Failure Indicators
- `FINISH` payload contains mixed types (e.g., numbers as strings).
- Dates are not ISO‑8601 or are missing timezone information.
- The agent returns a single descriptive string instead of the required structured array.
