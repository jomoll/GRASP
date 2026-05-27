---
description: Correctly compute MAX on text columns that store numbers with units or
  extra characters.
name: aggregation_max_numeric_units
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - 145
  - 192
  - 252
  - 133
  - 298
  - 24
  - 141
  - 54
  - 185
  - 267
  update_cycle: 1
tags:
- max
- most
- largest
- highest
- aggregation
- volume
- capacity
- measurement
version: 1
---

# aggregation_max_numeric_units

## Pattern Description
When a question asks for the *largest*, *most*, *highest* or *maximum* value of a measurement (e.g., volume, capacity, weight) the underlying column is often stored as **TEXT** and includes units or stray spaces. A naïve `MAX(col)` on the raw text returns the lexicographically greatest string, which is wrong, and even `MAX(CAST(col AS DECIMAL))` can miss values that contain extra characters (e.g., "6.5 L", " 7L"). This skill forces you to **clean the column**, cast it to a numeric type, **order by the cleaned value**, and finally return the **original un‑cleaned value** so the unit is preserved.

## When to Use This Skill
- The instruction contains superlatives such as *most*, *largest*, *highest*, *maximum*, *biggest*.
- The target column name suggests a measurement (contains words like `volume`, `capacity`, `weight`, `size`, `length`, `height`, `speed`).
- A `SHOW COLUMNS` query reveals the column’s data type is `text`/`varchar` (or any non‑numeric type).
- You are about to run an aggregation query of type **MAX**.

## Common Failure Patterns
- Using `SELECT MAX(col) FROM tbl` on a text column and returning a string that is lexicographically max but numerically incorrect.
- Casting directly with `MAX(CAST(col AS DECIMAL))` when the text contains extra characters (units, spaces) that prevent proper conversion, yielding NULL or a lower value.
- Returning the cleaned numeric value (e.g., `6.0`) instead of the original representation (`6.0L`).

## Recommended Patterns
**Pattern 1: column type inspection**
```sql
SHOW COLUMNS FROM `table_name` LIKE 'column_name';
```
Observe the `Type` field. If it contains `text` or `varchar`, treat it as a unit‑encoded column.

**Pattern 2: clean‑and‑order query**
```sql
SELECT `column_name`
FROM `table_name`
WHERE `column_name` IS NOT NULL
ORDER BY CAST(
        REPLACE(
            REPLACE(
                REPLACE(`column_name`, 'L', ''),
                'l', ''),
            ' ', ''
        ) AS DECIMAL(10,2)
    ) DESC
LIMIT 1;
```
- Replace the unit string (`'L'`) with the appropriate unit for the column (e.g., `'kg'`, `'mph'`).
- The `REPLACE(' ', '')` removes stray spaces.
- The query returns the **original** text value of the row that has the highest numeric measurement.

**Pattern 3: answer payload**
```json
commit_final_answer({"answers": ["<original_value>"]})
```
Do **not** strip the unit; return exactly what the column stores.

## Example Application
**Task:** "What is the most volume any engine will hold?" (table `Car_model_info`, column `Volume`).

**Wrong trajectory (failure):**
1. Think: *Volume looks numeric, use MAX.*
2. Act: `SELECT MAX(CAST(REPLACE(Volume, 'L', '') AS DECIMAL(10,2))) FROM Car_model_info;`
3. Obs: Returns `6.00`.
4. Think: *Answer is 6.0.*
5. Act: `commit_final_answer({"answers": ["6.0"]})` → **Wrong** because the true maximum is `6.5L`.

**Correct trajectory (skill applied):**
1. Think: *Superlative + column name suggests a measurement stored as text → use cleaning strategy.*
2. Act: `SHOW COLUMNS FROM Car_model_info LIKE 'Volume';`
3. Obs: Type = `text`.
4. Think: *Clean and order.*
5. Act:
```sql
SELECT Volume
FROM Car_model_info
WHERE Volume IS NOT NULL
ORDER BY CAST(REPLACE(REPLACE(Volume, 'L', ''), ' ', '') AS DECIMAL(10,2)) DESC
LIMIT 1;
```
6. Obs: Returns `('6.5L',)`.
7. Think: *Return the original value with its unit.*
8. Act: `commit_final_answer({"answers": ["6.5L"]})` → **Correct**.

## Success Indicators
- The `SHOW COLUMNS` step reports a non‑numeric type.
- The final SELECT uses `ORDER BY … DESC LIMIT 1` on the cleaned numeric cast.
- The answer payload contains the original column string (including unit).

## Failure Indicators
- The agent runs a plain `MAX(col)` on a text column and returns a lexicographic result.
- The agent casts to numeric inside `MAX` but still returns the cleaned numeric value instead of the original string.
- The answer omits the unit or returns a value that does not match any row in the table.
