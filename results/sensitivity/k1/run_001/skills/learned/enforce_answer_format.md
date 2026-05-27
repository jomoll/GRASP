---
description: Validate FINISH output matches the answer type explicitly requested in
  the instruction
name: enforce_answer_format
provenance:
  action: MODIFY
  epoch: 3
  fixes: 15
  parent_version: 1
  probe_score: 8
  regressions: 5
  triggering_sample_ids:
  - task9_9
  - task10_15
  - task2_17
  - task1_7
  - task1_6
  - task3_10
  - task2_6
  - task2_1
  - task1_27
  - task2_26
  update_cycle: 1
tags: []
version: 2
---

# Enforce Answer Format

## Pattern Description
You must ensure that the final `FINISH` payload exactly matches the data structure the instruction explicitly demands.  The instruction often states the required shape – a single number, an array of values, or a JSON object with named fields.  Before emitting `FINISH`, parse the instruction for these cues and verify that the payload’s JSON type (number, array, object) and, when applicable, its field names and value types conform.  Reject or correct mismatched outputs instead of passing them through.

## When to Use This Skill
- When the instruction contains phrasing such as:
  - "answer should be a single number"
  - "the answer should be an array"
  - "return a JSON object with `value` and `date` fields"
  - "the answer must be rounded down to an integer"
- Immediately before emitting `FINISH` for any task that expects a structured answer.

## Common Failure Patterns
- Returning `FINISH(["text"])` when the task expects a numeric array like `FINISH([3.8])`.
- Emitting an empty array `FINISH([])` for tasks that require a non‑empty result (e.g., a value or object).
- Providing a plain object `{"value":"5.9%","date":"..."}` when the instruction asked for an array `FINISH([{"value":"5.9%","date":"..."}])`.
- Omitting required field names or using wrong field types (e.g., string instead of number).
- Returning a number when the instruction explicitly says “answer should be an array”.

## Recommended Patterns
**Pattern 1: Detect expected type**
1. Scan the instruction text for keywords:
   - `single number`, `integer`, `rounded down` → expect a JSON number **or** a one‑element numeric array.
   - `array`, `list`, `should be a single number` (but still phrased as array) → expect a JSON array.
   - `object`, `JSON object`, `fields` → expect a JSON object (or an array of objects if “array of objects” is mentioned).
2. Record the expected JSON schema (type, required fields, element type).

**Pattern 2: Validate payload before FINISH**
- If expected type is **number**:
  - `CORRECT`: `FINISH(3.8)` or `FINISH([3.8])` when the instruction says “array with a single number”.
  - `WRONG`: `FINISH(["3.8"])` or `FINISH([])`.
- If expected type is **array**:
  - Ensure the payload is a JSON array with at least one element.
  - Verify each element’s type matches the sub‑type (e.g., number, object).
- If expected type is **object**:
  - Verify the payload is a JSON object.
  - Check required keys exist and their values have the correct primitive type.

**Pattern 3: Fallback / correction**
- If validation fails, do **not** emit `FINISH`. Instead, raise a diagnostic `FINISH_ERROR` (or simply abort) so the higher‑level controller can retry or report the mismatch.
- Optionally, attempt a simple conversion when safe (e.g., strip surrounding quotes from a numeric string) and re‑validate.

## Example Application
**Task:** "What’s the last HbA1C value and when was it recorded? The answer should be a JSON object with fields `value` (string) and `date` (ISO‑8601)."

**Step‑by‑step:**
1. Detect that the instruction demands an **object** with keys `value` and `date`.
2. After extracting the lab result, construct `{ "value": "5.7%", "date": "2023-07-07T11:27:00+00:00" }`.
3. Validate:
   - Payload is an object → ✅
   - Contains `value` (string) and `date` (string) → ✅
4. Emit `FINISH({"value":"5.7%","date":"2023-07-07T11:27:00+00:00"})`.

**Incorrect output:** `FINISH(["5.7%","2023-07-07T11:27:00+00:00"])` → validation fails because payload is an array, not an object.

## Success Indicators
- `FINISH` payload type matches the instruction‑derived schema.
- No warnings about mismatched types appear in logs.
- Downstream consumers receive data they can parse without additional type checks.

## Failure Indicators
- `FINISH` emits an array when an object was required (or vice‑versa).
- Empty arrays are returned for tasks that require a concrete value.
- Field names are missing or have incorrect primitive types.
- The system logs a “answer format mismatch” error.
