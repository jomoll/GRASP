---
description: "Fetch the most recent Observation for a given code/patient within 24\u202F\
  h and return its numeric value or -1"
name: retrieve_recent_observation
provenance:
  action: ADD
  epoch: 2
  fixes: 21
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task4_21
  - task4_7
  - task4_6
  - task10_17
  - task2_9
  - task10_13
  - task10_20
  - task10_27
  - task10_18
  - task9_3
  update_cycle: 0
tags: []
version: 1
---

# Retrieve Recent Observation Value

## Pattern Description
You must translate any task that asks for the most recent value of a lab or vital‑sign Observation (e.g., “most recent magnesium level within last 24 hours”) into a concrete FHIR GET request, extract the numeric result, and return it in a `FINISH([value])` array. If no qualifying Observation exists, return `FINISH([-1])`. This pattern centralises the logic for building the query, handling the 24‑hour date filter, sorting by `effectiveDateTime`, and normalising the extracted value (e.g., `valueQuantity.value` or a numeric `valueString`).

## When to Use This Skill
- When a task asks for the *most recent* value of a specific Observation code within the last 24 hours.
- When the task specifies a code literal (e.g., `"MG"`, `"K"`, `"A1C"`) and a patient identifier (MRN like `S123456`).
- When the required answer is a single number (or `-1` if unavailable) and no ordering or further logic is described.

## Common Failure Patterns
- Agent does **not** issue any GET request at all.
- GET URL omits the patient identifier or the `date=ge…` filter, returning unrelated observations.
- Extraction uses the wrong field (`valueString` with units, `valueQuantity.unit` concatenated, or `effectiveDateTime` instead of the numeric value).
- Agent returns a free‑text placeholder instead of the numeric array.

## Recommended Patterns
**Pattern 1: Core retrieval and extraction**
1. Identify the Observation code from the task context (e.g., `code "MG"`).
2. Identify the patient MRN from the task (e.g., `patient S1521703`).
3. Compute the ISO‑8601 timestamp for *now minus 24 hours* (use the provided current time).
4. Issue:
   ```
   GET http://localhost:8080/fhir/Observation?code={CODE}&patient={MRN}&date=ge{NOW_MINUS_24H}
   ```
5. If the response `Bundle.total` is **0**, go to step 8.
6. Sort the `entry` array by `resource.effectiveDateTime` descending (most recent first).
7. From the first entry, extract the numeric value:
   - Prefer `resource.valueQuantity.value` (number).
   - If missing, fall back to parsing a numeric prefix from `resource.valueString` (e.g., "2.5 mg/dL" → 2.5).
   - **Do not** include the unit; the task expects the value in the unit already defined (e.g., mg/dL).
8. **Output**:
   - If a value was extracted, `FINISH([VALUE])`.
   - If no qualifying Observation, `FINISH([-1])`.

**Pattern 2: Fallback placeholder (optional)**
If the skill is invoked in a context where a placeholder is explicitly required, replace step 8 with:
```json
FINISH(["{placeholder}"])
```
where `{placeholder}` is the task‑specified string.

**Pattern 3: Formatting rule**
Always return a JSON array with a **single numeric element** (or `-1`). Do **not** wrap the number in a string or add explanatory text.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1311412 within last 24 hours?"

**Step‑by‑step:**
1. Code = `MG`, MRN = `S1311412`.
2. Current time = `2023-11-13T10:15:00+00:00`; 24‑h ago = `2023-11-12T10:15:00+00:00`.
3. GET `http://localhost:8080/fhir/Observation?code=MG&patient=S1311412&date=ge2023-11-12T10:15:00+00:00`.
4. Response `Bundle.total = 2`; first entry has `valueQuantity.value = 2.5`.
5. FINISH([2.5])

**Correct output:** `FINISH([2.5])`
**Incorrect output examples:**
- `FINISH(["2.5 mg/dL"])` (unit included)
- `FINISH(["Magnesium is 2.5 mg/dL"] )` (free‑text)
- No GET request issued.

## Success Indicators
- A GET request to `/Observation` with both `code` and `patient` parameters **and** a `date=ge…` filter appears in the agent’s actions.
- The URL uses the exact code string from the task.
- The final `FINISH` contains a single numeric element (or `-1`).

## Failure Indicators
- The agent finishes without issuing any GET request.
- The GET URL is missing the `patient` or `date` parameter.
- The `FINISH` payload is empty, contains a string, or includes explanatory text.
- The extracted value includes the unit or is taken from the wrong field.
