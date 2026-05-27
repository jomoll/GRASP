---
description: Cast text columns to numeric before SUM/AVG aggregations to avoid string
  concatenation or errors.
name: numeric_cast_for_aggregation
provenance:
  action: ADD
  epoch: 1
  fixes: 2
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 192
  - 3
  - 280
  - 267
  - 141
  - 133
  - 221
  - 121
  - 75
  - 71
  update_cycle: 1
tags:
- aggregation
- sum
- total
- average
- numeric
- cast
version: 1
---

# numeric_cast_for_aggregation

## Pattern Description
When a task asks for a total, sum, average, or any numeric aggregation, the target column is often stored as `TEXT` (e.g., containing commas, periods, or other formatting). Directly applying `SUM()` or `AVG()` on such columns leads to incorrect results or type errors because MySQL treats the values as strings. This skill forces the agent to detect text‑typed numeric columns and apply the appropriate `CAST` (and optional `REPLACE`) before performing the aggregation.

## When to Use This Skill
- The instruction contains keywords like **total**, **sum**, **combined**, **overall**, **average**, **mean**, **add up**, or **calculate** that imply a numeric aggregation.
- The column name in the question suggests a count or numeric measure (e.g., `population`, `playoffs appearances`, `value`, `amount`, `price`).
- The schema inspection (`DESCRIBE <table>`) shows the column’s data type is `text` (or `varchar`).

## Common Failure Patterns
- Using `SELECT SUM(column) …` on a `TEXT` column, producing `0` or a concatenated string.
- Forgetting to remove thousand‑separator commas before casting, causing `CAST('1,234' AS UNSIGNED)` to fail.
- Applying `AVG` on a text column without casting, yielding `NULL` or incorrect decimal.
- Returning the raw string result instead of a numeric value.

## Recommended Patterns
**Pattern 1: Identify column type**
```sql
DESCRIBE `table_name`;
```
Inspect the `Type` field for the target column. If it contains `text`/`varchar`, proceed with casting.

**Pattern 2: Build a safe numeric expression**
- For integer‑like values (may contain commas):
```sql
CAST(REPLACE(`column_name`, ',', '') AS UNSIGNED)
```
- For decimal values (may contain commas as thousand separators and a dot as decimal point):
```sql
CAST(REPLACE(REPLACE(`column_name`, ',', ''), '.', '.') AS DECIMAL(15,2))
```
Adjust the precision as needed.

**Pattern 3: Perform the aggregation**
```sql
SELECT SUM(CAST(REPLACE(`column_name`, ',', '') AS UNSIGNED)) AS total
FROM `table_name`
WHERE <any necessary filters>;
```
or for average:
```sql
SELECT AVG(CAST(REPLACE(`column_name`, ',', '') AS DECIMAL(15,2))) AS avg_val
FROM `table_name`
WHERE <filters>;
```

**Pattern 4: Answer payload**
```json
{"answers": ["<numeric_result>"]}
```
Do **not** embed the number in plain text.

## Example Application
**Task:** "What is the total number of playoffs appearances from all teams?"

**Wrong trajectory (fails)**
- *Think:* The column `Playoffs appearances` looks numeric, so I will sum it directly.
- *Act:* `SELECT SUM(`Playoffs appearances`) AS total FROM `Basketball Teams History`;`
- *Obs:* The column type is `text`; MySQL returns `0` or a concatenated string, leading to an incorrect answer.
- *Think:* I have the answer, so I commit.
- *Act:* `commit_final_answer({"answers": ["429"]})`

**Correct trajectory (skill applied)**
- *Think:* The task asks for a *total* and the column name sounds numeric, but I should verify its type.
- *Act:* `DESCRIBE `Basketball Teams History`;`
- *Obs:* `Playoffs appearances` is listed as `text`.
- *Think:* I must cast it to a number, removing commas if present.
- *Act:* `SELECT SUM(CAST(REPLACE(`Playoffs appearances`, ',', '') AS UNSIGNED)) AS total FROM `Basketball Teams History`;`
- *Obs:* Result `429` (numeric).
- *Think:* Return the numeric total.
- *Act:* `commit_final_answer({"answers": ["429"]})`

## Success Indicators
- The agent runs a `DESCRIBE` before the aggregation.
- The final aggregation query contains `CAST` (and optional `REPLACE`).
- The `commit_final_answer` payload contains a plain numeric string, not a formatted one.

## Failure Indicators
- The aggregation query references the column directly without casting.
- The answer payload contains a non‑numeric string or extra formatting.
- The agent skips the `DESCRIBE` step for a column that is actually `text`.
