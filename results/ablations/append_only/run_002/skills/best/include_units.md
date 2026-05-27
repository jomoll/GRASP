---
description: Append the correct measurement unit to extracted Observation values and
  convert when needed
name: include_units
provenance:
  action: ADD
  epoch: 0
  fixes: 6
  probe_score: 4
  regressions: 4
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  - task3_7
  update_cycle: 0
tags: []
version: 1
---

# Include Units in Observation Value Extraction

## Pattern Description
You must always return a lab result together with its measurement unit, even when the task description only mentions a numeric answer. The central reusable lesson is to treat the unit as part of the answer, not as ancillary text. This prevents quantity‑unit mismatches where the agent returns a bare number (e.g., `2.0`) instead of `2.0 mg/dL`. The pattern applies to any FHIR Observation that uses `valueQuantity` (or `valueString` with a parsable unit) and where the downstream task expects the value expressed in a specific unit.

## When to Use This Skill
- When a task asks for the most recent value of a lab Observation (e.g., magnesium, potassium, HbA1c) and the instruction mentions a target unit (e.g., "mg/dL").
- When the Observation resource contains `valueQuantity.value` **and** `valueQuantity.unit` fields.
- When the task expects a single string or number **with** unit, not a free‑text sentence.
- When the agent has already identified the correct Observation entry (most recent within the required date range).

## Common Failure Patterns
- Returning only `valueQuantity.value` (e.g., `2.0`) and omitting `valueQuantity.unit`.
- Concatenating the unit to the value with extra spaces or punctuation (e.g., `"2.0 mg/dL "`).
- Using the wrong field such as `valueString` that already contains a formatted phrase (e.g., `"2.0 mg/dL"`) without parsing the numeric part.
- Ignoring required unit conversion (e.g., the Observation is in mmol/L but the task wants mg/dL).

## Recommended Patterns
**Pattern 1: Core extraction with unit**
1. After you have the Observation Bundle, locate the entry with the most recent `effectiveDateTime` that satisfies any date filter.
2. From that entry, read `valueQuantity.value` **and** `valueQuantity.unit`.
3. If the unit matches the target unit specified in the task, construct the answer as `"{value} {unit}"` (e.g., `"2.0 mg/dL"`).
4. If the unit differs, apply the appropriate conversion (see conversion table below) before formatting.

**Pattern 2: Fallback when unit is missing**
- If `valueQuantity.unit` is absent, check `valueString` for a parsable unit using a regex like `/([0-9.]+)\s*([a-zA-Z/]+)$/`.
- If still unavailable, default to the unit given in the task description; **but** annotate the answer with a comment that the original unit was unknown (e.g., `"2.0 mg/dL (unit inferred)"`).

**Pattern 3: Formatting for FINISH**
- The FINISH payload must be a JSON array containing a single string: `FINISH(["{value} {unit}"])`.
- Do **not** wrap the answer in additional explanatory text.

**Conversion Table (common lab conversions)**
| From Unit | To Unit | Formula |
|-----------|---------|---------|
| mmol/L (magnesium) | mg/dL | `value * 2.43` |
| mmol/L (potassium) | mEq/L | `value * 1` (same) |
| % (HbA1c) | % (no change) | identity |

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0636132 within last 24 hours? The answer should be a single number converted to a unit of mg/dL."

**Step‑by‑step:**
1. Issue GET `http://localhost:8080/fhir/Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00Z`.
2. Parse the returned Bundle and locate the entry with the highest `effectiveDateTime`.
3. Extract `valueQuantity.value = 0.82` and `valueQuantity.unit = "mmol/L"`.
4. Convert: `0.82 * 2.43 = 1.99` → round to one decimal if desired → `2.0`.
5. Format answer: `FINISH(["2.0 mg/dL"])`.

**CORRECT output:** `FINISH(["2.0 mg/dL"])`
**WRONG output:** `FINISH(["2.0"])` (unit omitted) or `FINISH(["Magnesium is 2.0 mg/dL."])` (extra text).

## Success Indicators
- The FINISH payload contains a single string with a numeric value **followed by a space and the correct unit**.
- The unit matches the one requested in the task or is a correctly converted equivalent.
- No additional explanatory text is present.

## Failure Indicators
- The answer string lacks a unit (e.g., `"2.0"`).
- The unit is present but malformed (extra spaces, punctuation, or wrong case).
- The agent returns a list of numbers or a sentence instead of the required single‑string format.
- The conversion factor was not applied when the source unit differs from the target.
