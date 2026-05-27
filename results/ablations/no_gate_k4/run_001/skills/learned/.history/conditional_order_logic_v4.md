---
description: "Restrict low\u2011threshold ordering to potassium and magnesium only,\
  \ preventing misuse on unrelated labs"
name: conditional_order_logic
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 3
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_16
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags: []
version: 4
---

# Conditional Order Logic (Refined)

## Pattern Description
This skill governs automatic ordering **only** for electrolyte replacement when the latest serum level is below a defined low‑threshold. It must not be applied to any other laboratory test (e.g., HbA1c, lipid panels) or to decisions based on result staleness.

## When to Use This Skill
- Task explicitly mentions *potassium* (`K`) or *magnesium* (`MG`) replacement.
- The task provides a low‑threshold value (e.g., K < 3.5 mmol/L, Mg < 1.5 mg/dL).
- No other ordering criteria (such as result age) are part of the instruction.

## Common Failure Patterns
- The skill is triggered for unrelated labs (e.g., HbA1c) because the agent sees a generic "order" keyword.
- The agent orders replacement even when the result is within normal range.
- The skill is applied without first confirming the lab code matches K or MG.

## Recommended Patterns
**Pattern 1: Verify Lab Code**
1. After extracting the Observation, check `code.coding[0].code`:
   - `K` for potassium, `MG` for magnesium.
2. If the code is anything else, **exit** this skill and let other skills handle the task.

**Pattern 2: Low‑Threshold Check**
1. Parse `valueQuantity.value` as a number.
2. Compare against the low‑threshold defined in the task (or default thresholds: K < 3.5, Mg < 1.5).
3. Only if the value is **below** the threshold, proceed to **Pattern 3**.

**Pattern 3: Create Replacement ServiceRequest**
- Build a `ServiceRequest` for the appropriate replacement medication (e.g., potassium chloride, IV magnesium sulfate) using the NDC or medication code supplied in the task.
- POST the request and confirm success before `FINISH`.

## Example Application
**Task:** "Check patient S2402518's last serum magnesium level within last 24 h. If low, order IV magnesium replacement."
1. `GET ...code=MG...`
2. Extract `valueQuantity.value = 1.2` (mg/dL).
3. Verify code = `MG` → proceed.
4. Compare 1.2 < 1.5 → low, so POST a `ServiceRequest` for magnesium replacement.
5. `FINISH([1.2])`.

If the task were about HbA1c, step 1 would find code `A1C`, the skill would **exit** without ordering.

## Success Indicators
- The skill runs only when the Observation code is `K` or `MG`.
- An order is placed **only** when the numeric value is below the defined low‑threshold.
- No orders are created for other lab codes.

## Failure Indicators
- A `ServiceRequest` is posted for a non‑electrolyte lab (e.g., HbA1c).
- The agent orders replacement despite the value being normal or above the threshold.
