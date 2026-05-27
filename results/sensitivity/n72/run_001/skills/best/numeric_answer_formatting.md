---
description: Return plain numeric values (e.g., ages, lab results) in a concise list
  without extra text
name: numeric_answer_formatting
provenance:
  action: ADD
  epoch: 0
  fixes: 26
  probe_score: 25
  regressions: 1
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task5_20
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task3_14
  - task4_11
  - task9_14
  update_cycle: 0
tags:
- answer_formatting
- numeric_extraction
- age_computation
version: 1
---

# Numeric Answer Formatting

## Pattern Description
You must return a **single numeric value** (or a list of numeric values) as the sole content of the `FINISH` payload. This skill applies whenever the task asks for a measurement, lab result, or patient age and does **not** request a narrative explanation. The goal is to avoid descriptive sentences, units, or string‑quoted numbers, and to provide the answer in the exact format `FINISH([value])` where `value` is a JSON number.

## When to Use This Skill
- When the instruction is of the form "What’s the age of the patient …" or "Give the most recent potassium level …".
- When a lab check (e.g., magnesium, potassium, HbA1c) is required and the expected answer is the numeric result only.
- When the task explicitly says the answer should be a numeric value or a short list of numbers.
- When the agent has already retrieved the relevant `Observation` or `Patient` resource.

## Common Failure Patterns
- Returning a sentence: `"No potassium replacement needed; latest potassium level is 3.9 mmol/L."`
- Including units with the number: `"3.9 mmol/L"`
- Returning the number as a JSON **string**: `FINISH(["3.9"])`
- Adding explanatory text before or after the number.

## Recommended Patterns
**Pattern 1: Extract a numeric lab value**
1. Locate the `Observation` entry that matches the requested code.
2. Use the field `valueQuantity.value` (or `valueQuantity.value` inside `component` if applicable) – this field is already a number.
3. **Do not** concatenate the unit (`valueQuantity.unit`).
4. Return the number directly:
   ```
   FINISH([value])
   ```
   *Correct:* `FINISH([3.9])`
   *Wrong:* `FINISH(["3.9 mmol/L"])`

**Pattern 2: Compute patient age**
1. Retrieve the `Patient` resource and read `birthDate`.
2. Parse the current time supplied in the task context (e.g., `2023-11-13T10:15:00+00:00`).
3. Compute the age in whole years, rounding **down**.
4. Return the integer:
   ```
   FINISH([age])
   ```
   *Correct:* `FINISH([60])`
   *Wrong:* `FINISH(["60"])`

**Pattern 3: Fallback when no value is present**
- If the search returns zero entries, return a short explanatory list as required by the task (e.g., `FINISH(["No magnesium level recorded"])`). Do **not** embed additional prose.

## Example Application
**Task:** "What’s the age of the patient with MRN of S2874099?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S2874099`
2. Extract `birthDate` = `1963-01-29`.
3. Current time = `2023-11-13T10:15:00+00:00` → age = 60 (rounded down).
4. Output:
   ```
   FINISH([60])
   ```

**Task:** "Check patient S3213957's most recent potassium level. If low, then order replacement…"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S3213957`
2. Find the latest entry, read `valueQuantity.value` = `3.9`.
3. Since the task only needs the numeric value for the decision, return:
   ```
   FINISH([3.9])
   ```
   (The ordering logic can then use this number.)

## Success Indicators
- The final `FINISH` payload contains a JSON array with **only numbers** (or a single string when the task explicitly asks for a textual placeholder).
- No units, no explanatory sentences, and no surrounding quotes around numbers.

## Failure Indicators
- The output includes any alphabetic characters, spaces, or unit symbols.
- Numbers are wrapped in quotes, turning them into strings.
- The answer is a full sentence rather than a bare numeric list.
