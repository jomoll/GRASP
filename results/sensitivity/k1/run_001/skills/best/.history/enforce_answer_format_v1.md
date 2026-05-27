---
description: Guarantee FINISH output matches the exact type/structure required by
  the instruction
name: enforce_answer_format
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 1
  regressions: 5
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task9_14
  - task9_27
  - task1_12
  update_cycle: 0
tags: []
version: 1
---

# Enforce Answer Format

## Pattern Description
You must ensure that the final `FINISH` payload conforms exactly to the data type and structure described in the task instruction.  Whether the answer should be a plain scalar (e.g., `48`), a JSON object with named fields (e.g., `{"value":"5.4%","date":"2023-11-02T06:53:00+00:00"}`), or a specific string literal (e.g., `"Patient not found"`), you must output **only** that representation—no surrounding arrays, no free‑text sentences, and no extra keys.

## When to Use This Skill
- When the instruction says *"answer should be a single number"* or *"rounded down to an integer"*.
- When the instruction says *"the answer should be a JSON object with fields X and Y"*.
- When the instruction says *"return the string \"Patient not found\" if the patient does not exist"*.
- When any other task explicitly defines the expected output format (list, object, plain string, etc.).

## Common Failure Patterns
- `FINISH(["48"])` – scalar wrapped in a list.
- `FINISH(["Patient not found"])` – string wrapped in a list.
- `FINISH(["5.4% on 2023-11-02"])` – free‑text sentence instead of a JSON object.
- Missing required keys in a JSON object (e.g., omitting `date`).
- Using the wrong field names (`valueQuantity` vs `value`).

## Recommended Patterns
**Pattern 1: Determine the required output type**
1. Scan the instruction for keywords like *"single number"*, *"plain string"*, *"JSON object"*, *"field"*, *"key"*.
2. Set `expected_type` to one of: `scalar_number`, `plain_string`, `json_object`.
3. If `json_object`, extract the required field names (e.g., `value`, `date`).

**Pattern 2: Build the answer in the exact shape**
- **Scalar number**
  ```
  answer = 48   # integer, no quotes, no list
  FINISH(answer)
  ```
- **Plain string**
  ```
  answer = "Patient not found"   # raw string, no list
  FINISH(answer)
  ```
- **JSON object**
  ```
  answer = {"value": "5.4%", "date": "2023-11-02T06:53:00+00:00"}
  FINISH(answer)
  ```
  *Only the keys that the instruction explicitly requests may appear.*

**Pattern 3: Verification before FINISH**
1. If `expected_type == "scalar_number"`, assert `type(answer) in (int, float)`.
2. If `expected_type == "plain_string"`, assert `isinstance(answer, str)`.
3. If `expected_type == "json_object"`, assert `isinstance(answer, dict)` and that all required keys are present.
4. If any check fails, raise a brief error and re‑format the answer.

## Example Application
**Task:** "What’s the last HbA1C value and when was it recorded? Return a JSON object with fields `value` and `date`."

**Step‑by‑step:**
1. Detect that a JSON object is required with keys `value` and `date`.
2. Query the Observation resource, extract `valueQuantity.value` and `effectiveDateTime`.
3. Build `answer = {"value": f"{value}%", "date": effectiveDateTime}`.
4. Verify both keys exist and are strings.
5. `FINISH(answer)`.

**Correct output:** `{"value":"5.4%","date":"2023-11-02T06:53:00+00:00"}`
**Wrong output:** `["5.4% on 2023-11-02"]` (list and free‑text).

## Success Indicators
- The `FINISH` call contains a value whose JSON type matches the instruction (scalar, string, or object).
- No surrounding array brackets appear when a scalar or string is required.
- All required keys are present and correctly named in a JSON object.

## Failure Indicators
- The output is a list (`[ ... ]`) when a scalar or string was requested.
- The output is a free‑text sentence instead of a structured object.
- Required keys are missing or misspelled in a JSON object.
- Extra unrelated fields are included.

**Tags:** ["formatting","answer_validation","json_output"]
