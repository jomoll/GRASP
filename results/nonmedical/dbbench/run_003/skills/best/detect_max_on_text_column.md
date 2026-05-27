---
description: Detect and fix MAX/MIN aggregations on text columns by casting to numeric.
name: detect_max_on_text_column
provenance:
  action: ADD
  epoch: 0
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 162
  - 133
  - 24
  - 91
  - 267
  - 35
  - 225
  - 150
  - 77
  - 15
  update_cycle: 0
tags:
- aggregation
- max
- min
- text
- numeric
- most
- largest
- superlative
version: 1
---

# Detect MAX/MIN on Text Columns

## Pattern Description
When a task asks for the "most", "largest", "highest", "maximum", or similar superlative value, you will typically generate a `MAX()` (or `MIN()`) aggregation. If the target column is stored as a text/varchar type (e.g., contains units like "L", "kg", "%"), applying `MAX()` directly yields lexical ordering, which is incorrect. This skill forces you to inspect the column type first and, if it is non‑numeric, cast or strip non‑numeric characters before performing the aggregation.

## When to Use This Skill
- The instruction contains superlative keywords such as **most**, **largest**, **highest**, **maximum**, **biggest**, **smallest**, **minimum**.
- The inferred SQL query would use `MAX(`*column*`)` or `MIN(`*column*`).
- The column name suggests a measurement (e.g., `Volume`, `Weight`, `Size`, `Length`, `Capacity`, `Score`) **or** a quick `DESCRIBE` of the table shows the column type is `text`, `varchar`, or `char`.

## Common Failure Patterns
- `SELECT MAX(Volume) FROM Car_model_info;` where `Volume` is a text column like `"6.0L"` → returns the lexicographically greatest string, not the numeric maximum.
- Forgetting to strip units before casting, e.g., `CAST(Volume AS DECIMAL)` on `'6.0L'` causing a conversion error.
- Returning the raw string value in the final answer payload instead of the numeric part (or the expected format).

## Recommended Patterns
**Pattern 1: schema check and safe aggregation**
1. **Describe the table** to confirm the column type.
   ```sql
   DESCRIBE `Car_model_info`;
   ```
2. If the column is `text`/`varchar`, **extract the numeric part** and cast to a numeric type before aggregation.
   ```sql
   SELECT MAX(CAST(REPLACE(`Volume`, 'L', '') AS DECIMAL(10,2))) AS max_volume
   FROM `Car_model_info`;
   ```
   - For other units replace accordingly (e.g., `REPLACE(col, '%', '')`).
3. **Optional**: re‑append the unit in the answer if the task expects it.
   ```json
   {"answers": ["6.0L"]}
   ```
   or, if only the numeric value is required:
   ```json
   {"answers": ["6.0"]}
   ```

**Pattern 2: answer payload rule**
- Always call `commit_final_answer` with a JSON payload containing an `answers` array.
- The payload must match the expected format exactly (no stray text). Example:
  ```json
  {"answers": ["6.0L"]}
  ```
  Wrong: `6.0L` printed in plain text.

## Example Application
**Task:** "What is the most volume any engine will hold?" (table `Car_model_info` with column `Volume` stored as text like `"6.0L"`).

**Wrong trajectory (fails)**
1. Think: Need MAX on Volume → construct query.
2. Act: `SELECT MAX(Volume) AS max_volume FROM Car_model_info;`
3. Obs: Returns `('6.0L')` but this is lexical max; if the column had values `"10.0L"` and `"9.5L"` the result could be wrong.
4. Think: Commit answer directly.
5. Act: `commit_final_answer({"answers": ["6.0L"]})` → passes format but may be incorrect for other data.

**Correct trajectory (skill applied)**
1. Think: Task asks for "most" → need MAX. Check column type first.
2. Act: `DESCRIBE `Car_model_info`;`
3. Obs: Shows `Volume` is `varchar`.
4. Think: Strip unit and cast before aggregation.
5. Act: `SELECT MAX(CAST(REPLACE(`Volume`, 'L', '') AS DECIMAL(10,2))) AS max_volume FROM `Car_model_info`;`
6. Obs: Returns `(6.0)`.
7. Think: Re‑append unit for readability.
8. Act: `commit_final_answer({"answers": ["6.0L"]})`.

## Success Indicators
- The agent runs a `DESCRIBE` (or otherwise confirms column type) before the aggregation.
- The `MAX()` query includes a `CAST(... AS DECIMAL)` or equivalent numeric conversion.
- The final answer payload is a JSON object with an `answers` array.

## Failure Indicators
- The agent executes `MAX()` directly on a text column without casting.
- The answer payload is plain text or missing the JSON wrapper.
- The numeric value is wrong because lexical ordering was used.
