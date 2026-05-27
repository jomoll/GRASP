---
name: skeleton
description: Template and quality standard for learned skills — read-only
tags: []
---

# Skill Title

Use a title that names a reusable SQL/database capability, pattern, or strategy.
Prefer broad titles like `Aggregate Query Construction` or
`Answer Format for Mutation Queries` over titles that only name one specific table
or column, unless the rule is truly unique to that object.

## Pattern Description

Write 1–3 paragraphs. State the central reusable lesson. Describe the general
capability first, then anchor it with the type of behavior it should change.

- Keep the opening general and reusable.
- Do not front-load with one specific table name unless the rule is unique to it.
- Focus on a stable SQL/database pattern, not one isolated benchmark case.

## When to Use This Skill

Bullet list of task types and trigger conditions where this skill applies.
Be specific about when the agent should actively recall this skill.

- Example: "When the question asks for a count and the table has duplicate rows"
- Example: "When the task is an INSERT and requires reading the exact column order
  from the table schema before constructing the statement"
- Example: "When an aggregation query returns NULL and the agent must handle it"

## Common Failure Patterns

Bullet list. Reference exact SQL constructs, column names, or output formats.

- Example: using `COUNT(*)` instead of `COUNT(DISTINCT col)` when duplicates exist
- Example: submitting `["3.5"]` (string) when the answer expects `[3.5]` (float) —
  the `commit_final_answer` payload must match exactly
- Example: not wrapping table/column names in backticks when they contain spaces
- Cover both obvious failures and subtle regressions

## Recommended Patterns

Step-by-step operational guidance. Name exact SQL clauses or tool payload formats.

**Pattern 1: core query strategy**
Describe what to do, in order. Show the exact SQL structure.

CORRECT:
```sql
SELECT COUNT(DISTINCT `column_name`) FROM `table_name` WHERE condition;
```
WRONG:
```sql
SELECT COUNT(`column_name`) FROM `table_name` WHERE condition;
```

**Pattern 2: answer payload rule**
How to structure the `commit_final_answer` payload for this query type.

CORRECT: call `commit_final_answer` with `{"answers": ["March 19, 1998"]}`
WRONG:   write `March 19, 1998` in assistant text without calling the tool

**Pattern 3: mutation verification**
For INSERT/UPDATE/DELETE tasks, use `execute_sql` for the mutation, verify the
changed rows with a targeted `SELECT`, then call `commit_final_answer`.

## Example Application

At least one worked example with explicit steps.

**Task:** "Insert 'Madison High School' into the School Location Table..."

**Step-by-step:**

1. Query the table schema to confirm column order.
2. Construct the INSERT with backtick-quoted column names.
3. Execute and check the MySQL response for errors.
4. Verify the inserted row with a targeted SELECT.
5. Commit with `commit_final_answer` using a minimal payload such as
   `{"answers": ["done"]}`.

CORRECT SQL:
```sql
INSERT INTO `School Location Table` (`School`, `Location`, `Date moved`, `Currently at this location`) VALUES ('Madison High School', 'San Diego', '1980', 'nearby junior high school');
```

## Success Indicators

Observable signs the skill was applied correctly.

## Failure Indicators

Observable signs something went wrong despite following the skill. Include
both wrong SQL (syntax, logic) and wrong tool-payload failures.

---

A useful skill is 30–60 lines. Include concrete SQL examples — vague guidance
does not change agent behavior reliably.
