---
description: Prevents unnecessary potassium replacement orders by enforcing a threshold
  check before ordering.
name: threshold_based_ordering_for_replacement_potassium
provenance:
  action: ADD
  epoch: 1
  fixes: 14
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_16
  - task10_10
  - task9_8
  - task9_27
  - task9_6
  - task9_5
  - task9_20
  - task4_28
  - task10_12
  - task9_11
  update_cycle: 0
tags:
- ordering
- lab
- threshold
- potassium
- safety
- decision-logic
version: 1
---

# Threshold-Based Ordering for Replacement Potassium

## Pattern Description

When a clinical instruction requires ordering potassium replacement only if the patient's most recent potassium level is low, you must enforce a threshold-based decision before placing any order. This prevents unnecessary or potentially harmful medication orders. The agent should always check the latest potassium value and compare it to the defined lower limit (typically 3.5 mmol/L, but always confirm the threshold in the task or protocol). Only if the value is below this threshold should a replacement order be placed.

This pattern is critical for safe, protocol-driven care and applies to any lab-driven conditional ordering, but is especially important for electrolytes like potassium where overcorrection can be dangerous.

## When to Use This Skill

- When the task says "If low, then order replacement potassium" or similar conditional instructions.
- When the agent is asked to check a lab value and only act if it is below a certain threshold.
- When the agent is to pair a replacement order with a follow-up lab, but only if the initial replacement is indicated.

## Common Failure Patterns

- Placing a ServiceRequest for potassium replacement without checking the actual potassium value.
- Placing a replacement order even when the potassium is normal or high.
- Failing to extract the most recent potassium value before making the decision.
- Ignoring the threshold or using the wrong comparison operator (e.g., ordering if value is equal to threshold).

## Recommended Patterns

**Pattern 1: Extract and Compare**
1. Issue a GET /Observation?code=K&patient={id} to retrieve potassium results.
2. Identify the most recent potassium value (use `effectiveDateTime` to sort if needed).
3. Extract the numeric value from `valueQuantity.value`.
4. Compare the value to the defined threshold (e.g., < 3.5 mmol/L).
5. Only proceed to order replacement potassium if the value is below the threshold.

CORRECT: Only POST ServiceRequest if potassium < 3.5
WRONG: POST ServiceRequest regardless of potassium value

**Pattern 2: No Order if Not Indicated**
- If the potassium is normal or high, do not place a replacement order. You may still place a follow-up lab order if the task requires it, but do not order replacement medication.

**Pattern 3: Output Structure**
- Document the potassium value in the answer array if required, but do not include extra text or justification unless the task requests it.

## Example Application

**Task:** "Check patient S1635224's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. GET http://localhost:8080/fhir/Observation?code=K&patient=S1635224
2. Extract the most recent `valueQuantity.value` (e.g., 4.5 mmol/L).
3. Compare 4.5 to threshold 3.5. Since 4.5 >= 3.5, do NOT order replacement potassium.
4. Do NOT POST a ServiceRequest for potassium replacement.
5. If the task requires a follow-up lab regardless, POST only the lab order.
6. FINISH([4.5])

CORRECT output: FINISH([4.5])
WRONG output: POST ServiceRequest for potassium replacement, then FINISH([4.5])

## Success Indicators

- No replacement potassium order is placed when the potassium is normal or high.
- The agent only POSTs a ServiceRequest for replacement if the potassium is below the threshold.
- The answer array contains only the potassium value (if required), with no extra text or unnecessary actions.

## Failure Indicators

- A ServiceRequest for potassium replacement is placed even when the potassium is normal or high.
- The agent ignores the threshold and always places the order.
- The agent fails to extract or compare the potassium value before acting.
