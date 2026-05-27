---
name: skeleton
description: Template and quality standard for learned skills — read-only
tags: []
---

# Skill Title

Use a title that names a reusable capability, pattern, or strategy.
Prefer broad titles like `Truncated Output Handling` or
`File Search Strategy` over titles that only name one specific task
object, unless the rule is truly unique to that object.

## Pattern Description

Write 1–3 paragraphs. State the central reusable lesson. Describe the general
capability first, then anchor it with the type of behavior it should change.

- Keep the opening general and reusable.
- Do not front-load the skill with one specific command or task unless
  the rule is genuinely unique to that case.
- Focus on a stable pattern, not one isolated benchmark case.

## When to Use This Skill

Bullet list of task types and trigger conditions where this skill applies.
Be specific about when the agent should actively recall this skill — name the
observable situation, not just the abstract category.

- Example: "When bash output is truncated at 800 chars and the answer requires
  the full content"
- Example: "When searching for a file and `find` returns nothing but the file
  may exist under a different name or location"

## Common Failure Patterns

Bullet list. Be specific — reference exact commands, flags, output fields,
or tool payload formats when that is the real source of failure.

- Example: using `cat` on a large file when `wc -l` or `grep -c` would give
  the count directly without truncation risk
- Example: returning a raw number like `3.14` when the task expects a string
  like `3.14 GB` — or vice versa
- Cover both obvious failures and subtle regressions

## Recommended Patterns

Step-by-step operational guidance. Name exact commands or flags to use.
Include concrete correct/wrong examples where helpful.

**Pattern 1: core strategy or rule**
Describe what to do, in order. Name the exact commands or flags.

CORRECT: `ls -1 /etc | wc -l`  (counts lines directly, no truncation)
WRONG:   `ls /etc` then counting manually from truncated output

**Pattern 2: fallback or verification rule**
What to do when the primary strategy fails or returns no results.

**Pattern 3: formatting or answer rule**
How to structure the final `answer_action` payload.

## Example Application

At least one worked example with explicit steps. Show the actual command,
the value extracted or decision made, and the correct answer format.

**Task:** "..."

**Step-by-step:**

1. Run the appropriate command (show the exact bash snippet).
2. Parse the relevant field from the output (name it explicitly).
3. Apply any threshold or transformation.
4. Call `answer_action` or `finish_action` with the correct payload.

CORRECT output: call `answer_action` with `{"answer": "220"}`
WRONG output:   write `There are 220 files in /etc` as assistant text

## Success Indicators

Observable signs the skill was applied correctly — what you would see in the
agent's actions or final answer.

## Failure Indicators

Observable signs something went wrong despite following the skill. Include
both obvious failures and subtle regressions.

---

A useful skill is 30–60 lines. A skill that is only 3–5 bullet points is too
shallow to change agent behavior reliably. The agent needs concrete step-by-step
guidance, exact commands, and worked examples to act differently.
