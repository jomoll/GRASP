---
description: When a task says 'check if low' or 'if low then order', compare the value
  against the threshold and act accordingly
name: conditional_lab_value_decision
provenance:
  action: MODIFY
  epoch: 4
  fixes: 4
  parent_version: 2
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_14
  - task9_6
  - task5_17
  - task10_24
  - task9_11
  - task10_20
  - task9_20
  - task10_10
  - task10_16
  - task9_22
  update_cycle: 0
tags:
- conditional_logic
- lab_value
- threshold_comparison
- task_parsing
version: 3
---

# Conditional Lab Value Decision

## Pattern Description

This skill governs how you handle tasks that require checking a lab value against a threshold and conditionally taking action. The central lesson is: you must parse the task instruction carefully to identify which actions are truly conditional on the threshold comparison and which actions are unconditional instructions that must be executed regardless of the comparison result.

When a task says "If low, then order X. Also do Y," the word "also" signals that Y is an independent instruction, not a sub-step of the conditional branch. You must execute Y regardless of whether the condition was met. Similarly, when a task says "Pair this order with a morning lab," the pairing instruction applies only if the conditional order is placed — but if the task separately says "Also order a morning lab" or "Order a morning lab regardless," that is an unconditional action.

## When to Use This Skill

- When a task says "check if [lab] is low" or "if low then order [medication]"
- When a task includes both a conditional action and an unconditional follow-up action (e.g., "Also pair this order with..." or "Also order a morning lab")
- When a task says "If low, then order X. Also do Y" — the "also" clause is typically unconditional
- When constructing a MedicationRequest or ServiceRequest based on a threshold comparison

## Common Failure Patterns

- Skipping an unconditional follow-up lab order because the conditional replacement was not needed
- Misinterpreting "Also pair this order with a morning lab" as meaning the morning lab is only ordered if the replacement is ordered
- Treating all instructions after "If low" as conditional, when some are independent clauses
- Failing to distinguish between "pair this order" (conditional on the order existing) vs "also order" (unconditional)

## Recommended Patterns

**Pattern 1: Parse the task into conditional vs unconditional actions**
Read the full task instruction. Identify which actions are prefixed by "if" or "if low" — those are conditional. Identify which actions are introduced by "also", "additionally", "regardless", or are standalone sentences — those are unconditional.

**Pattern 2: Execute the conditional branch**
1. Fetch the most recent lab value using the correct code and patient identifier
2. Compare the numeric value against the threshold (typically 3.5 for potassium, 1.8 for magnesium)
3. If below threshold: execute the conditional action (e.g., order replacement medication)
4. If at or above threshold: do NOT execute the conditional action

**Pattern 3: Execute unconditional actions regardless**
After handling the conditional branch, check if there are any unconditional actions in the task. If the task says "Also order a morning serum potassium level to be completed the next day at 8am," you must order that lab even if no replacement was needed. The word "also" means "in addition to whatever else happens."

CORRECT: Potassium is 4.0 (not low) → no replacement ordered → but still order the morning lab as instructed
WRONG:   Potassium is 4.0 (not low) → no replacement ordered → skip the morning lab because "this order" refers to the replacement

**Pattern 4: Distinguish "pair this order" from "also order"**
- "Pair this order with a morning lab" = the morning lab is paired with the replacement order; if no replacement order exists, no pairing is needed
- "Also order a morning lab" or "Also pair this order with a morning serum potassium level" = the morning lab is an independent instruction; order it regardless

## Example Application

**Task:** "Check patient S6550473's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Parse the task: 
   - Conditional: "If low, then order replacement potassium"
   - Unconditional: "Also pair this order with a morning serum potassium level" — the word "also" makes this an independent instruction

2. Fetch potassium: GET /fhir/Observation?code=K&patient=S6550473
   → Most recent value: 4.3 mmol/L (above threshold of 3.5)

3. Conditional branch: value is 4.3, not below 3.5 → do NOT order replacement potassium

4. Unconditional action: The task says "Also pair this order with a morning serum potassium level to be completed the next day at 8am." Since this is an unconditional instruction, you must still order the morning lab even though no replacement was ordered.

5. Order the morning lab: POST /fhir/ServiceRequest with appropriate code for serum potassium, scheduled for next day at 8am

CORRECT output: `FINISH(["No replacement needed", "Ordered morning serum potassium level for 2023-11-14T08:00:00"])`
WRONG output:   `FINISH(["No replacement needed"])` — missing the unconditional morning lab order

## Success Indicators

- When the lab value is below threshold, both the replacement medication AND any unconditional follow-up actions are executed
- When the lab value is at or above threshold, the replacement is skipped but unconditional follow-up actions (like morning labs) are still executed
- The agent correctly distinguishes between "pair this order" (conditional on the order existing) and "also order" (unconditional)

## Failure Indicators

- The agent skips ordering a morning lab when the potassium is not low, even though the task said "Also..."
- The agent fails to order a morning lab when the task explicitly says to order it regardless of the threshold result
- The agent treats all post-condition instructions as conditional, missing independent clauses introduced by "also" or "additionally"
