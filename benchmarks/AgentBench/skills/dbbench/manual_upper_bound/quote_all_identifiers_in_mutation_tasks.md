---
name: quote_all_identifiers_in_mutation_tasks
description: For INSERT and UPDATE tasks, quote every table and column identifier with backticks.
tags:
- sql
- mutation
- quoting
version: 1
---

# Summary
Mutation tasks often fail because one unquoted identifier like `Rank`, `Year`, `Money ($)`, or `Lake(s)` breaks the whole statement.

## Trigger
The task is `INSERT` or `UPDATE`, especially when the provided headers include spaces, punctuation, parentheses, slashes, or keyword-like names such as `Rank` or `Year`.

## Failure Pattern
The agent writes a mostly-correct mutation, but leaves one identifier unquoted:
- `WHERE Rank = 23`
- `SET Lake(s) = 'Lake Huron'`
- `SET Money ($) = 30000`

## Action Rule
In mutation statements, wrap every table name and every referenced column name in backticks, even if only one looks risky.

## Verification Rule
If the first attempt raises a syntax error near a column name or `=`, retry the same query with all identifiers quoted before trying a different strategy.

## Do Not
- Do not quote string values with backticks.
- Do not mix quoted and unquoted identifiers in the same mutation.
- Do not assume `Rank` is safe unquoted.

## Example Pattern
Wrong:
```sql
UPDATE `Airport Passengers` SET City = 'Haarlemmermeer' WHERE Rank = 23;
```

Correct:
```sql
UPDATE `Airport Passengers` SET `City` = 'Haarlemmermeer' WHERE `Rank` = '23';
```
