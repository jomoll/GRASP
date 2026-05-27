---
description: Force FINISH to always receive a JSON list, wrapping scalar strings and
  removing extra text
name: verify_before_finish
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 3
  triggering_sample_ids:
  - task4_7
  - task2_30
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  update_cycle: 1
tags: []
version: 4
---

# verify_before_finish

## Pattern Description
You must guarantee that every FINISH call returns a JSON array (list) containing the final answer(s). The agent often produces a plain string or adds explanatory text, which violates the required output contract and leads to `answer_format_wrong_type` failures. This skill enforces a strict list format and strips any surrounding narrative before finishing.

## When to Use This Skill
- After completing any task that requires a FINISH response (e.g., patient lookup, lab value query, order placement).
- Whenever the agent is about to call `FINISH(...)` and the prepared payload is not a JSON array.
- If the answer includes extra sentences or formatting beyond the raw value(s).

## Common Failure Patterns
- `FINISH("S1234567")` – scalar string instead of list.
- `FINISH([6.1, "2023-10-13"])` – mixed scalar types; should be a list of strings or numbers consistently.
- `FINISH("No replacement needed; potassium is 3.8 mmol/L.")` – explanatory text wrapped in a string.
- Missing outer brackets: `FINISH("Blood pressure recorded for patient S123")`.

## Recommended Patterns
**Pattern 1: Core enforcement**
1. Inspect the value you intend to pass to FINISH.
2. If the value is already a JSON array, verify each element is a primitive (string, number, or boolean). Keep it as‑is.
3. If the value is a scalar (string, number, boolean) **or** a complex object, wrap it in a single‑element array: `FINISH([value])`.
4. If the scalar string contains explanatory sentences, extract only the required answer portion (e.g., the MRN, the numeric lab value, or the confirmation phrase) before wrapping.

**Pattern 2: Normalization of mixed types**
- When you have multiple pieces of data (e.g., value and date), convert both to strings and place them in an array: `FINISH(["6.1", "2023-10-13"])`.
- Avoid mixing raw numbers with strings inside the same array unless the downstream consumer explicitly expects that format.

**Pattern 3: Final output check**
- Immediately before emitting `FINISH`, perform a sanity check:
  ```python
  if not isinstance(answer, list):
      answer = [answer]
  # ensure no surrounding whitespace or newline characters
  answer = [str(item).strip() for item in answer]
  FINISH(answer)
  ```
- If the answer list contains more than one element, confirm the task description expects multiple values.

## Example Application
**Task:** "What’s the MRN of the patient with name Christopher Cruz and DOB of 1940-08-28?"

**Step‑by‑step:**
1. GET `Patient?family=Cruz&given=Christopher&birthdate=1940-08-28`.
2. Extract the MRN from `entry[0].resource.id` → `"S0658561"`.
3. Verify the extracted value is a string.
4. Wrap it: `answer = ["S0658561"]`.
5. Call `FINISH(answer)`.

**Correct output:** `FINISH(["S0658561"])`
**Wrong output:** `FINISH("S0658561")`

## Success Indicators
- The agent’s final line is always `FINISH([...])` with square brackets.
- No extra explanatory text appears inside the FINISH payload.
- All elements inside the list are primitive types and match the task’s expected answer format.

## Failure Indicators
- FINISH is called with a plain string or object.
- The list contains nested objects or untrimmed whitespace.
- The output includes sentences like "Referral order placed" without being wrapped in a list.
