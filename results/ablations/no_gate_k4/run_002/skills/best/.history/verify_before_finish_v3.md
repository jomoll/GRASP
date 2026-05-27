---
description: Enforce FINISH to receive a scalar string, not a list or array
name: verify_before_finish
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task1_27
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_26
  - task4_6
  - task4_27
  update_cycle: 0
tags:
- output_verification
- formatting
version: 3
---

# Ensure Scalar FINISH Output

## Pattern Description
You must guarantee that every call to `FINISH` supplies a single scalar string (or number) rather than a JSON array or list. This prevents downstream consumers from receiving unexpected list structures and aligns with the expected answer format for most clinical queries (e.g., lab values, ages, MRNs). The rule applies universally across tasks that culminate in a `FINISH` call.

## When to Use This Skill
- After extracting a value from a FHIR resource and before calling `FINISH`.
- When the task description expects a single answer (e.g., "What’s the patient’s age?", "What’s the last HbA1c value?", "What’s the MRN?").
- Whenever the agent is about to execute `FINISH([...])` or `FINISH([-1])` and the argument is an array.

## Common Failure Patterns
- `FINISH(["5.7 % on 2023-07-07"])` – list containing a single string.
- `FINISH(["1.8 mg/dL"])` – list instead of plain value.
- `FINISH(["50"])` – age returned as a list.
- `FINISH([-1])` – placeholder returned as an array.
- Any `FINISH` call where the argument type is `list`/`array` rather than a scalar.

## Recommended Patterns
**Pattern 1: Detect and unwrap list output**
1. Before invoking `FINISH`, inspect the variable you intend to return.
2. If the variable is of type `list`/`array`:
   - If the list is empty, decide on an appropriate placeholder (e.g., `"-1"` or a descriptive message) and assign that scalar to a new variable.
   - If the list contains exactly one element, extract that element: `result = my_list[0]`.
   - If the list contains multiple elements, join them with a semicolon and space: `result = "; ".join(str(x) for x in my_list)`.
3. Call `FINISH(result)` where `result` is now guaranteed to be a scalar string or number.

**Pattern 2: Defensive fallback**
- If you cannot determine a sensible scalar (e.g., unexpected data shape), abort the task with a clear error message rather than returning a list.

**Pattern 3: Consistent formatting**
- Do not include surrounding brackets or quotes that imply a JSON array.
- Ensure the final string contains only the answer text, e.g., `"5.7 % on 2023-07-07"`.

## Example Application
**Task:** "What’s the last HbA1c value for patient S6545016 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6545016`.
2. Parse the bundle, extract `valueQuantity.value` and `effectiveDateTime` → `value = "5.7 %"`, `date = "2023-07-07"`.
3. Combine into a single string: `answer = f"{value} on {date}"` (scalar).
4. **Before FINISH:** verify `type(answer) is str`.
5. `FINISH(answer)` → `FINISH("5.7 % on 2023-07-07")`.

**Correct output:** `FINISH("5.7 % on 2023-07-07")`
**Wrong output:** `FINISH(["5.7 % on 2023-07-07"])`

## Success Indicators
- The agent calls `FINISH` with a plain string/number, no surrounding brackets.
- Log shows `FINISH("...")` rather than `FINISH(["..."])`.

## Failure Indicators
- `FINISH` is invoked with an array literal.
- The final answer appears as `[...]` in the response payload.
- Consumers report type‑mismatch errors when parsing the answer.

---

*This modification expands the original `verify_before_finish` skill to actively detect list structures, unwrap or reformat them, and enforce a scalar output for every `FINISH` call.*
