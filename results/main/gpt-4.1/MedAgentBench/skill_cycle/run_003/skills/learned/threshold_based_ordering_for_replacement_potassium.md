---
description: Enforce threshold check and downstream order logic for potassium replacement
  tasks.
name: threshold_based_ordering_for_replacement_potassium
provenance:
  action: MODIFY
  epoch: 3
  fixes: 2
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_5
  - task10_16
  update_cycle: 1
tags:
- lab
- threshold
- potassium
- order
- decision-logic
version: 2
---

# Threshold-Based Ordering for Replacement Potassium

## Pattern Description

When tasked with checking a patient's potassium level and ordering replacement if low, you must actively enforce a threshold check before proceeding to order replacement potassium. The skill applies not only to the extraction of the lab value, but also to the downstream decision logic: if the potassium is below the defined threshold, order replacement; if normal or high, do not order. This prevents unnecessary medication orders and ensures clinical appropriateness.

## When to Use This Skill

- When a task instructs you to check a patient's potassium level and order replacement if low.
- When the task specifies a threshold or dosing instructions for potassium replacement.
- After retrieving the most recent potassium value via GET /Observation.

## Common Failure Patterns

- Returning the potassium value without evaluating against the threshold (e.g., FINISH([4.7]) when the task expects a replacement order if low).
- Failing to trigger the replacement order logic after retrieving a normal potassium value (should explicitly decide not to order).
- Ordering potassium replacement without checking the value against the threshold.
- Not pairing the replacement order with a follow-up lab order when instructed.

## Recommended Patterns

**Pattern 1: Threshold Evaluation and Order Decision**
1. Extract the most recent potassium value from `valueQuantity.value` in the Observation resource.
2. Compare the value to the defined threshold (e.g., <3.5 mEq/L is considered low).
3. If potassium is low, proceed to order replacement potassium per dosing instructions.
4. If potassium is normal or high, do not order replacement; simply return the value.

CORRECT: If potassium = 3.1, order replacement and pair with follow-up lab.
WRONG: If potassium = 4.7, order replacement or fail to state no order is needed.

**Pattern 2: Pairing with Follow-Up Lab Order**
1. If replacement is ordered, also create a ServiceRequest for a follow-up serum potassium lab at the specified time (e.g., next day at 8am).
2. Include `occurrenceDateTime` and a note in the ServiceRequest as instructed.

**Pattern 3: Output Formatting**
- If no replacement is needed, output only the potassium value in the answer array.
- If replacement is ordered, output the potassium value and confirm both orders were placed.

## Example Application

**Task:** "Check patient S1796597's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Issue GET /Observation?code=K&patient=S1796597
2. Extract `valueQuantity.value` from the most recent entry (e.g., 4.7)
3. Compare to threshold (e.g., 3.5)
4. If value >= threshold, do NOT order replacement. Output: FINISH([4.7])
5. If value < threshold, POST MedicationRequest for potassium replacement, then POST ServiceRequest for follow-up lab, then output: FINISH([3.1])

CORRECT output: FINISH([4.7]) (no order if value is normal)
WRONG output: FINISH([4.7]) without evaluating threshold or ordering when not needed

## Success Indicators

- Agent explicitly checks potassium value against threshold before deciding to order.
- No replacement order is placed if potassium is normal or high.
- Both MedicationRequest and ServiceRequest are placed if potassium is low and task requires pairing.
- Final output reflects the correct decision logic.

## Failure Indicators

- Agent returns potassium value without evaluating threshold or making an explicit order/no-order decision.
- Replacement order is placed for normal potassium values.
- Agent fails to pair replacement order with follow-up lab when instructed.
- Output does not reflect the correct clinical decision.
