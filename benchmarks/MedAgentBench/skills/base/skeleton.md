---
name: skeleton
description: Template and quality standard for learned skills — read-only
tags: []
---

# Skill Title

Use a title that names a reusable capability, pattern, or strategy.
Prefer broad titles like `FHIR Search Fallback Strategy` or
`Observation Value Extraction` over titles that only name one specific task
object, unless the rule is truly unique to that object.

## Pattern Description

Write 1–3 paragraphs. State the central reusable lesson. Describe the general
capability first, then anchor it with the type of behavior it should change.

- Keep the opening general and reusable.
- Do not front-load the skill with one specific substance, lab, or task unless
  the rule is genuinely unique to that case.
- Focus on a stable pattern, not one isolated benchmark case.

## When to Use This Skill

Bullet list of task types and trigger conditions where this skill applies.
Be specific about when the agent should actively recall this skill — name the
observable situation, not just the abstract category.

- Example: "When a GET /Observation returns empty entry array but the task
  expects a value"
- Example: "When constructing a MedicationRequest and the task specifies an NDC
  code"

## Common Failure Patterns

Bullet list. Be specific — reference exact API parameters, field names, resource
fields, or output formats when that is the real source of failure.

- Example: `effectiveDateTime` vs `issued` — wrong field causes stale value
- Example: returning `["3.5 mmol/L"]` instead of `[3.5]` — units in value
- Cover both obvious failures and subtle regressions

## Recommended Patterns

Step-by-step operational guidance. Name exact fields or parameters to inspect.
Include concrete correct/wrong examples where helpful.

**Pattern 1: core strategy or rule**
Describe what to do, in order. Name the exact fields or parameters.

CORRECT: `valueQuantity.value` extracted as a number
WRONG:   `valueQuantity.value` concatenated with `valueQuantity.unit`

**Pattern 2: fallback or verification rule**
What to do when the primary strategy fails or returns no results.

**Pattern 3: formatting or completion rule**
How to structure the final output or POST body.

## Example Application

At least one worked example with explicit steps. Show the actual query or
action, the value extracted or decision made, and the correct output format.

**Task:** "..."

**Step-by-step:**

1. Issue GET with exact parameters (show the URL pattern).
2. Extract the relevant field (name it explicitly).
3. Apply the decision or threshold check.
4. Construct the output or POST body (show correct format).

CORRECT output: `FINISH([3.5])`
WRONG output:   `FINISH(["Potassium is 3.5 mmol/L, within normal range."])`

## Success Indicators

Observable signs the skill was applied correctly — what you would see in the
agent's actions or final output.

## Failure Indicators

Observable signs something went wrong despite following the skill. Include
both obvious failures and subtle regressions.

---

A useful skill is 30–60 lines. A skill that is only 3–5 bullet points is too
shallow to change agent behavior reliably. The agent needs concrete step-by-step
guidance, exact field names, and worked examples to act differently.
