---
description: "Validate that FINISH output for lab queries matches the required numeric/value\
  \ and ISO\u2011date schema"
name: enforce_lab_result_answer_schema
provenance:
  action: ADD
  epoch: 1
  fixes: 26
  probe_score: 8
  regressions: 2
  triggering_sample_ids:
  - task9_27
  - task10_20
  - task5_17
  - task10_17
  - task1_7
  - task9_11
  - task5_16
  - task10_24
  - task9_22
  - task9_28
  update_cycle: 0
tags: []
version: 1
---

# enforce_lab_result_answer_schema

## Pattern Description
You must guarantee that any answer you provide for a task that requests a laboratory result (value and/or collection date) follows a strict schema. The answer should be a JSON array where the first element is a numeric value (float or integer) representing the lab measurement, and the second element—when a date is required—is an ISO‑8601 timestamp string. If the task only asks for a single numeric result (e.g., magnesium level), the array must contain exactly one numeric element. Returning free‑text sentences, string‑encoded numbers, or arrays of strings is a failure.

## When to Use This Skill
- When the instruction asks for "the last *X* value" and "when it was recorded" (e.g., HbA1c, potassium, magnesium).
- When the instruction expects a numeric result only (e.g., "What’s the most recent magnesium level?").
- When you have already performed a GET /Observation query and extracted the relevant fields.

## Common Failure Patterns
- `FINISH(["5.0","2023-11-09T10:06:00+00:00"])` – numbers are quoted as strings.
- `FINISH(["No potassium replacement needed; latest potassium 3.9 mmol/L is above threshold."])` – a single narrative string instead of a structured array.
- `FINISH(["6.1", "2023-10-13T22:22:00+00:00"])` – both elements are strings.
- `FINISH([-1])` for a task that explicitly requires a value + date (should be `[ -1, "" ]` or raise a separate “no result” flag).

## Recommended Patterns
**Pattern 1: Extract and format a numeric value with a date**
1. From the Observation bundle, locate the most recent entry (`entry[0]`).
2. Read `valueQuantity.value` (or `valueDecimal`, `valueQuantity.value` for LOINC labs) – keep it as a number, **do not** cast to string.
3. Read `effectiveDateTime` (or `issued` if `effectiveDateTime` missing) – keep the exact ISO‑8601 string.
4. Construct the answer as:
   ```json
   FINISH([valueNumber, "2023-11-09T10:06:00+00:00"])
   ```
   where `valueNumber` is a raw numeric literal (e.g., `5.0`).

**Pattern 2: Extract a single numeric value only**
1. Follow steps 1‑2 above.
2. Return:
   ```json
   FINISH([valueNumber])
   ```
   (no surrounding quotes).

**Pattern 3: No recent result**
1. If the Observation search returns `total = 0` or all entries are older than the required window, return a sentinel numeric value **and** an empty string when a date is required:
   - For value‑only tasks: `FINISH([-1])`.
   - For value‑plus‑date tasks: `FINISH([-1, ""])`.
2. Do **not** embed explanatory text in the array.

## Example Application
**Task:** "What’s the last HbA1C value for patient S3114648 and when was it recorded?"

**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S3114648`.
2. Identify the most recent Observation entry.
3. Extract `valueQuantity.value` → `6.1` (numeric).
4. Extract `effectiveDateTime` → `"2023-10-13T22:22:00+00:00"`.
5. Return:
   ```json
   FINISH([6.1, "2023-10-13T22:22:00+00:00"])
   ```

**Correct output:** `FINISH([6.1, "2023-10-13T22:22:00+00:00"])`
**Wrong output:** `FINISH(["6.1","2023-10-13T22:22:00+00:00"])` or a narrative string.

## Success Indicators
- The FINISH payload is a JSON array with the exact number of elements required by the task.
- The first element is a raw numeric literal (no quotes).
- The second element, when present, is a valid ISO‑8601 datetime string.
- No extra explanatory text appears inside the array.

## Failure Indicators
- FINISH contains quoted numbers or any string values where a number is expected.
- The array length does not match the task’s specification (e.g., a single string for a value‑plus‑date request).
- Narrative sentences are returned instead of a structured array.
- The date string is missing or malformed.

**Tags:** ["answer_format", "lab_result", "validation"]
