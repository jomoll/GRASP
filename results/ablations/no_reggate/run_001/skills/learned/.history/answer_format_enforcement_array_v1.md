---
description: "Ensures FINISH output matches the expected JSON array shape and element\
  \ types for value\u2011timestamp tasks."
name: answer_format_enforcement_array
provenance:
  action: ADD
  epoch: 1
  fixes: 13
  probe_score: 1
  regressions: 4
  triggering_sample_ids:
  - task9_28
  - task10_20
  - task5_17
  - task9_6
  - task1_16
  - task5_7
  - task9_27
  - task9_14
  - task9_20
  - task5_16
  update_cycle: 0
tags: []
version: 1
---

# Answer Format Enforcement for Structured Array Responses

## Pattern Description
You must guarantee that every `FINISH` call returns a JSON array whose structure and element types exactly match what the instruction expects. Many clinical queries ask for a numeric result (e.g., a lab value) optionally paired with an ISO‑8601 timestamp. The agent should never return an empty list, a string‑wrapped value, or a free‑text sentence. Instead, construct the array explicitly:
- A single numeric value → `[value]`
- A numeric value with a timestamp → `[value, "2023-11-07T12:34:00+00:00"]`
- No recent measurement → `[-1]` (or `[-1, null]` if a timestamp slot exists)
- A textual error message is never a valid answer; use the sentinel values above.

## When to Use This Skill
- When the instruction asks *"What’s the last X value and when was it recorded?"*
- When the instruction asks *"Check Y level; if low, order …"* and expects a numeric result or `-1` when no action is taken.
- When the agent is about to call `FINISH` and the provisional answer is a string, empty list, or contains non‑numeric types.

## Common Failure Patterns
- `FINISH([])` – empty array returned where a value is required.
- `FINISH(["5.7"])` – numeric value encoded as a string.
- `FINISH(["Potassium is 3.5 mmol/L, within normal range."])` – free‑text sentence instead of a numeric array.
- Missing timestamp element when the task explicitly requests a date.
- Returning `null` or `""` for missing data instead of the sentinel `-1`.

## Recommended Patterns
**Pattern 1: Determine expected shape**
1. Scan the instruction for keywords:
   - "value and when was it recorded" → expect `[number, string]`
   - "most recent" *or* "last" *and* no date request → expect `[number]`
   - "if no measurement" → plan to use `[-1]` (or `[-1, null]`).
2. Set variables `expected_len` and `expected_type` accordingly.

**Pattern 2: Build the answer**
- Extract the numeric value from the FHIR resource (`valueQuantity.value` or `valueString` parsed to float).
- Extract the timestamp (`effectiveDateTime` or `issued`).
- If the value is missing, assign `-1`.
- If a timestamp is required but missing, assign `null`.
- Assemble the array respecting the expected order and types.

**Pattern 3: Validate before FINISH**
```python
# pseudo‑code
if not isinstance(answer, list):
    raise_error()
if len(answer) != expected_len:
    # pad or truncate with sentinel values
    answer = adjust_to_length(answer, expected_len)
for i, elem in enumerate(answer):
    if expected_type[i] == 'number' and isinstance(elem, str):
        answer[i] = float(elem)  # convert
    if expected_type[i] == 'string' and not isinstance(elem, str):
        answer[i] = str(elem) if elem is not None else None
```
- Only after this validation may you emit `FINISH(answer)`.

## Example Application
**Task:** "What’s the last HbA1C value in the chart for patient S6545016 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. Detect that the task asks for *value and when it was recorded* → expect `[number, string]`.
2. GET the Observation bundle, extract the most recent `valueQuantity.value` = `5.2` and `effectiveDateTime` = `2022-08-09T15:33:00+00:00`.
3. Because the date is > 1 year old, POST a ServiceRequest (ordering step).
4. Build `answer = [5.2, "2022-08-09T15:33:00+00:00"]`.
5. Validate: length = 2, first element is a number, second is a string → OK.
6. `FINISH([5.2, "2022-08-09T15:33:00+00:00"])`.

**Correct output:** `FINISH([5.2, "2022-08-09T15:33:00+00:00"])`
**Wrong output:** `FINISH(["5.2", "2022-08-09T15:33:00+00:00"])` or `FINISH([])`.

## Success Indicators
- Every `FINISH` call returns a non‑empty list when a value is required.
- Numeric elements are of type `number`, timestamps are ISO‑8601 strings.
- Sentinel `-1` (or `[-1, null]`) appears only when the instruction explicitly permits “no recent measurement”.

## Failure Indicators
- `FINISH` emits an empty list or a list containing only strings.
- The array length does not match the number of items the instruction asked for.
- The agent returns free‑text sentences inside the array instead of raw values.
- Missing timestamp when the task demanded it.
