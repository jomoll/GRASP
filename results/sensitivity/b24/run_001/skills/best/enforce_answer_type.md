---
description: "Require FINISH output to match the data type explicitly requested *only\
  \ when the task\u2019s sole purpose is to return a value*. The skill now checks\
  \ that the task description does not also require additional actions (e.g., ordering\
  \ medication, scheduling a procedure, creating resources). If such actions are present,\
  \ the type\u2011check is skipped so the agent can continue performing the required\
  \ steps."
name: enforce_answer_type
provenance:
  action: ADD
  epoch: 0
  fixes: 15
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - task1_20
  - task9_1
  - task9_22
  - task1_16
  - task9_28
  update_cycle: 2
tags: []
version: 1
---

## Answer Type Enforcement (Conditional)

### When to Apply
1. The task description **explicitly requests** a return value in a specific primitive format (single number, list of numbers, tuple, etc.).
2. The description **does not contain** keywords that imply further clinical actions such as `order`, `create`, `schedule`, `pair`, `add`, `update`, `delete`, `prescribe`, `administer`, `request`, `perform`, or similar verbs.
3. The agent has already completed any required GET/POST/PUT actions and is about to emit `FINISH(...)`.

### Guard Clause (Skip Enforcement)
```python
# Pseudo‑code for the guard
action_keywords = [
    "order", "create", "schedule", "pair", "add", "update", "delete",
    "prescribe", "administer", "request", "perform", "send", "record"
]
if any(word in task_description.lower() for word in action_keywords):
    # Do not enforce answer type – other actions are required
    skip_type_check = True
else:
    skip_type_check = False
```
If `skip_type_check` is `True`, the skill does nothing and the agent proceeds normally.

### Type‑Check Procedure (when not skipped)
1. **Detect Expected Type** – Parse the task description for phrases like:
   - "return the value as a single number in a JSON array"
   - "list of numbers"
   - "tuple (value, timestamp)"
   - Provide explicit example syntax if present.
2. **Extract Primitive Value(s)** from prior GET responses, converting strings to native numbers where needed.
3. **Build FINISH Payload** using the exact JSON syntax required:
   - Single number → `FINISH([<number>])`
   - List of numbers → `FINISH([<num1>, <num2>, ...])`
   - Tuple → `FINISH([<number>, "<ISO8601>"])`
4. **Validate** the JSON payload against the inferred schema before calling `FINISH`. If validation fails, emit a brief error message and abort the FINISH call.

### Example (type‑check applied)
**Task:** "Return the most recent potassium value as a single number in a JSON array."
- After GET, extract `3.9` → `float(3.9)`.
- Expected type = `number_array`.
- Emit `FINISH([3.9])`.

### Example (type‑check skipped)
**Task:** "Check patient S3236936's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."
- The description contains the keyword `order` and `pair`, so `skip_type_check` is `True`.
- The agent proceeds to create the medication order and the follow‑up observation request instead of finishing early.

### Success Indicators
- `FINISH` payload matches the primitive type(s) required **and** the guard clause determined that no extra actions were needed.
- For tasks with additional actions, the skill does not intervene, allowing the agent to perform those actions.

### Failure Indicators
- `FINISH` contains strings where numbers are required, *and* the guard clause incorrectly allowed enforcement.
- The guard clause incorrectly skips enforcement for a task that only needs a value, leading to malformed output.

---
*This revised skill retains the original type‑checking logic but adds a precise guard clause to prevent premature `FINISH` calls on tasks that also require ordering or scheduling actions, thereby fixing the regression while still preventing answer‑format‑type errors.*
