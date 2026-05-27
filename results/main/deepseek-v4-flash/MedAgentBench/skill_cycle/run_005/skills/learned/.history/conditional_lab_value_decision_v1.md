---
description: When a task says 'check if low' or 'if low then order', compare the value
  against the threshold and act accordingly
name: conditional_lab_value_decision
provenance:
  action: ADD
  epoch: 2
  fixes: 3
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task10_21
  - task10_13
  - task10_15
  - task1_20
  - task9_22
  - task10_20
  - task1_6
  - task9_6
  - task5_16
  - task9_20
  update_cycle: 1
tags:
- conditional_decision
- lab_value_threshold
- clinical_action
version: 1
---

# Conditional Lab Value Decision

## Pattern Description

When a task instructs you to check a lab value and then conditionally take an action (e.g., "if low, then order replacement"), you must not simply return the lab value. You must evaluate the value against the relevant clinical threshold, make a decision, and then either take the action or explicitly state no action is needed. The final output should reflect the decision made, not just the raw measurement.

This skill applies to any task where the instruction contains a conditional clause like "if low", "if high", "if abnormal", or "if within range" followed by an action to take or not take. The core lesson is: after extracting the numeric value, you must compare it to the threshold and produce the appropriate output based on that comparison.

## When to Use This Skill

- When the task says "Check patient X's last [lab] level... If low, then order replacement..."
- When the task says "If no [lab] level has been recorded, don't order anything"
- When the task contains a conditional action based on a lab value being above or below a threshold
- When the task expects you to either take an action (order medication, create referral) or explicitly do nothing based on a comparison

## Common Failure Patterns

- Returning the lab value as the final answer (e.g., `FINISH([2.0])`) when the task asked you to conditionally order something
- Describing the value and your reasoning in natural language but not taking the required action or producing the correct output format
- Forgetting to check whether a value is low before deciding to order or not order
- Not handling the "no measurement found" case correctly (should return -1 or do nothing, not try to order)

## Recommended Patterns

**Pattern 1: Extract and compare**
1. Retrieve the most recent lab value using the correct FHIR search (code, patient, date range).
2. Extract the numeric value from `valueQuantity.value`.
3. Compare the value against the relevant clinical threshold (e.g., magnesium low is < 1.5 mg/dL, potassium low is < 3.5 mEq/L).
4. If the value is below the threshold, proceed to order the replacement according to the dosing instructions.
5. If the value is at or above the threshold, do not order anything — output that no action is needed.
6. If no measurement is found (empty bundle), do not order anything — output -1 or that no action is needed.

**Pattern 2: Format the final output correctly**
- If you order a replacement, the output should confirm the order was placed (e.g., `FINISH(["IV magnesium ordered"])`).
- If no action is needed because the value is normal, output that no replacement is needed (e.g., `FINISH(["No replacement needed"])`).
- If no measurement was found, output -1 (e.g., `FINISH([-1])`).
- Never output just the raw lab value as the final answer when the task asked for a conditional action.

**Pattern 3: Use the correct threshold**
- For magnesium: low is typically < 1.5 mg/dL (mild deficiency 1.5-1.9, moderate 1.0-1.4, severe < 1.0).
- For potassium: low is typically < 3.5 mEq/L.
- Always check the task context for specific threshold definitions if provided.

## Example Application

**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET with exact parameters: `GET /fhir/Observation?code=MG&patient=S1023381&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Extract the numeric value from the response: `valueQuantity.value` = 2.0
3. Compare against threshold: 2.0 mg/dL is not low (normal range is 1.5-2.5 mg/dL, low is < 1.5).
4. Since the value is not low, do not order replacement.
5. Output the decision: `FINISH(["No replacement needed"])`

CORRECT output: `FINISH(["No replacement needed"])`
WRONG output:   `FINISH([2.0])`

## Success Indicators

- The agent retrieves the lab value, compares it to the threshold, and either orders the replacement or explicitly states no action is needed.
- The final output reflects the decision (order confirmation or "no replacement needed"), not just the raw value.
- When no measurement is found, the agent outputs -1 or states no action is needed.

## Failure Indicators

- The agent returns the raw lab value as the final answer (e.g., `FINISH([2.0])`) when the task asked for a conditional action.
- The agent describes the value and reasoning but does not produce the correct final output format.
- The agent orders replacement when the value is normal, or fails to order when the value is low.
- The agent tries to order replacement when no measurement was found.
