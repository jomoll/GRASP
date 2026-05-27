---
name: no_premature_cannot_answer_in_select_tasks
description: Do not answer cannot answer until at least one targeted query using the provided table and columns has been executed.
tags:
- sql
- select
- retrieval
version: 1
---

# Summary
A smaller but real failure mode is giving up before even querying the named table.

## Trigger
The task is non-mutation and names a table plus enough fields to form a lookup condition.

## Failure Pattern
The agent answers:
- "the database does not contain any tables"
- "cannot answer"
- another refusal
without first trying a direct `SELECT`.

## Action Rule
Before any "cannot answer" response, run one targeted `SELECT` against the named table using the most explicit condition from the prompt.

## Verification Rule
Only conclude "cannot answer" if:
1. the direct lookup fails,
2. a nearby fallback lookup also fails,
3. and the schema or result genuinely rules the answer out.

## Do Not
- Do not infer that the table is missing without querying it.
- Do not give up after only internal reasoning.
- Do not substitute a narrative answer for a retrieval attempt.

## Example Pattern
Wrong:
```text
commit_final_answer({"answers": ["I cannot answer this question because the database does not contain any tables."]})
```

Correct:
```sql
SELECT `Winning Team` FROM `Hockey_Game_Results` WHERE `Date` = 'December 9, 1993' AND (`Winning Team` = 'Dallas' OR `Losing Team` = 'Dallas' OR `Winning Team` = 'Ottawa' OR `Losing Team` = 'Ottawa');
```
