---
description: Prevent using a constant multiplier on a total when a percentage filter
  is required for aggregation.
name: avoid_constant_multiplier_aggregation
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - 25
  - 71
  - 108
  - 107
  - 145
  - 75
  - 275
  - 45
  - 93
  - 149
  update_cycle: 2
tags:
- aggregation
- percentage
- sum
- filter
- constant_multiplier
version: 1
---

# Avoid Constant Multiplier Aggregation for Percentage Filters

## Pattern Description
When a task asks for a total (e.g., SUM) *for rows that match a given percentage* (e.g., "foreign nationals in % of 23,3%"), the correct strategy is to **filter the rows by the percentage column** and then aggregate the numeric column.  A common mistake is to compute the overall SUM and multiply it by the percentage value, which yields an incorrect result when the percentage applies only to a subset of rows.

## When to Use This Skill
- The instruction contains the words *percentage*, *%*, or a literal percentage value (e.g., `23,3%`, `12%`).
- The query type is an aggregation (`SUM`, `AVG`, `COUNT`, etc.) and the user wants a total *for that percentage* rather than the percentage of the total.
- The schema includes a column that stores percentages as text (often with a `%` sign or locale‑specific decimal separator).

## Common Failure Patterns
- Using `SELECT SUM(col) * 0.233 …` instead of filtering rows where the percentage column equals `23,3%`.
- Converting the entire column to a numeric type and applying the multiplier globally.
- Ignoring locale‑specific decimal separators (comma vs dot) and casting the percentage value incorrectly.
- Returning a single scalar that does **not** respect the intended filter.

## Recommended Patterns
**Pattern 1: Core query strategy**
1. Identify the column that holds the percentage (e.g., `Foreign nationals in %`).
2. Use the exact textual representation from the instruction in the `WHERE` clause (preserve commas, spaces, and the `%` sign).
3. Aggregate the numeric column after the filter.

CORRECT:
```sql
SELECT SUM(`Population`) AS total_population
FROM `city_district_statistics`
WHERE `Foreign nationals in %` = '23,3%';
```

WRONG (constant multiplier):
```sql
SELECT SUM(`Population`) * 0.233 AS total_population
FROM `city_district_statistics`;
```

**Pattern 2: Answer payload rule**
- After receiving the numeric result, call `commit_final_answer` with a JSON payload containing the raw number (as string or number, matching the expected type).

CORRECT:
```json
{"answers": ["4911"]}
```
WRONG: embedding the answer in free‑form text or omitting the tool call.

## Example Application
**Task:** "I want to know the total number of population for foreign nationals in percentage of 23,3%"

**Wrong trajectory (fails):**
1. *Think*: The user wants a total, so compute the overall sum and multiply by 0.233.
2. *Act*: `execute_sql({"query": "SELECT SUM(Population) * 0.233 AS total FROM city_district_statistics"})`
3. *Obs*: Returns a number, but it does not respect the specific percentage filter.
4. *Think*: Assume the result is correct and commit.
5. *Act*: `commit_final_answer({"answers": ["229"]})`
   → **Failure** – result is wrong because the multiplier was applied to all rows.

**Correct trajectory (uses the new skill):**
1. *Think*: The instruction mentions a specific percentage value (`23,3%`). I must filter rows where the percentage column equals that value before aggregating.
2. *Act*: `execute_sql({"query": "SELECT SUM(`Population`) AS total_population FROM `city_district_statistics` WHERE `Foreign nationals in %` = '23,3%'"})`
3. *Obs*: Returns `4911`.
4. *Think*: The aggregation respects the filter; commit the exact number.
5. *Act*: `commit_final_answer({"answers": ["4911"]})`
   → **Success** – the answer matches the intended calculation.

## Success Indicators
- The generated SQL contains a `WHERE` clause that matches the percentage literal from the task.
- No multiplication (`*`) of the aggregated column by a constant appears.
- The final answer payload contains the single numeric result.

## Failure Indicators
- The SQL query multiplies the SUM (or other aggregate) by a constant derived from the percentage.
- The `WHERE` clause does not reference the percentage column.
- The answer payload is missing or includes explanatory text instead of a strict JSON array.
