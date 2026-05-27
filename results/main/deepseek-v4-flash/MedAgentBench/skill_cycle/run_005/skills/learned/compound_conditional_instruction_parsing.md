---
description: Parse compound instructions where 'also' clauses are conditional on the
  preceding condition being met
name: compound_conditional_instruction_parsing
provenance:
  action: ADD
  epoch: 4
  fixes: 4
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - task10_21
  - task1_12
  - task10_12
  - task5_16
  - task10_27
  - task5_7
  - task5_3
  - task10_15
  - task10_13
  - task9_3
  update_cycle: 1
tags: []
version: 1
---

# Compound Conditional Instruction Parsing

## Pattern Description

When a task contains a conditional instruction ("If X, then do Y") followed by an "also" clause ("Also do Z"), the "also" clause is typically dependent on the condition being met, not an unconditional action. The word "also" refers to doing Z in addition to Y, but only when the condition X is true. You must carefully parse the logical structure of compound instructions to determine whether each action is conditional or unconditional.

- The key insight: "Also pair this order with..." means "in addition to ordering the replacement, also order the follow-up lab" — both actions are conditional on the lab value being low.
- Do not treat "also" as introducing an unconditional action unless the task explicitly separates it with a period or new sentence that makes it independent.
- When in doubt, re-read the task and identify which actions are inside the "if" block and which are outside.

## When to Use This Skill

- When a task says "If [condition], then [action A]. Also [action B]" — the "also" clause is conditional on the same condition.
- When a task says "If [condition], then [action A]. Also pair this order with [action B]" — both A and B are conditional.
- When a task says "If [condition], then [action A]. [Unrelated action C]." — action C may be unconditional if it's a separate sentence not linked by "also".
- When a task has multiple sentences and you need to determine which actions are conditional vs unconditional.

## Common Failure Patterns

- Treating "Also pair this order with a morning serum potassium level" as unconditional when the potassium is not low
- Ordering follow-up labs when no replacement was needed because the condition was not met
- Adding extra commentary about why an action was or wasn't taken instead of just executing the correct logic
- Misinterpreting "also" as a separate unconditional instruction rather than an additional conditional action

## Recommended Patterns

**Pattern 1: Parse the conditional structure**
1. Identify the condition (e.g., "If low", "If the lab value result date is greater than 1 year old").
2. Identify the primary action inside the condition (e.g., "order replacement IV magnesium").
3. Look for "also" or "in addition" clauses — these are part of the same conditional block.
4. Only execute actions inside the conditional block if the condition is true.
5. Only execute actions outside the conditional block unconditionally.

**Pattern 2: Verify conditional scope**
- If the task says "If [condition], then [action A]. Also [action B]." → both A and B are conditional.
- If the task says "If [condition], then [action A]. [action B]." without "also" → action B may be unconditional.
- If the task says "[action A]. If [condition], then [action B]." → action A is unconditional, action B is conditional.

**Pattern 3: Output formatting**
- When the condition is not met, output only the required answer without extra commentary.
- Do not include explanations like "no replacement needed" unless the task explicitly asks for that.
- Do not perform actions that were conditional on a condition that was not met.

## Example Application

**Task:** "Check patient S1635224's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Parse the task structure:
   - Condition: potassium is low (below 3.5 mmol/L)
   - Primary action (conditional): order replacement potassium
   - "Also" clause (conditional): pair this order with a morning serum potassium level
   - Both actions are inside the conditional block

2. GET the potassium level: `GET /fhir/Observation?code=K&patient=S1635224`
   - Response: most recent potassium is 4.5 mmol/L

3. Check condition: 4.5 is NOT low (above 3.5), so the condition is not met.

4. Since condition is not met, do NOT execute either action:
   - Do NOT order replacement potassium
   - Do NOT order morning serum potassium level (because "also" is conditional)

CORRECT output: `FINISH([4.5])` or whatever the task expects
WRONG output: Ordering a morning lab when no replacement was needed

## Success Indicators

- When the condition is not met, no conditional actions (including "also" clauses) are executed
- The agent correctly identifies which actions are inside vs outside the conditional block
- The agent does not add extra commentary about why actions were skipped

## Failure Indicators

- Ordering a follow-up lab when the primary condition was not met
- Treating "also" as introducing an unconditional action
- Adding explanatory text like "no replacement needed" when the task only expects the value
- Performing actions that were clearly conditional on a condition that evaluated to false

## Guard Clause

This skill ONLY applies when the task contains BOTH:
1. A conditional statement using "if" (e.g., "If [condition], then [action]")
2. An "also" clause that is part of the same sentence or directly follows the conditional statement

This skill does NOT apply to simple lookup tasks (e.g., "What's the MRN of patient X?") or tasks where the only conditional is about existence of a record (e.g., "If the patient does not exist, answer 'Patient not found'"). In those cases, follow the standard logic without applying this skill.
