---
description: Force FINISH to return a single scalar string, not an array
name: verify_before_finish
provenance:
  action: MODIFY
  epoch: 0
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task8_29
  update_cycle: 1
tags: []
version: 2
---

# verify_before_finish

## Pattern Description
You must ensure that every call to `FINISH` returns **exactly one plain string**.  The agent often builds answers as JSON arrays (e.g. `FINISH(["value"])`), which violates the expected output contract and leads to `answer_format_wrong_type` failures.  This skill overrides any intermediate formatting and forces the final response into a single string, concatenating multiple pieces when necessary.

## When to Use This Skill
- When the task requires a simple answer (e.g., an MRN, age, confirmation message) and the agent is about to call `FINISH`.
- When you see the agent preparing an array literal for `FINISH` (e.g., `FINISH(["text1", "text2"])`).
- After extracting values from a FHIR response and before emitting the final answer.

## Common Failure Patterns
- `FINISH(["Referral order placed"])` – array instead of string.
- `FINISH(["5.0 % on 2023-11-09"])` – array wrapping a formatted string.
- `FINISH(["5.9 %", "2023-11-12"])` – multiple array elements.
- `FINISH([])` – empty array returned.

## Recommended Patterns
**Pattern 1: enforce scalar output**
1. Gather all answer components you need (value, date, status, etc.).
2. Combine them into a single human‑readable string using string interpolation or concatenation.
3. Call `FINISH` with that string **without any surrounding brackets**.

   ```
   # Correct
   FINISH("Referral order placed")

   # Wrong
   FINISH(["Referral order placed"])   # array
   ```

**Pattern 2: fallback when multiple pieces exist**
- If you have more than one piece, join them with a separator (e.g., ", ", " on ") to produce one string.
   ```
   value = "5.9 %"
   date  = "2023-11-12"
   FINISH(f"{value} on {date}")
   ```

**Pattern 3: guard against empty results**
- If no data is found, still return a single string explaining the situation.
   ```
   FINISH("No magnesium level recorded in the last 24 hours; no IV magnesium ordered.")
   ```

## Example Application
**Task:** "What’s the age of the patient with MRN of S2450227?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2450227`
2. Extract `birthDate` from the returned `Patient` resource.
3. Compute age as an integer.
4. Build a single string: `age_str = f"{age}"`.
5. `FINISH(age_str)`

**Correct output:** `FINISH("75")`
**Wrong output:** `FINISH(["75"])`

## Success Indicators
- The final agent output is `FINISH("some text")` with no surrounding brackets.
- All answer components appear in one contiguous string.
- No `answer_format_wrong_type` errors are logged.

## Failure Indicators
- The agent still emits `FINISH([...])` or `FINISH([])`.
- Multiple separate strings are returned in an array.
- The final answer is missing or truncated because the array was not flattened.
