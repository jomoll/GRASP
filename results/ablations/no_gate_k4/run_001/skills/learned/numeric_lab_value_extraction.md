---
description: Extract a numeric lab result, normalize its unit to mg/dL, and return
  the plain number (or -1 if missing).
name: numeric_lab_value_extraction
provenance:
  action: ADD
  epoch: 1
  no_gate: true
  triggering_sample_ids:
  - task9_28
  - task10_20
  - task4_10
  - task5_17
  - task9_6
  - task4_27
  - task8_29
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Numeric Lab Value Extraction and Unit Normalization

## Pattern Description
You must treat any lab‑value query as a two‑step process: first locate the numeric `valueQuantity.value` and its `valueQuantity.unit`, then ensure the result is expressed as a plain number in the unit required by the task (most often **mg/dL** for magnesium).  If the source unit differs (e.g., **mmol/L**), apply the appropriate conversion factor and discard the unit string before forming the final `FINISH` payload.  This prevents mismatches where the agent returns a string like `"1.8 mg/dL"` instead of the expected numeric `1.8`.

## When to Use This Skill
- When a task asks for "a single number" or "the value converted to mg/dL" for a lab observation.
- When the Observation resource contains `valueQuantity` with a unit that may differ from the target unit.
- When the task expects `-1` if no recent measurement exists.

## Common Failure Patterns
- Returning `"1.8 mg/dL"` (string with unit) instead of `1.8` (numeric).
- Using the wrong field such as `valueString` or concatenating `valueQuantity.unit` to the number.
- Failing to convert from `mmol/L` (or other units) to `mg/dL` before output.
- Omitting the `-1` placeholder when the bundle has `total: 0`.

## Recommended Patterns
**Pattern 1: Core extraction & conversion**
1. After the GET, verify the response is a `Bundle` with `total > 0`.
2. Locate the most recent entry (usually the first in `entry`).
3. Read `valueQuantity.value` (numeric) and `valueQuantity.unit` (string).
4. If `unit` is `mmol/L` (or any non‑mg/dL unit), apply the conversion factor:
   - Magnesium: `mg/dL = value * 2.42`
   - Calcium: `mg/dL = value * 4.0` (example)
5. Round or truncate as appropriate (typically keep one decimal).
6. **FINISH([numeric_value])** – no unit string.

**Pattern 2: Fallback when no observation**
1. If `Bundle.total == 0` or the `entry` array is empty, **FINISH([-1])**.

**Pattern 3: Output formatting**
- Always output a JSON array containing a single number (or -1).  Do **not** wrap the number in quotes or append any text.
- Example correct output: `FINISH([1.8])`
- Example wrong output: `FINISH(["1.8 mg/dL"])` or `FINISH(["1.8"] )`.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S6227720 within last 24 hours? The answer should be a single number converted to mg/dL, and -1 if unavailable."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S6227720&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`
2. Response bundle shows `valueQuantity.value = 0.74` and `valueQuantity.unit = "mmol/L"`.
3. Convert: `0.74 * 2.42 = 1.79` → round to `1.8`.
4. `FINISH([1.8])`.

## Success Indicators
- The agent issues the GET query, extracts `valueQuantity.value`, performs conversion if needed, and calls `FINISH` with a bare numeric array.
- The output matches the expected type (number) and unit (mg/dL) without extra text.

## Failure Indicators
- The FINISH payload contains a quoted string or includes the unit.
- The agent skips conversion and returns the raw value from the source unit.
- The agent returns a placeholder string instead of `-1` when no observation exists.
