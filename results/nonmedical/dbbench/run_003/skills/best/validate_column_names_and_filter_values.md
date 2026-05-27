---
description: Check that every column used in a WHERE clause exists and that string
  literals are copied exactly from the task.
name: validate_column_names_and_filter_values
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - 112
  - 130
  - 166
  - 151
  - 126
  - 47
  - 199
  - 207
  - 137
  - 239
  update_cycle: 1
tags: []
version: 1
---

# Validate Column Names and Exact Filter Values

## Pattern Description
You must never assume a column name or a filter value is correct without first confirming it against the table schema. For any task that requires a `WHERE` clause, first retrieve the column list with `DESCRIBE`, match the natural‑language column references to the exact schema names (using backticks for names containing spaces or symbols), and copy the literal value verbatim—including spaces, punctuation, and case. This prevents two common errors: (1) referencing a non‑existent column (e.g., `Match` when the schema uses a different spelling) and (2) truncating or altering string filter values (e.g., using `'A'` instead of `'A Arena'`).

## When to Use This Skill
- When the instruction contains phrases like "at **X**, the **Y** league" or "where **Column** equals **Value**" that will be turned into a `WHERE` clause.
- When column names in the schema contain spaces, parentheses, or other special characters.
- When the task mentions a specific string that includes spaces or punctuation.
- When you are about to construct a query that filters on text columns.

## Common Failure Patterns
- Using a column name that does not appear in `DESCRIBE` output (e.g., `SELECT ... WHERE Match > 16` when the schema has `Match #` or `MatchID`).
- Writing `WHERE Arena='A'` instead of the full value `'A Arena'` because the agent split the phrase at a space.
- Forgetting to backtick‑quote column identifiers that contain spaces (e.g., `` `Date & Time ( CET )` ``).
- Omitting single quotes around string literals, leading to syntax errors or numeric comparison.

## Recommended Patterns
**Pattern 1: schema discovery and column validation**
1. `execute_sql({"query": "DESCRIBE `table_name`;"})` – store the list of column names.
2. Parse the instruction to extract *column‑value* pairs.
3. For each extracted column, check that it exists (case‑insensitive) in the schema list.
   - If it does not, abort with a helpful error or try a synonym mapping.
4. Quote the column with backticks: `` `Column Name` ``.
5. Quote the literal value exactly as it appears in the instruction, preserving spaces and case.

**Pattern 2: safe WHERE clause construction**
```sql
SELECT <desired_columns>
FROM `table_name`
WHERE `Arena` = 'A Arena'
  AND `League` = 'SL'
  AND `Match` > 16;
```
- **CORRECT**: column names back‑ticked, string literals fully quoted.
- **WRONG**: `WHERE Arena='A' AND League='SL' AND Match>16;` (truncated value, missing backticks).

**Pattern 3: verification step**
After executing the SELECT, quickly glance at the first few rows to ensure the filter behaved as expected. If the result set is empty and you expected rows, double‑check the literal values.

## Example Application
**Task:** "What was the result at A Arena, the SL league, and a match number over 16?"

**Wrong trajectory (fails):**
1. *Think*: Build query directly.
2. *Act*: `execute_sql({"query": "SELECT Result FROM `Basketball Matches` WHERE Arena='A Arena' AND League='SL' AND `Match`>16;"})`
3. *Obs*: Returns rows, but agent later runs another query with `Arena='A'` and returns wrong answers.
4. *Think*: No further validation, commits wrong answer.

**Correct trajectory (skill applied):**
1. *Think*: Need column list before filtering.
2. *Act*: `execute_sql({"query": "DESCRIBE `Basketball Matches`;"})`
3. *Obs*: Columns returned include `Match`, `League`, `Arena`, `Result`.
4. *Think*: All columns exist; extract filter values exactly.
5. *Act*: `execute_sql({"query": "SELECT Result FROM `Basketball Matches` WHERE `Arena`='A Arena' AND `League`='SL' AND `Match`>16;"})`
6. *Obs*: Result rows `["63–85", "57–87"]`.
7. *Think*: Values look plausible, no empty set.
8. *Act*: `commit_final_answer({"answers": ["63–85", "57–87"]})`

## Success Indicators
- `DESCRIBE` runs before any query that uses a `WHERE` clause.
- All column identifiers in the final query are wrapped in backticks.
- String literals in the `WHERE` clause exactly match the phrasing in the instruction (including spaces).
- The query returns a non‑empty result set that matches the expected semantics.

## Failure Indicators
- The agent emits a query that references a column not present in the `DESCRIBE` output.
- The `WHERE` clause contains a truncated or altered string value.
- The final answer is based on a result set that is empty when the task clearly expects rows.
- No `DESCRIBE` step appears before the first SELECT/UPDATE/DELETE that filters on text columns.

---
**Tags**: ["filter", "where", "column", "string", "match", "validation"]
