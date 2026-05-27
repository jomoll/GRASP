---
description: Ensure lab value extraction returns both numeric value and its unit for
  correct threshold checks
name: include_quantity_unit
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task8_19
  - task9_22
  - task9_1
  - task4_28
  - task9_5
  - task9_9
  - task10_10
  - task5_3
  - task9_8
  update_cycle: 1
tags: []
version: 1
---

# include_quantity_unit

## Pattern Description
You must always extract a laboratory Observation's numeric result **and** its unit before any decision logic.  Many tasks compare the value against a clinical threshold that is defined in a specific unit (e.g., mg/dL for magnesium).  If the unit is omitted the comparison can be wrong, leading to missed orders or false alerts.

## When to Use This Skill
- When a task asks for the *most recent* value of a lab (e.g., magnesium, potassium, HbA1c) and the decision depends on a numeric threshold.
- When the task explicitly mentions a unit conversion (e.g., "convert to mg/dL") or when the expected answer format includes a unit.
- When the Observation resource contains a `valueQuantity` element.

## Common Failure Patterns
- Returning only `valueQuantity.value` and omitting `valueQuantity.unit`.
- Using the timestamp field as a second element in the FINISH array, thereby losing the unit.
- Encountering an Observation where `valueQuantity.unit` is missing; the agent then has no fallback and cannot apply the threshold.

## Recommended Patterns
**Pattern 1: Primary extraction**
1. Locate the first entry in the Bundle that matches the requested `code` and falls within any date filter.
2. From that entry read:
   - `valueQuantity.value` → numeric value `V`
   - `valueQuantity.unit`   → string unit `U`
3. If `U` is present, keep it.
4. If `U` is missing, map the observation `code` to a default unit (e.g., `MG` → `mg/dL`, `K` → `mmol/L`, `A1C` → `%`).
5. Store the pair as `(V, U)` for later comparison.

**Pattern 2: Unit normalization / conversion**
- If the task requires a specific unit different from `U`, apply a conversion table:
  - `mmol/L` → `mg/dL` for magnesium: `V_mg/dL = V_mmol/L * 2.0`
  - `mmol/L` → `mg/dL` for potassium: `V_mg/dL = V_mmol/L * 39.1`
- After conversion, replace `U` with the target unit.

**Pattern 3: FINISH formatting**
- When the task expects a simple numeric answer, return `FINISH([V])` **after** you have verified the unit matches the required one.
- When the task expects the value **and** the unit (or timestamp), return `FINISH([V, "U", "timestamp"])` preserving the order: value, unit, timestamp.

## Example Application
**Task:** "Check patient S0636132's last serum magnesium level within last 24 hours. If low (<1.5 mg/dL) order replacement."

**Step‑by‑step:**
1. `GET http://.../Observation?code=MG&patient=S0636132&date=ge2023-11-12T10:15:00Z`
2. From the first entry extract `valueQuantity.value = 2.0` and `valueQuantity.unit = "mg/dL"`.
3. Verify the unit is `mg/dL`. (If it were `mmol/L`, convert: `2.0 mmol/L * 2.0 = 4.0 mg/dL`).
4. Compare `2.0` to the low‑threshold `1.5` → not low, so **no order**.
5. Return `FINISH([2.0, "mg/dL", "2023-11-13T00:36:00+00:00"])`.

**CORRECT:** `valueQuantity.value` extracted as a number and `valueQuantity.unit` kept.
**WRONG:** `FINISH([2.0, "2023-11-13T00:36:00+00:00"])` – unit omitted.

## Success Indicators
- The FINISH array contains the unit string in the expected position.
- Threshold comparisons use the correct unit (no unit‑mismatch errors).
- No task that requires a unit fails with a “quantity_unit_missing” error.

## Failure Indicators
- FINISH output lacks a unit when the task description mentions a unit or a threshold.
- The agent compares a value against a threshold expressed in a different unit (e.g., compares mg/dL threshold to a value reported in mmol/L).
- The agent falls back to `-1` or placeholder because it could not find a unit.
