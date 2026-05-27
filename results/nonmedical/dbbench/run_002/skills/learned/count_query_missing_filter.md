---
description: Add a WHERE filter to COUNT queries when the question asks for a total
  for a specific person, team, or entity.
name: count_query_missing_filter
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 108
  - 243
  - 25
  - 198
  - 138
  - 75
  - 160
  - 276
  - 93
  - 207
  update_cycle: 0
tags:
- counting
- total
- how many
- aggregate
- count
- filter
- entity
version: 1
---

# Count Query with Entity Filter

## Pattern Description
When the user asks for a total, number, or count that is tied to a particular entity (e.g., a person, team, organization, or any named subject), the agent must not run a plain `COUNT(*)` over the whole table. Instead, it should first discover a column that can hold that entity and then restrict the count with a `WHERE` clause. This prevents over‑counting and matches the intent of questions such as "how many films **he** has made" or "total wins for **Manchester United**".

## When to Use This Skill
- The instruction contains a counting phrase (`total`, `number of`, `how many`, `count`) **and** mentions a specific entity (proper noun, quoted name, or pronoun that refers to a known subject).
- The table schema does **not** contain a column whose name is exactly the entity but does contain a column that plausibly stores that entity (e.g., columns named `Name`, `Person`, `Director`, `Team`, `Artist`, `Owner`).
- The initial instinct might be to write `SELECT COUNT(*) FROM table` without a filter.

## Common Failure Patterns
- Using `SELECT COUNT(*) FROM table` when the question asks for a total for a named subject, resulting in a count of *all* rows.
- Omitting a `WHERE` clause even though a column like `Director`, `Team`, or `Name` exists that could filter the rows.
- Returning an answer that is obviously too large relative to the context (e.g., “25” films for an unspecified director).

## Recommended Patterns
**Pattern 1: Identify a filter column**
1. Run `SHOW COLUMNS FROM <table>`.
2. Scan the returned column names for any that contain keywords from the entity phrase (case‑insensitive): `name`, `person`, `director`, `team`, `owner`, `artist`, `player`, etc.
3. If multiple candidates exist, prefer the one that matches the entity word most closely.

**Pattern 2: Build the filtered COUNT query**
- If a suitable column `col_filter` is found and the entity value can be extracted (e.g., "Manchester United" → `'Manchester United'`):
```sql
SELECT COUNT(*) AS total FROM `table` WHERE `col_filter` = '<entity_value>';
```
- If the column stores the entity in a slightly different format (e.g., case differences, extra spaces), wrap the comparison in `TRIM()` and `COLLATE` if needed.
- If no column matches, fall back to counting distinct values of a likely identifier column (e.g., `COUNT(DISTINCT `Film`)`).

**Pattern 3: Answer payload**
```json
{"answers": ["<numeric_result>"]}
```
Do **not** embed the number in plain text; always call `commit_final_answer` with the JSON payload.

## Example Application
**Task:** "What is the total number of films he has made?" (table `Film Ratings` with columns `Year,Film,Rotten Tomatoes,Metacritic,IMDb` and a hidden column `Director`).

**Wrong trajectory (fails):**
1. *Think*: The user wants a total, so I will count rows.
2. *Act*: `execute_sql({"query": "SELECT COUNT(*) AS total FROM `Film Ratings`"})`
3. *Obs*: Returns `25` (all rows).
4. *Think*: Return the number.
5. *Act*: `commit_final_answer({"answers": ["25"]})`
   – **Failure**: No filter for the director; the answer is the count of *all* films.

**Correct trajectory (skill applied):**
1. *Think*: The question asks for a total for a specific person (“he”). I need to find the column that stores the director name.
2. *Act*: `execute_sql({"query": "SHOW COLUMNS FROM `Film Ratings`"})`
3. *Obs*: Columns returned include `Director`.
4. *Think*: Use `Director` as the filter column and the pronoun refers to the director mentioned earlier in the conversation (assume we have extracted `"Quentin Tarantino"`).
5. *Act*: `execute_sql({"query": "SELECT COUNT(*) AS total FROM `Film Ratings` WHERE `Director` = 'Quentin Tarantino'"})`
6. *Obs*: Returns `3`.
7. *Think*: Return the filtered count.
8. *Act*: `commit_final_answer({"answers": ["3"]})`
   – **Success**: The count now reflects only the films made by the specified director.

## Success Indicators
- The generated `SELECT` statement includes a `WHERE` clause that references a column matching the entity.
- The returned count is plausibly smaller than the raw row count and aligns with the entity context.
- The final answer is delivered via `commit_final_answer` with a JSON payload.

## Failure Indicators
- The agent emits a `COUNT(*)` query without any `WHERE` clause despite the question mentioning a specific entity.
- The final answer payload is a plain string or missing the `answers` key.
- The observed row count equals the total number of rows in the table, suggesting no filter was applied.
