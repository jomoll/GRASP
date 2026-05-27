---
description: Ensures numeric answers are returned as JSON numbers, not quoted strings
name: numeric_answer_formatting
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 9
  regressions: 1
  triggering_sample_ids:
  - task9_22
  - task4_15
  - task4_26
  - task9_3
  - task1_11
  - task2_16
  - task9_8
  - task1_15
  - task10_12
  - task10_17
  update_cycle: 0
tags: []
version: 1
---

# Numeric Answer Formatting

## Pattern Description
You must always return a plain JSON number (or a JSON object containing numbers) when a task asks for a numeric value such as a patient’s age, a lab result, or a calculated score.  Wrapping the number in quotes turns it into a string, which the evaluation harness treats as the wrong type.  This skill applies to any task where the expected answer is a single numeric value or a simple numeric field inside a JSON object.

## When to Use This Skill
- When the instruction asks for "age", "value", "count", "score", "percentage", or any other scalar numeric result.
- When the answer should be a JSON object with numeric fields (e.g., `{ "value": 5.9, "date": "2023-11-12" }`).
- When the task explicitly says the answer must be a number (e.g., "rounded down to an integer").

## Common Failure Patterns
- `FINISH(["66"])` – number returned as a quoted string.
- `FINISH(["5.9%"])` – includes units or symbols, making it a string.
- Returning a free‑text sentence instead of a JSON number or object.

## Recommended Patterns
**Pattern 1: Return a plain JSON number**
1. Extract the numeric value from the FHIR resource (e.g., calculate age from `birthDate`).
2. Ensure the value is a JavaScript/JSON number, not a string.
3. Call `FINISH([<number>])`.

   **CORRECT:** `FINISH([66])`
   **WRONG:** `FINISH(["66"])`

**Pattern 2: Return a structured JSON object for lab results**
1. Locate the most recent Observation matching the code.
2. Extract `valueQuantity.value` as a number and `effectiveDateTime` as an ISO‑8601 string.
3. Build an object: `{ "value": <number>, "date": "<ISO‑date>" }`.
4. Call `FINISH([<object>])`.

   **CORRECT:** `FINISH([{ "value": 5.9, "date": "2023-11-12" }])`
   **WRONG:** `FINISH(["5.9% recorded on 2023-11-12"])`

**Pattern 3: Fallback when no numeric data is available**
- If the required observation is missing, return the sentinel number `-1` **as a number**, not a string.
  `FINISH([-1])`

## Example Application
**Task:** "What's the age of the patient with MRN of S2119664?"

**Step‑by‑step:**
1. `GET {api_base}/Patient?identifier=S2119664`
2. From the returned Patient resource, read `birthDate` (e.g., `1957-04-15`).
3. Compute age = floor(currentDate - birthDate in years).
4. `FINISH([66])`  ← note the number is not quoted.

**Task:** "What’s the last HbA1c value and when was it recorded for patient S1311412?"

**Step‑by‑step:**
1. `GET {api_base}/Observation?code=A1C&patient=S1311412`
2. Identify the Observation with the most recent `effectiveDateTime`.
3. Extract `valueQuantity.value` (e.g., `5.9`) and `effectiveDateTime` (e.g., `2023-11-12`).
4. `FINISH([{ "value": 5.9, "date": "2023-11-12" }])`

## Success Indicators
- The final `FINISH` call contains a JSON array whose first element is a number (e.g., `[66]`) or a JSON object with numeric fields.
- No quotation marks surround the numeric value.
- For missing data, the sentinel `-1` appears as a number, not a string.

## Failure Indicators
- The `FINISH` payload contains quoted numbers (`["66"]`).
- The answer is a free‑text sentence instead of a JSON number/object.
- Units or symbols are concatenated to the number, turning it into a string.
