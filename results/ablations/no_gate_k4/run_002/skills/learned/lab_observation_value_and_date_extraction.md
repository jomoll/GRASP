---
description: Extract a lab observation's numeric value and its timestamp, returning
  them in the required format
name: lab_observation_value_and_date_extraction
provenance:
  action: ADD
  epoch: 4
  no_gate: true
  triggering_sample_ids:
  - task10_13
  - task9_5
  - task9_22
  - task5_7
  - task10_10
  - task1_10
  - task5_3
  - task10_15
  - task10_18
  - task5_17
  update_cycle: 1
tags:
- lab
- observation
- extraction
- value
- date
version: 1
---

# Lab Observation Value and Date Extraction

## Pattern Description
When a task asks for the most recent value of a lab test **and** when it was recorded, you must query the appropriate Observation resource, pull out the numeric result and the `effectiveDateTime`, and return both pieces exactly as the instruction specifies. This skill guarantees the correct field selection (`valueQuantity.value` and `effectiveDateTime`) and proper output formatting.

## When to Use This Skill
- The instruction contains phrases like "last ... value" **and** "when was it recorded".
- The task mentions a specific LOINC or short code (e.g., `MG` for magnesium, `HbA1c`).
- The expected answer is a pair `[value, "YYYY-MM-DD"]` (or a single string combining both) rather than a free‑text sentence.
- The agent has already performed a `GET` on an `Observation` endpoint.

## Common Failure Patterns
- Returning the whole Observation bundle instead of extracting the scalar value.
- Including the unit in the value (e.g., `"2.2 mg/dL"` instead of `2.2`).
- Omitting the date or returning the wrong timestamp field (`issued` vs `effectiveDateTime`).
- Wrapping the result in a nested array like `[[2.2, "2023-11-12"]]`.

## Recommended Patterns
**Pattern 1: Core extraction**
1. Ensure a `GET` was made to `/Observation` with the correct `code` and patient filter, sorted descending by date, limited to 1.
2. Parse the response Bundle:
   - Verify `total > 0`.
   - Locate the first entry's `resource`.
   - Extract `valueQuantity.value` as a number (do **not** concatenate the unit).
   - Extract `effectiveDateTime` (ISO‑8601 string, date portion only if required).
3. Construct the output array exactly as required, e.g., `FINISH([2.2, "2023-11-12"])`.

**Pattern 2: Fallback when no result**
- If `total == 0`, return the sentinel value defined by the task (often `-1` or a specific message) and **do not** attempt ordering logic.

**Pattern 3: Formatting rules**
- Do not add surrounding text, units, or explanatory sentences.
- Keep numeric values as raw numbers, not strings, unless the task explicitly asks for a string.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3213957 within last 24 hours?"

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Observation?code=MG&patient=S3213957&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z&_sort=-date&_count=1`.
2. Receive Bundle with `total = 1`.
3. Extract `valueQuantity.value = 2.2` and `effectiveDateTime = "2023-11-12T14:20:00Z"`.
4. Return `FINISH([2.2, "2023-11-12"])` (or just `[2.2]` if the task only wants the value).

**CORRECT output:** `FINISH([2.2, "2023-11-12"])`
**WRONG output:** `FINISH(["2.2 mg/dL on 2023-11-12"])` or `FINISH([[2.2, "2023-11-12"]))`.

## Success Indicators
- The action log shows a correctly parameterized `GET /Observation` before `FINISH`.
- The `FINISH` payload is a flat array containing a number and, when required, a date string.
- No unit text or extra phrasing appears in the output.

## Failure Indicators
- The agent returns a string sentence instead of a numeric/date array.
- The extracted value includes the unit (e.g., `"2.2 mg/dL"`).
- The date is missing or taken from the wrong field (`issued`).
- The output array is nested or contains extra elements.
