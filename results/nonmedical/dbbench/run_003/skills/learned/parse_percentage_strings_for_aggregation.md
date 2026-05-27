---
description: "Convert locale\u2011specific percentage strings (e.g., \u201C23,3%\u201D\
  ) to numeric before filtering or aggregating."
name: parse_percentage_strings_for_aggregation
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - 146
  - 130
  - 221
  - 174
  - 43
  - 101
  - 257
  - 166
  - 45
  - 71
  update_cycle: 2
tags:
- aggregation
- sum
- percentage
- locale
- numeric_cast
version: 1
---

# parse_percentage_strings_for_aggregation

## Pattern Description
When a task asks for a numeric aggregation (SUM, AVG, MIN, MAX) **and** the table contains columns that store percentages as text with a comma decimal separator and a trailing `%` sign, the raw string cannot be compared or summed directly. The agent must strip the `%` character and replace the comma with a dot (or remove it for integer casts) before casting to a numeric type. This pattern also applies when the WHERE clause filters on such a percentage column.

## When to Use This Skill
- The instruction contains a percentage value written with a comma and a trailing `%` (e.g., `23,3%`).
- The table schema shows a column name that includes `%` (e.g., `Foreign nationals in %`).
- The query type is an aggregation (`SUM`, `AVG`, `MIN`, `MAX`).
- The task asks for a total, average, highest, or lowest value **and** mentions a percentage filter.

## Common Failure Patterns
- Using `WHERE column = '23,3%'` on a text column that stores `23,3%` and then summing another column without converting the percentage column to a numeric value.
- Applying `CAST(column AS UNSIGNED)` directly on a string like `23,3%`, which results in `0` or a cast error.
- Forgetting to remove the `%` sign, causing the comparison to fail and returning an empty result set.
- Using `REPLACE(column, ',', '')` but leaving the `%` sign, leading to `CAST('23,3%' AS UNSIGNED)` → error.

## Recommended Patterns
**Pattern 1: Filter on a percentage column**
```sql
-- WRONG
SELECT SUM(pop) FROM tbl WHERE `Foreign nationals in %` = '23,3%';

-- CORRECT
SELECT SUM(pop) AS total
FROM tbl
WHERE CAST(REPLACE(REPLACE(`Foreign nationals in %`, '%', ''), ',', '.') AS DECIMAL(10,2)) = 23.3;
```
**Pattern 2: Aggregate a numeric column that contains commas**
```sql
-- WRONG (keeps commas)
SELECT SUM(`Population`) FROM tbl;

-- CORRECT (remove commas before casting)
SELECT SUM(CAST(REPLACE(`Population`, ',', '') AS UNSIGNED)) AS total_population
FROM tbl;
```
**Pattern 3: Combine both when the WHERE clause uses a percentage and the aggregation target needs cleaning**
```sql
SELECT SUM(CAST(REPLACE(`Population`, ',', '') AS UNSIGNED)) AS total_pop
FROM `city_district_statistics`
WHERE CAST(REPLACE(REPLACE(`Foreign nationals in %`, '%', ''), ',', '.') AS DECIMAL(10,2)) = 23.3;
```

## Example Application
**Task:** "I want to know the total number of population for foreign nationals in percentage of 23,3%"

**Wrong trajectory (fails):**
1. *Think:* Need to filter rows where `Foreign nationals in %` equals `23,3%` and sum `Population`.
2. *Act:* `SELECT SUM(CAST(REPLACE(`Population`, ',', '') AS UNSIGNED)) AS total FROM city_district_statistics WHERE `Foreign nationals in %` = '23,3%';`
3. *Obs:* The query returns no rows because the string comparison fails (the column value includes a `%`).
4. *Think:* Return the (incorrect) result `4`.

**Correct trajectory (skill applied):**
1. *Think:* The task mentions a percentage with a comma; the table has a `%` column. I must convert it to a numeric value before filtering.
2. *Act:* `SELECT SUM(CAST(REPLACE(`Population`, ',', '') AS UNSIGNED)) AS total_pop
   FROM city_district_statistics
   WHERE CAST(REPLACE(REPLACE(`Foreign nationals in %`, '%', ''), ',', '.') AS DECIMAL(10,2)) = 23.3;`
3. *Obs:* The query returns the correct total (e.g., `4256.9`).
4. *Think:* Commit the answer with the numeric total.

## Success Indicators
- The `execute_sql` observation returns a non‑empty numeric result for the aggregation.
- No SQL error about invalid cast or unknown column.
- The `commit_final_answer` payload contains the expected numeric value.

## Failure Indicators
- Observation shows `0` rows or `NULL` when a non‑zero result is expected.
- SQL error: `Incorrect decimal value: '23,3%'` or similar cast error.
- The final answer is a string that includes the `%` sign instead of a plain number.
