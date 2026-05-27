---
description: "Extract numeric lab values safely, rejecting placeholder or non\u2011\
  numeric results before answering."
name: observation_value_extraction_and_validation
provenance:
  action: ADD
  epoch: 3
  fixes: 11
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task9_8
  - task10_20
  - task4_28
  - task10_24
  - task9_3
  - task8_7
  - task9_22
  - task8_13
  - task8_21
  - task9_5
  update_cycle: 1
tags:
- observation
- validation
- lab
- numeric_extraction
version: 1
---

# Observation Numeric Value Extraction and Placeholder Rejection

## Pattern Description
You must reliably pull a numeric result from a FHIR Observation while guarding against placeholder or malformed values. Many lab observations store a sentinel like `-1`, `0`, or a string such as "N/A" when the real measurement is unavailable. Treating these as legitimate results leads to wrong answers (e.g., returning `-1` even though a valid magnesium value exists). This skill defines a deterministic extraction pipeline that validates the numeric payload, applies unit conversion when needed, and skips any observation that does not contain a genuine measurement.

## When to Use This Skill
- When a task asks for the **most recent numeric lab value** (e.g., magnesium, potassium, HbA1c) within a time window and expects a single number.
- When the numeric result determines a downstream decision (e.g., order replacement if value is low).
- Whenever you receive an Observation bundle and need to decide whether the contained value is usable.

## Common Failure Patterns
- Returning `-1` because the first Observation in the bundle had `valueQuantity.value = -1` (placeholder) even though later entries contain a real value.
- Accepting a string like `"N/A"` or an empty `valueQuantity` as a valid result.
- Using `valueString` that includes units (e.g., `"1.6 mg/dL"`) instead of extracting the numeric component.
- Failing to convert units (e.g., µmol/L → mg/dL) and thus returning an out‑of‑range number.

## Recommended Patterns
**Pattern 1: Core extraction and validation**
1. Sort the Observation entries by `effectiveDateTime` descending (most recent first).
2. For each entry:
   - If `valueQuantity` exists, read `valueQuantity.value` as a number.
   - If the number is **null, NaN, ≤ 0, or exactly `-1`**, treat it as *invalid* and continue to the next entry.
   - If a `valueQuantity.unit` is present and differs from the target unit, apply the appropriate conversion (e.g., `µmol/L → mg/dL` for magnesium: divide by 0.822).
   - **Return** the first valid numeric value.
3. If no entry yields a valid number, return the sentinel `-1` to indicate “no measurement”.

**Pattern 2: Fallback to alternative fields**
- If `valueQuantity` is missing, check `valueString` for a plain number (e.g., `"1.6"`).
- Parse the string with a regular expression extracting the first numeric token.
- Apply the same validation rules as above.

**Pattern 3: Formatting the final answer**
- Output **only** the numeric value (or `-1`) inside a JSON array: `FINISH([value])`.
- Do **not** include units, explanatory text, or additional brackets.

## Example Application
**Task:** "What’s the most recent magnesium level of patient S1876702 within last 24 hours?"

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S1876702` → receive a Bundle with several entries.
2. Sort entries by `effectiveDateTime` descending.
3. Examine the first entry:
   - `valueQuantity.value = -1` → invalid, skip.
4. Examine the second entry:
   - `valueQuantity.value = 1.6` and `unit = "mg/dL"` → valid.
5. No conversion needed; return `FINISH([1.6])`.

**Correct output:** `FINISH([1.6])`
**Wrong output:** `FINISH(["1.6 mg/dL"])` or `FINISH([-1])` when a valid value exists.

## Success Indicators
- The agent returns a numeric value when a valid Observation exists.
- Placeholder values (`-1`, `0`, "N/A") are never returned as the answer.
- Unit conversion is applied correctly, and the final output contains only the number.

## Failure Indicators
- `FINISH([-1])` is produced despite a later Observation containing a proper numeric result.
- The answer includes units or free‑text (e.g., `"1.6 mg/dL"`).
- The agent orders or refrains from ordering based on a placeholder value rather than the true measurement.
