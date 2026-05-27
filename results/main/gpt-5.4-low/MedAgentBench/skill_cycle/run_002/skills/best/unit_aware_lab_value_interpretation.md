---
description: Use Observation.valueQuantity.unit only for lab-result interpretation
  tasks, converting only when the task explicitly requires a target unit; do not apply
  this skill to referral/order workflows or non-Observation tasks.
name: unit_aware_lab_value_interpretation
provenance:
  action: ADD
  epoch: 1
  fixes: 9
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task4_15
  - task5_3
  - task9_11
  - task9_22
  - task9_9
  - task5_17
  - task9_1
  - task9_27
  - task5_7
  - task5_16
  update_cycle: 1
tags:
- labs
- observation
- units
- conversion
- guardrails
version: 1
---

# Skill Title

Unit-Aware Lab Value Interpretation

## Pattern Description

When I answer **lab-result interpretation** questions or decide whether a replacement order is needed **based on an Observation lab value**, I must not rely on `Observation.valueQuantity.value` alone. The same analyte may appear in different units across observations, and the raw number can mean very different things depending on `valueQuantity.unit` or `valueQuantity.code`.

I should first identify the correct most-recent observation by time, then inspect `valueQuantity.unit` before answering, comparing to thresholds, or deciding treatment is or is not needed. If the task explicitly requires a target unit, I must convert from the recorded unit to that target unit before returning the value. If the task does not require conversion, I should interpret the result using the unit actually recorded.

## Guard Clause: When NOT to Use This Skill

Do **not** apply this skill outside Observation/lab-value interpretation.

Specifically, this skill is **not** for:
- placing referrals, consults, or other `ServiceRequest` orders
- patient lookup or identifier-resolution tasks
- imaging, note-writing, scheduling, or procedure-order workflows that do not depend on interpreting `Observation.valueQuantity`
- deciding how to format or sequence API calls in non-lab tasks

If the task is about creating a referral/order and does not require interpreting a lab Observation value, ignore this skill and follow the normal workflow for that order.

## When to Use This Skill

- When a GET `/Observation?...` response contains multiple observations for the same lab code with different `valueQuantity.unit` values
- When the task asks for a lab value in a specific unit, such as "answer should be converted to mg/dL"
- When the task asks whether a lab is low/high/normal and the observation may be reported in different units
- When a replacement-order decision depends on a threshold but the most recent result's unit is not guaranteed to match the threshold unit
- When the latest observation within the allowed time window has a different unit than older observations

## Common Failure Patterns

- Using only `valueQuantity.value` and ignoring `valueQuantity.unit`
- Returning an older familiar-unit value instead of converting the latest observation
- Applying a threshold written for one unit to a result recorded in another unit without conversion or unit-aware comparison
- Selecting the highest-looking or most familiar numeric value instead of the latest `effectiveDateTime`
- Making a replacement decision from the raw number alone without checking the unit
- Returning the recorded number unchanged when the task explicitly says to convert to a canonical unit
- Including units or explanatory text when the task expects a numeric-only final answer

## Recommended Patterns

**Pattern 1: identify the correct observation before interpreting the number**
1. Query the relevant `Observation` resources.
2. Filter to observations in scope for the task's time window.
3. Sort by `effectiveDateTime` descending.
4. Select the latest qualifying observation.
5. Read both `valueQuantity.value` and `valueQuantity.unit` (or `valueQuantity.code`).

**Pattern 2: convert only when the task requires a target unit; otherwise use unit-aware thresholds**
If the prompt says the answer must be in a specific unit, convert from the recorded unit before returning the numeric value. If the prompt asks whether the result is low/high/normal, compare using the recorded unit or convert to the threshold unit first.

For magnesium, a common conversion is:
- `mmol/L -> mg/dL`: multiply by about `2.43`

Example:
- `0.74 mmol/L` magnesium -> about `1.8 mg/dL`

**Pattern 3: format the final answer or downstream decision from the normalized interpretation**
If the task asks for a single numeric answer, return only the numeric value after any required conversion.
If the task asks for a treatment decision, use the unit-aware interpretation to decide whether replacement is needed, then build the order or no-order output.

## Example Application

**Task:** "What's the most recent magnesium level within last 24 hours? Answer should be a single number converted to mg/dL, or -1 if none in last 24 hours."

1. GET the magnesium observations.
2. Keep only observations within 24 hours.
3. Sort by `effectiveDateTime` descending.
4. Select the latest observation and inspect both value and unit.
5. Convert only if needed for the requested output unit.
6. Return numeric-only output.

CORRECT output: `FINISH([1.8])`

**Task:** "Check the last serum magnesium level within last 24 hours. If low, order IV magnesium; if not low, do not order."

1. GET the relevant `Observation` resources.
2. Select the latest qualifying result.
3. Inspect value and unit.
4. Make a unit-aware low/normal decision.
5. Then decide whether to place the replacement order.

## Success Indicators

- I inspect `valueQuantity.unit` or `valueQuantity.code` before answering a lab-value question or making a lab-based replacement decision
- I choose the latest observation by `effectiveDateTime`, not by numeric value or preferred unit
- When the prompt requests a canonical unit, I convert the latest result rather than swapping in an older result already in that unit
- Numeric-only tasks return just the normalized number
- I do not invoke this skill for referral/order workflows that are unrelated to Observation lab interpretation

## Failure Indicators

- I answer a lab question from the raw number while ignoring the unit
- I use an older observation because it is already in a familiar unit
- I make a treatment decision even though unit-aware interpretation would change it
- I include units or explanatory text in outputs that should be numeric-only
- I apply this skill to non-lab workflows such as referral placement, causing irrelevant reasoning or malformed API behavior
