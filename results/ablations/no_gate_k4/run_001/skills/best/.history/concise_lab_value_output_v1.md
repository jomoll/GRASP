---
description: Force FINISH to return only the raw lab value with unit (or ordering
  action) instead of a narrative sentence.
name: concise_lab_value_output
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task8_26
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  update_cycle: 1
tags: []
version: 1
---

# Concise Lab Value Output

## Pattern Description
You must return a minimal, machine‑readable answer when a task asks for the most recent laboratory value (e.g., potassium, magnesium, HbA1c) and optionally an order based on that value. The answer should be a JSON array containing **only** the extracted value with its unit, or a short token indicating that an order was placed. No explanatory text, thresholds, or narrative phrasing is allowed.

## When to Use This Skill
- When the task description includes phrases like "What’s the last … level", "Check patient … potassium level", or "If low then order …".
- After you have performed the required GET request(s) for the Observation resource.
- Before calling `FINISH` you must format the output according to this skill.

## Common Failure Patterns
- `FINISH(["Latest potassium level is 4.7 mmol/L, which is above the 3.5 mmol/L threshold; no replacement ordered."])`
- `FINISH(["Serum magnesium is 2.0 mg/dL, which is not low; no IV magnesium ordered."])`
- Including any explanatory clause, semicolon, or extra wording beyond the raw value or order token.

## Recommended Patterns
**Pattern 1: Extract and return the raw value**
1. From the Observation bundle, take the first entry (most recent).
2. Prefer `valueQuantity.value` and `valueQuantity.unit`. If the observation uses `valueString`, parse the numeric part and unit.
3. Construct a string `"{value} {unit}"` (e.g., `"4.7 mmol/L"`).
4. Call `FINISH(["{value} {unit}"])`.

**CORRECT**: `FINISH(["4.7 mmol/L"])`
**WRONG**: `FINISH(["Potassium level 4.7 mmol/L is above the low threshold."])`

**Pattern 2: Order when value is below threshold**
1. After extracting the numeric value, compare it to the task‑specific low‑threshold (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL).
2. If the value is low, build and POST the appropriate `MedicationRequest` or `ServiceRequest`.
3. After a successful POST, call `FINISH(["order placed"])` (or a more specific token like `"IV magnesium ordered"`).

**CORRECT**: `FINISH(["IV magnesium ordered"])`
**WRONG**: `FINISH(["Serum magnesium 1.2 mg/dL is low; IV magnesium ordered."])`

**Pattern 3: No recent observation**
1. If the Observation search returns `total: 0`, do **not** fabricate a value.
2. Return the placeholder defined by `missing_observation_placeholder` **or** a concise token such as `"no result"`.
3. Example: `FINISH(["no result"])`.

## Example Application
**Task:** "Check patient S3057899's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded, don't order anything."

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S3057899&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Bundle contains an entry with `valueQuantity.value = 2.2` and `valueQuantity.unit = "mg/dL"`.
3. Compare `2.2` to low‑threshold `1.5` → not low.
4. No order is needed.
5. `FINISH(["2.2 mg/dL"])`.

**If the value had been 1.2 mg/dL:**
1‑3 same, value < 1.5 → build `MedicationRequest` for IV magnesium and POST it.
4. After successful POST, `FINISH(["IV magnesium ordered"])`.

## Success Indicators
- The final `FINISH` call contains a JSON array with a single short string: either "{value} {unit}", "order placed", "IV magnesium ordered", or "no result".
- No extra words, commas, or explanatory clauses are present.
- The correct POST (if needed) is performed **before** the `FINISH` call.

## Failure Indicators
- The `FINISH` output includes narrative text, thresholds, or explanations.
- The output mixes the value with additional commentary (e.g., "above the low threshold").
- An order is performed but the `FINISH` still returns the full sentence instead of the concise token.

---

**Tags:** ["lab","output","format","ordering"]
