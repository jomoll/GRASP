---
description: Correctly interpret lab thresholds and order follow-up labs when replacement
  is needed
name: lab_value_threshold_interpretation_and_conditional_ordering
provenance:
  action: ADD
  epoch: 2
  fixes: 2
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_20
  - task10_27
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task2_6
  - task5_16
  - task9_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Lab Value Threshold Interpretation and Conditional Ordering

## Pattern Description

When a task requires checking a lab value against a threshold and conditionally ordering a replacement, you must correctly interpret the threshold comparison and ensure all required follow-up actions are performed. The threshold is inclusive - a value equal to the threshold is considered low and requires replacement. Additionally, when a replacement is ordered, you must also order any paired follow-up lab as specified in the task.

This skill covers the decision logic for threshold-based replacement ordering, including the correct interpretation of comparison operators and the complete set of actions required when replacement is triggered.

## When to Use This Skill

- When a task says "If low, then order replacement" and provides a threshold value
- When a task requires pairing a replacement order with a follow-up lab (e.g., "pair this order with a morning serum potassium level")
- When evaluating lab values against numeric thresholds for clinical decision-making
- When the task specifies both a conditional action and a mandatory paired action

## Common Failure Patterns

- Treating a value equal to the threshold as "not low" - e.g., threshold of 3.5 and value of 3.5 should trigger replacement
- Ordering replacement but forgetting to order the paired follow-up lab
- Using strict greater-than instead of greater-than-or-equal for normal range checks
- Skipping the follow-up lab entirely when replacement is not needed (correct behavior depends on task wording)

## Recommended Patterns

**Pattern 1: Threshold comparison**
When the task says "If low" with a threshold value, treat values <= threshold as low. Use `valueQuantity.value <= threshold` for the comparison.

CORRECT: threshold=3.5, value=3.5 → low (replace)
WRONG:   threshold=3.5, value=3.5 → not low (skip)

**Pattern 2: Complete action set when replacement is triggered**
When replacement is ordered AND the task specifies a paired follow-up lab, you must order BOTH:
1. The replacement medication (as a MedicationRequest)
2. The follow-up lab (as a ServiceRequest with the specified timing)

Do not stop after ordering the replacement - check the task for any additional required orders.

**Pattern 3: When replacement is not needed**
If the value is above the threshold (strictly greater), no replacement is needed. Check the task wording carefully - some tasks still require ordering the follow-up lab even without replacement, while others say "no further orders are required."

## Example Application

**Task:** "Check patient S1311412's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Query the most recent potassium: `GET /fhir/Observation?code=K&patient=S1311412`
2. Extract the value: `valueQuantity.value` = 3.5, threshold = 3.5
3. Apply comparison: 3.5 <= 3.5 → low → replacement needed
4. Order replacement potassium as a MedicationRequest with the NDC code from context
5. Order follow-up lab: POST a ServiceRequest for potassium with `occurrenceDateTime` set to next day at 8am

CORRECT output: FINISH(["Replacement potassium ordered", "Morning potassium lab ordered for next day at 8am"])
WRONG output:   FINISH([]) or FINISH(["No replacement needed, value equals threshold"])

## Success Indicators

- When value equals threshold, agent orders replacement and any paired follow-up lab
- Agent correctly uses <= for low threshold comparison
- Both replacement and follow-up lab are ordered when task specifies both
- Agent checks task wording to determine if follow-up lab is needed even without replacement

## Failure Indicators

- Agent says "value equals threshold, so not low" and skips replacement
- Agent orders replacement but forgets the paired follow-up lab
- Agent uses strict < instead of <= for threshold comparison
- Agent orders follow-up lab but not the replacement when value is below threshold
