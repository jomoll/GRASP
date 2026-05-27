---
description: "Extract the latest observation value (with unit conversion) or return\
  \ the task\u2011specified placeholder when no result is found."
name: observation_value_extraction_with_placeholder
provenance:
  action: ADD
  epoch: 0
  fixes: 21
  probe_score: 19
  regressions: 4
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task4_10
  - task2_16
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  - task2_9
  update_cycle: 0
tags: []
version: 1
---

# Observation Value Extraction with Missing Placeholder Handling

## Pattern Description
You must reliably pull a numeric result from a FHIR Observation bundle and present it exactly as the task expects. The core pattern is:
1. Issue a GET on the Observation endpoint with the appropriate `code`, `patient` (or `subject`), and any required date filter.
2. Inspect the returned Bundle. If `total` > 0, locate the most recent entry (usually the first in `entry`). Extract the numeric value from `valueQuantity.value` (or `valueString` when the value is a simple string that can be parsed to a number). Convert the unit to the one required by the task (e.g., mg/dL for magnesium) before returning the plain number.
3. If the Bundle reports `total` = 0, **do not** attempt further extraction. Instead, return the placeholder defined in the task description (commonly `-1` or the string "-1"). This rule prevents the agent from fabricating values or leaving the answer empty.

## When to Use This Skill
- When a task asks for the *most recent* value of a lab or vital sign (e.g., magnesium, HbA1c, potassium) and specifies a placeholder for “no recent measurement”.
- When the GET request includes a date filter (`date=ge...`) and the response may be empty.
- When the task requires the value in a specific unit (e.g., mg/dL) and the Observation may store it in another unit (e.g., mmol/L).

## Common Failure Patterns
- Returning the placeholder `-1` even though a valid observation exists (bundle `total` > 0 but the agent never inspected `entry`).
- Extracting the wrong field, such as `valueString` that contains a formatted text like `"3.5 mmol/L"` instead of the numeric `valueQuantity.value`.
- Forgetting to apply the missing‑value rule, leading to an empty FINISH payload or a JSON array with no element.
- Using the wrong placeholder type (e.g., returning the number `-1` when the task expects the string `"-1"`).

## Recommended Patterns
**Pattern 1: Core extraction workflow**
1. Perform the GET request exactly as the task describes.
2. Parse the JSON response.
3. If `bundle["total"]` > 0:
   - Take the first entry in `bundle["entry"]` (most recent).
   - If `resource["valueQuantity"]` exists, set `raw_value = resource["valueQuantity"]["value"]` and `unit = resource["valueQuantity"]["unit"]`.
   - If only `valueString` exists, attempt to parse a number from it (e.g., using regex). Set `raw_value` accordingly.
   - Convert `raw_value` to the required unit if `unit` differs (e.g., mmol/L → mg/dL for magnesium: multiply by 2.0).
   - **FINISH([converted_value])**.
4. Else (`total` == 0):
   - Use the placeholder defined in the task (usually `-1`).
   - **FINISH(["-1"])** (string placeholder) or **FINISH([-1])** (numeric) matching the task’s expected type.

**Pattern 2: Fallback verification**
- After extraction, double‑check that the resulting value is a finite number. If parsing fails, fall back to the placeholder.

**Pattern 3: Output formatting**
- The FINISH payload must be a JSON array containing a single element: either the numeric value **or** the exact placeholder string. No extra text, units, or explanatory sentences.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3213957 within last 24 hours? The answer should be a single number in mg/dL, and `-1` if no measurement is available."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=MG&patient=S3213957&date=ge2023-11-12T10:15:00Z`
2. Response bundle shows `"total": 1` and the first entry contains:
   ```json
   "valueQuantity": { "value": 0.8, "unit": "mmol/L" }
   ```
3. Convert: 0.8 mmol/L × 2.0 = 1.6 mg/dL.
4. FINISH([1.6])

**If the bundle had `"total": 0`**:
- Directly FINISH(["-1"]).

## Success Indicators
- FINISH payload contains exactly one element, either a plain number or the exact placeholder string.
- No extra explanatory text is present.
- When a value exists, the extracted number matches the `valueQuantity.value` (after any required unit conversion).

## Failure Indicators
- FINISH contains a formatted sentence or includes units (e.g., `"Magnesium is 1.6 mg/dL"`).
- The agent returns an empty array or omits the placeholder when `total` = 0.
- The extracted value is taken from the wrong field (e.g., `valueString` with units still attached).
- Unit conversion is not applied when the source unit differs from the required unit.
