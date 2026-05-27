---
description: Extract latest magnesium level, verify unit, convert to mg/dL, and return
  a plain number (or -1).
name: magnesium_observation_value_extraction
provenance:
  action: ADD
  blind_select: random
  epoch: 0
  fixes_unused: 10
  probe_score_unused: -1
  regressions_unused: 3
  triggering_sample_ids:
  - task9_1
  - task2_25
  - task10_27
  - task4_26
  - task4_27
  - task10_18
  - task9_6
  - task9_28
  - task2_22
  - task4_20
  update_cycle: 1
tags:
- magnesium
- unit_conversion
- observation_extraction
version: 1
---

# Magnesium Observation Value Extraction and Unit Conversion

## Pattern Description
You must reliably retrieve a serum magnesium measurement, ensure the reported unit matches the expected clinical unit (mg/dL), and perform any necessary conversion. This pattern is reusable for any lab where the source system may store values in alternative units (e.g., mmol/L). By normalising the value before answering, you avoid the common *quantity_unit_mismatch* failure where the agent returns the raw value with its original unit or as a string.

## When to Use This Skill
- When a task asks for "the most recent magnesium level" (or any other lab) and explicitly states the answer should be a **single number** in **mg/dL**.
- When the task includes a time window (e.g., "within the last 24 hours").
- When the Observation bundle may contain `valueQuantity` with a unit other than mg/dL (e.g., `mmol/L`).
- When the expected answer is `-1` if no qualifying measurement exists.

## Common Failure Patterns
- Returning `FINISH(["2.5"])` – value is a string inside an array.
- Returning the raw value without checking `valueQuantity.unit` (e.g., the source is `mmol/L`).
- Concatenating the unit with the number (`"2.5 mmol/L"`).
- Selecting the first entry in the bundle without sorting by `effectiveDateTime`.
- Omitting the conversion factor (1 mmol/L ≈ 2.43 mg/dL).

## Recommended Patterns
**Pattern 1: Core extraction and unit handling**
1. **Query** the Observation endpoint with the appropriate code and patient identifier, adding optional date filters for the required window.
   ```
   GET {api_base}/Observation?code=MG&patient={MRN}&date=ge{start}&date=le{end}
   ```
2. **Sort** the returned entries by `effectiveDateTime` descending and pick the first entry (most recent).
3. **Inspect** the `valueQuantity` object:
   - `valueQuantity.value` → numeric value
   - `valueQuantity.unit` → unit string
4. **Validate** the unit:
   - If unit is `mg/dL` (case‑insensitive), keep the value.
   - If unit is `mmol/L`, convert: `value_mgdl = value * 2.43`.
   - If unit is missing or unrecognised, treat as no valid result.
5. **Round** the final number to a reasonable precision (e.g., one decimal).
6. **Output** exactly:
   - `FINISH([<number>])` when a valid value exists.
   - `FINISH([-1])` when no qualifying observation is found or unit validation fails.

**Pattern 2: Fallback when no observations**
- If the bundle `total` is `0` or after filtering no entry remains, immediately `FINISH([-1])`.

**Pattern 3: Formatting rule**
- Never wrap the number in quotes.
- Do not include the unit in the output array.
- Do not return a JSON object; the answer must be a plain array with a single numeric element.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1311412 within last 24 hours?"

**Step‑by‑step:**
1. Compute the time window:
   - `now = 2023-11-13T10:15:00Z`
   - `start = now - 24h = 2023-11-12T10:15:00Z`
2. Issue the GET request:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S1311412&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z
   ```
3. Receive a Bundle with two entries. The first entry (most recent) contains:
   ```json
   "valueQuantity": { "value": 1.03, "unit": "mmol/L" }
   ```
4. Convert:
   - `1.03 * 2.43 = 2.5` (rounded to one decimal).
5. Return:
   ```
   FINISH([2.5])
   ```

**Correct output:** `FINISH([2.5])`
**Wrong output examples:**
- `FINISH(["2.5"])` (string inside array)
- `FINISH(["2.5 mmol/L"])` (unit included)
- `FINISH([-1])` when a valid observation exists.

## Success Indicators
- The agent returns a single numeric element in the array.
- The numeric value matches the mg/dL conversion when the source unit was mmol/L.
- No unit text appears in the final answer.
- `-1` is only returned when the bundle is empty or unit validation fails.

## Failure Indicators
- The answer array contains a string or includes the unit.
- The numeric value is unconverted (e.g., still in mmol/L).
- The agent selects an older observation instead of the most recent.
- The agent returns an empty array or a JSON object instead of the required format.
