---
description: Correctly interpret lab thresholds and order follow-up labs when replacement
  is needed or when task explicitly requires follow-up
name: lab_value_threshold_interpretation_and_conditional_ordering
provenance:
  action: MODIFY
  epoch: 2
  fixes: 2
  parent_version: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task5_19
  - task5_3
  - task10_10
  - task10_12
  - task10_13
  - task9_1
  - task9_20
  - task3_19
  update_cycle: 1
tags: []
version: 2
---

# Lab Value Threshold Interpretation and Conditional Ordering

## Pattern Description

This skill teaches you to correctly interpret lab values against thresholds and take appropriate action: order replacement when low, or order follow-up monitoring labs when the task explicitly requires them even if replacement is not needed. The key insight is that a task may have two independent requirements: (1) conditionally order replacement based on lab value, and (2) unconditionally order a follow-up lab regardless of the value.

When a task says "Also pair this order with a morning serum potassium level" or similar language, the follow-up lab must be ordered regardless of whether the value is low enough to warrant replacement. The follow-up lab is a monitoring requirement, not a conditional action tied to the replacement decision.

## When to Use This Skill

- When checking a lab value (potassium, magnesium, etc.) to decide if replacement is needed
- When the task includes language like "Also pair this order with..." or "Also order a follow-up..." indicating an additional required action
- When the task specifies a follow-up lab to be completed at a specific time (e.g., "next day at 8am")
- When interpreting thresholds from dosing instructions rather than assuming a single hardcoded threshold

## Common Failure Patterns

- Skipping the follow-up lab order entirely when the value is not low, because the agent treats the follow-up as conditional on replacement being ordered
- Using a hardcoded threshold (e.g., 3.5 for potassium) when the dosing instructions define a different threshold or range
- Not checking the dosing instructions for the exact threshold definition (e.g., mild deficiency defined as 1.5-1.9 mg/dL for magnesium)
- Forgetting to include the `date` parameter in the GET request to filter by the last 24 hours when the task specifies a time window

## Recommended Patterns

**Pattern 1: Parse the task for independent requirements**
Read the task carefully and identify all required actions. Separate conditional actions ("If low, then order replacement") from unconditional actions ("Also pair this order with a morning serum potassium level"). The unconditional action must be performed regardless of the lab value.

**Pattern 2: Check dosing instructions for exact thresholds**
When the task says "according to dosing instructions", you must examine the dosing instructions to find the exact threshold or range. Do not assume a single hardcoded threshold like 3.5 for potassium or 1.9 for magnesium.

CORRECT: Check dosing instructions for threshold (e.g., "mild deficiency: 1.5-1.9 mg/dL" means low is < 1.5 or < 1.9 depending on context)
WRONG: Assume threshold is 3.5 for potassium without checking dosing instructions

**Pattern 3: Order follow-up labs unconditionally when required**
If the task says "Also pair this order with a morning serum potassium level to be completed the next day at 8am", you must:
1. Check the potassium level
2. If low, order replacement AND order the follow-up morning lab
3. If NOT low, still order the follow-up morning lab (do not skip it)

**Pattern 4: Use the `date` parameter for time-windowed queries**
When the task specifies a time window (e.g., "within last 24 hours"), include the `date` parameter in the GET request to filter results server-side.

CORRECT: `GET /Observation?code=MG&patient=S123&date=ge2023-11-12T10:15:00Z`
WRONG: `GET /Observation?code=MG&patient=S123` (no date filter, then manually checking dates)

## Example Application

**Task:** "Check patient S6550473's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Issue GET with exact parameters: `GET /Observation?code=K&patient=S6550473`
2. Extract the most recent potassium value from `valueQuantity.value` (e.g., 4.6 mmol/L)
3. Check the dosing instructions for the threshold (e.g., threshold is 3.5 mmol/L)
4. Since 4.6 > 3.5, no replacement is needed
5. However, the task says "Also pair this order with a morning serum potassium level" — this is an unconditional requirement
6. Order the follow-up morning serum potassium lab for the next day at 8am (2023-11-14T08:00:00+00:00)

CORRECT output: `FINISH(["No replacement needed, potassium level is 4.6 mmol/L (above threshold of 3.5). Ordered morning serum potassium level for 2023-11-14 at 8am."])`
WRONG output: `FINISH(["No replacement needed, potassium level is 4.6 mmol/L (above threshold of 3.5)"])` (missing the follow-up lab order)

## Success Indicators

- When the task includes an unconditional follow-up lab requirement, the agent orders it even when replacement is not needed
- The agent checks dosing instructions for exact thresholds rather than assuming hardcoded values
- The agent uses the `date` parameter for time-windowed queries
- The agent correctly separates conditional and unconditional task requirements

## Failure Indicators

- The agent skips ordering a follow-up lab that the task explicitly requires, because the value was not low
- The agent uses a hardcoded threshold (e.g., 3.5) when dosing instructions define a different threshold
- The agent does not include the `date` parameter in the GET request when the task specifies a time window
- The agent returns a text description instead of the requested numeric value format
