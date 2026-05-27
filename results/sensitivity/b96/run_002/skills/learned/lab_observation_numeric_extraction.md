---
description: Extract numeric lab values, convert to mg/dL, and return as a bare number
  (no quotes)
name: lab_observation_numeric_extraction
provenance:
  action: ADD
  epoch: 1
  fixes: 14
  probe_score: 8
  regressions: 0
  triggering_sample_ids:
  - task9_27
  - task10_20
  - task4_15
  - task2_1
  - task5_17
  - task4_27
  - task2_25
  - task10_17
  - task2_6
  - task10_10
  update_cycle: 0
tags: []
version: 1
---

# Lab Observation Numeric Extraction

## Pattern Description
You must reliably pull a numeric result from a FHIR Observation that uses `valueQuantity`. The goal is to return the value **as a number**, already expressed in the target unit (mg/dL for magnesium, potassium, etc.). This pattern applies to any lab‑type query where the task expects a single numeric answer rather than a free‑text string.

## When to Use This Skill
- When a task asks for "the most recent *[lab]* level" and specifies that the answer should be a single number in mg/dL (e.g., magnesium, potassium).
- When the Observation resource contains `valueQuantity` with a `value` and a `unit` that may differ from mg/dL.
- When the agent is about to call `FINISH` with the extracted value.

## Common Failure Patterns
- Returning the value as a JSON string: `FINISH(["2.2"])`.
- Ignoring the `unit` field and returning the raw value (e.g., mmol/L) without conversion.
- Returning an array of strings or a formatted sentence instead of a bare number.
- Omitting a fallback `-1` when no recent observation exists.

## Recommended Patterns
**Pattern 1: Core extraction and conversion**
1. Perform the GET request for the Observation (already done by other skills).
2. From the returned Bundle, locate the most recent entry (`entry[0]`).
3. Access `resource.valueQuantity.value` **as a number** and `resource.valueQuantity.unit`.
4. If `unit` is already `mg/dL`, keep the number unchanged.
5. If `unit` is different (e.g., `mmol/L` for magnesium), apply the appropriate conversion factor:
   - Magnesium: `mg/dL = value * 2.03`
   - Potassium: `mg/dL = value * 39.1`
   - (Add other labs as needed.)
6. Round the result to one decimal place (or as clinically appropriate).
7. Call `FINISH([numeric_value])` **without quotes**.

**Pattern 2: Fallback when no recent observation**
- If the Observation search returns `total = 0`, call `FINISH([-1])`.

**Pattern 3: Validation before finishing**
- Verify that the argument passed to `FINISH` is a JSON number, not a string.
- If the value is `NaN` after conversion, treat it as missing and use the fallback.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3057899 within last 24 hours?"

**Step‑by‑step:**
1. GET `.../Observation?code=MG&patient=Patient/S3057899&date=ge2023-11-12T10:15:00Z`.
2. Find the first entry in the Bundle.
3. Suppose the entry contains:
   ```json
   "valueQuantity": { "value": 1.08, "unit": "mmol/L" }
   ```
4. Convert: `1.08 * 2.03 = 2.19` → round to `2.2`.
5. Call `FINISH([2.2])`.

**Correct output:** `FINISH([2.2])`
**Wrong output:** `FINISH(["2.2"])` or `FINISH([2.2, "mg/dL"])`

## Success Indicators
- The final `FINISH` call contains a single JSON number (e.g., `[2.2]`).
- The number reflects the correct mg/dL conversion when the original unit differs.
- When no observation is found, the output is exactly `FINISH([-1])`.

## Failure Indicators
- The `FINISH` argument is a string or an array containing a string.
- The returned number does not match the expected mg/dL conversion (e.g., still in mmol/L).
- The agent returns extra explanatory text instead of the bare number.

---
*Tags:* [lab, observation, numeric_extraction, unit_conversion, magnesium, potassium]
