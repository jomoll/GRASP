---
description: Detect and safely handle aggregation (MAX, MIN, AVG, SUM) on textual
  columns by converting or ordering instead of raw aggregation.
name: prevent_aggregation_on_text_columns
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - 162
  - 133
  - 24
  - 91
  - 242
  - 267
  - 35
  - 225
  - 150
  - 77
  update_cycle: 0
tags:
- aggregation
- max
- min
- average
- sum
- most
- least
- largest
- smallest
- text_column
- numeric_conversion
version: 1
---

# prevent_aggregation_on_text_columns

## Pattern Description
You must avoid applying SQL aggregation functions directly to columns whose declared type is a text type (e.g., `VARCHAR`, `CHAR`, `TEXT`). Text columns often store values with units ("6.0L", "$3.6 billion", dates, etc.) that cannot be numerically aggregated. Instead, first inspect the column type with `SHOW COLUMNS` (or `INFORMATION_SCHEMA.COLUMNS`). If the column is textual, rewrite the query to extract a numeric representation using `CAST`/`REPLACE` and then aggregate, or use an `ORDER BY … LIMIT 1` pattern for superlatives (most/least).

## When to Use This Skill
- When the instruction contains superlative or quantitative words such as **most**, **largest**, **highest**, **least**, **minimum**, **average**, **total**, **sum**, **count**, **mean** and the implied operation would be an aggregation (`MAX`, `MIN`, `AVG`, `SUM`).
- When you are about to run an aggregation on a column whose name suggests a measurement (e.g., `Volume`, `Weight`, `Price`, `Score`) but you have not yet verified its data type.
- After a `SHOW COLUMNS` (or `DESCRIBE`) call reveals the target column is of type `CHAR`, `VARCHAR`, `TEXT`, or similar.

## Common Failure Patterns
- `SELECT MAX(Volume) FROM Car_model_info;` where `Volume` is stored as strings like `"6.0L"` → returns the lexicographically largest string, not the numeric maximum.
- Using `AVG` on a column that contains currency strings (e.g., `"$3.6 billion"`).
- Forgetting to strip units or symbols before casting, causing a SQL error or wrong result.
- Returning a string answer (e.g., `"6.0L"`) when the expected numeric answer is `6.0`.

## Recommended Patterns
**Pattern 1: schema inspection before aggregation**
1. Run `SHOW COLUMNS FROM <table> LIKE '<column>';` to get the `Type`.
2. If the `Type` contains `char`/`text`, treat the column as textual.
3. Choose one of the two safe strategies:
   - **Numeric extraction** (when the format is consistent):
     ```sql
     SELECT MAX(CAST(REPLACE(REPLACE(<column>, 'L', ''), '$', '') AS DECIMAL(10,2))) AS max_val
     FROM <table>
     WHERE <optional filters>;
     ```
   - **Order‑by‑limit** (when extraction is unclear):
     ```sql
     SELECT <column>
     FROM <table>
     WHERE <optional filters>
     ORDER BY CAST(REPLACE(REPLACE(<column>, 'L', ''), '$', '') AS DECIMAL(10,2)) DESC
     LIMIT 1;
     ```
   Adjust the `REPLACE` calls to strip the specific unit symbols present in the data.

**Pattern 2: answer payload**
- After obtaining the numeric result, return it **without the unit** unless the question explicitly asks for the unit.
  ```json
  {"answers": ["6.0"]}
  ```
- If the unit is required, append it in the answer string, not as a separate payload element.

**Pattern 3: fallback for non‑numeric text**
- If the column cannot be reliably converted, respond that the data is non‑numeric and provide the raw value(s) via a `SELECT` with `LIMIT 1`.

## Example Application
**Task:** "What is the most volume any engine will hold?" (Table `Car_model_info`, column `Volume` contains values like `"6.0L"`).

**Wrong trajectory (fails)**
1. **Think:** The question asks for the highest volume → use `MAX`.
2. **Act:** `execute_sql({"query": "SELECT MAX(Volume) AS max_volume FROM Car_model_info"})`
3. **Obs:** Returns `"6.0L"` (lexicographic max, may be wrong if values like `"10.0L"` exist).
4. **Think:** Commit the answer.
5. **Act:** `commit_final_answer({"answers": ["6.0L"]})`
*Result:* Incorrect numeric comparison; aggregation on text.

**Correct trajectory (skill applied)**
1. **Think:** The question is superlative → need aggregation on `Volume`.
2. **Act:** `execute_sql({"query": "SHOW COLUMNS FROM Car_model_info LIKE 'Volume'"})`
3. **Obs:** Returns type `varchar(10)` → textual.
4. **Think:** Use numeric extraction via `REPLACE` and `CAST`.
5. **Act:** `execute_sql({"query": "SELECT MAX(CAST(REPLACE(Volume, 'L', '') AS DECIMAL(10,2))) AS max_volume FROM Car_model_info"})`
6. **Obs:** Returns `6.0` (correct numeric maximum).
7. **Think:** Return the numeric value.
8. **Act:** `commit_final_answer({"answers": ["6.0"]})`
*Result:* Accurate answer and no misuse of aggregation on text.

## Success Indicators
- The skill is invoked when the task wording contains superlatives and the target column is identified as text.
- The agent runs a `SHOW COLUMNS` (or similar) before the aggregation.
- The final SQL uses `CAST`/`REPLACE` or an `ORDER BY … LIMIT 1` pattern instead of raw `MAX`/`MIN`/`AVG`.
- The `commit_final_answer` payload contains a numeric value (or the correctly formatted string) matching the expected answer.

## Failure Indicators
- The agent executes `SELECT MAX(text_column) ...` without inspecting the column type.
- The answer payload includes the original text with units when a pure number is expected.
- The skill is not triggered despite the presence of words like "most" or "average".
- The agent receives a SQL error because the `CAST` expression is missing a necessary `REPLACE` for the unit.
