---
description: Ensures FINISH output is a plain string, not a JSON array, for scalar
  answer tasks
name: plain_string_answer_validation
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task4_11
  update_cycle: 0
tags:
- answer_format
- validation
- scalar_output
version: 1
---

# Plain String Answer Validation

## Pattern Description
You must guarantee that every `FINISH` call returns a **plain JSON string** when the task asks for a single value (e.g., an MRN, an age, a status).  Many instructions explicitly say *"If the patient does not exist, the answer should be \"Patient not found\""* or *"answer should be rounded down to an integer"*.  Returning a JSON array such as `FINISH(["Patient not found"])` is a format error that downstream consumers cannot parse.

## When to Use This Skill
- The task description requests a single scalar answer (MRN, age, lab value, status, etc.).
- The instruction includes phrasing like *"the answer should be \"...\""* or *"rounded down to an integer"*.
- After extracting the value, you are about to call `FINISH`.

## Common Failure Patterns
- `FINISH(["S3228213"])` – array of one string.
- `FINISH([86])` – array of a number.
- `FINISH([])` – empty array when a default string is required.
- `FINISH(["Patient not found"])` – correct text but wrong container type.

## Recommended Patterns
**Pattern 1: Verify output container before FINISH**
1. After you have the answer in a variable `answer`, check its type.
2. If `answer` is a list/array, extract the first element: `answer = answer[0]`.
3. Ensure `answer` is a string; if it is a number, convert to string: `answer = str(answer)`.
4. Call `FINISH(answer)` **without** surrounding brackets.

**CORRECT**: `FINISH("Patient not found")`
**WRONG**: `FINISH(["Patient not found"])`

**Pattern 2: Provide default when array is empty**
1. If the extracted list is empty, decide the appropriate default (often "Patient not found" or a sentinel like "0").
2. Set `answer = "Patient not found"` (or the task‑specific default).
3. Call `FINISH(answer)`.

**Pattern 3: Guard against accidental JSON encoding**
- Do not JSON‑encode the string yourself; the runtime will handle proper quoting.
- Example of a bad practice: `FINISH(json.dumps(answer))` – leads to double‑quoted strings inside an array.

## Example Application
**Task:** "What’s the MRN of the patient with name Julie Rodriguez and DOB of 1962-01-20? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://.../Patient?name=Julie%20Rodriguez&birthdate=1962-01-20`
2. Receive a Bundle with `total: 0` → no patient found.
3. Set `answer = "Patient not found"` (not `['Patient not found']`).
4. `FINISH(answer)` → `FINISH("Patient not found")`.

**CORRECT output:** `FINISH("Patient not found")`
**WRONG output:** `FINISH(["Patient not found"])`

## Success Indicators
- The final `FINISH` call contains a JSON string value, e.g., `FINISH("S3228213")` or `FINISH("Patient not found")`.
- No surrounding `[` or `]` characters appear in the output payload.

## Failure Indicators
- The agent still emits `FINISH(["..."])` or any array‑type payload.
- The output is an empty array when a default string is required.
- Numbers are returned without being converted to strings, causing type mismatches.
