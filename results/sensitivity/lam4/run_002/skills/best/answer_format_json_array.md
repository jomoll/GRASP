---
description: "Force FINISH output to be a plain JSON array of raw values, never a\
  \ free\u2011form sentence."
name: answer_format_json_array
provenance:
  action: ADD
  epoch: 0
  fixes: 18
  probe_score: 18
  regressions: 1
  triggering_sample_ids:
  - task3_14
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task5_13
  - task3_3
  - task4_28
  - task10_8
  update_cycle: 0
tags: []
version: 1
---

# Answer Format JSON Array Enforcement

## Pattern Description
You must always return the final answer with `FINISH([...])` where the brackets contain **only** the raw data elements required by the task (strings, numbers, or simple objects). No explanatory sentences, no extra wording, and no surrounding text are allowed. This pattern guarantees that downstream consumers can parse the result reliably.

## When to Use This Skill
- The instruction explicitly says *"the answer should be a JSON array"* or *"return a list of values"*.
- The task asks for a single value (e.g., MRN, lab result) **or** a small list (e.g., `[value, date]`).
- The expected output type is a primitive (string/number) or a simple JSON object, not a narrative paragraph.

## Common Failure Patterns
- `FINISH(["The most recent potassium is 3.8 mmol/L."])` – sentence inside the array.
- `FINISH(["No replacement needed; latest potassium is 3.8 mmol/L (2023-11-12)."])` – explanatory text mixed with data.
- Returning a JSON object instead of an array: `FINISH({"value":3.8})`.
- Omitting the array brackets entirely: `FINISH("3.8")`.

## Recommended Patterns
**Pattern 1: Extract and return a single primitive**
1. Identify the exact field that holds the required value (e.g., `valueQuantity.value`).
2. Convert it to the appropriate type (number or string) **without** appending units or commentary.
3. Call `FINISH([<value>])`.

**CORRECT**: `FINISH([3.8])`
**WRONG**: `FINISH(["3.8 mmol/L"])`

**Pattern 2: Return a small ordered list**
1. Extract each required element in the order specified by the instruction.
2. Ensure each element is a primitive (or a flat object) and does not contain extra text.
3. Call `FINISH([<elem1>, <elem2>, ...])`.

**CORRECT**: `FINISH(["2023-11-12", 3.8])`
**WRONG**: `FINISH(["Result recorded on 2023-11-12: 3.8 mmol/L"])`

**Pattern 3: Fallback when no data is available**
- If the task defines a sentinel (e.g., `-1` for missing numeric value), return that sentinel **alone** in the array.
- Example: `FINISH([-1])`.

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://.../Observation?code=K&patient=S6309742`.
2. From the returned Bundle, locate the newest entry and read `valueQuantity.value` (e.g., `3.8`).
3. Compare to the low‑threshold (e.g., `<3.5`).
4. If not low, **do not** place an order; simply return the value.
5. **FINISH** the answer as a plain array: `FINISH([3.8])`.

## Success Indicators
- The final agent message is exactly `FINISH([...])` with no surrounding prose.
- Each element inside the brackets is a raw primitive or a flat JSON object.
- The output can be parsed by a JSON parser without errors.

## Failure Indicators
- The FINISH payload contains a full sentence or explanatory text.
- The payload is not an array (object or scalar instead).
- Units, labels, or extra punctuation appear inside the array elements.
