---
description: Ensures COUNT queries use the table that actually stores the items being
  counted.
name: validate_aggregation_table_for_count
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 25
  - 71
  - 108
  - 107
  - 145
  - 66
  - 75
  - 275
  - 45
  - 93
  update_cycle: 2
tags:
- counting
- count
- total
- number of
- films
- movies
- aggregation
version: 1
---

# validate_aggregation_table_for_count

## Pattern Description
You must verify that a counting query (`COUNT(*)` or `COUNT(DISTINCT …)`) is executed against the table that contains the entities the user asks to count.  Many benchmark questions phrase the request in natural language (e.g., "total number of films he has made"), and the obvious‑looking table may be a related statistics table instead of the master entity table.  This skill forces a schema‑search step before building the aggregation so the agent selects the correct source table.

## When to Use This Skill
- When the instruction contains a superlative/count phrase such as "total number of", "how many", "count of", "number of" **and** mentions a specific entity type (e.g., *films*, *movies*, *players*, *books*).
- When the task does **not** explicitly name a table, so the agent must infer the appropriate table from column names.
- When the obvious‑looking table (often the one named in the prompt) does not contain a column representing the counted entity.

## Common Failure Patterns
- Using `SELECT COUNT(*) FROM <prompt‑named table>` where that table only holds ratings, scores, or related metadata.
- Counting rows of a lookup table that has one row per *year* or *category* instead of the entity table.
- Omitting `DISTINCT` when the target column can contain duplicate entries, leading to an inflated count.

## Recommended Patterns
**Pattern 1: Identify the correct entity table**
1. **Inspect column names** of all tables (via `SHOW COLUMNS FROM <table>` or `SELECT * FROM <table> LIMIT 1`).
2. Look for a column whose name matches the entity in the question (e.g., `Film`, `Title`, `Movie`, `Player Name`).
3. Choose the table that contains that column as the counting source.

**Pattern 2: Build the COUNT query**
- If the column may have duplicates, use `COUNT(DISTINCT <entity_column>)`.
- Otherwise, `COUNT(*)` is fine.
```sql
-- Correct example for counting a director's films
SELECT COUNT(DISTINCT `Film`) AS total FROM `Films` WHERE `Director` = 'John Doe';
```
```sql
-- Wrong example (used the ratings table)
SELECT COUNT(*) AS total FROM `Film Ratings` WHERE `Director` = 'John Doe';
```

**Pattern 3: Answer payload**
- Return the numeric result as a string inside the `answers` list.
```json
{"answers": ["25"]}
```

## Example Application
**Task:** "What is the total number of films he has made?" (additional info: table *Film Ratings* is described, but the director's film list lives in a table that has a `Film` column).

**Wrong trajectory (fails)**
1. *Think:* The prompt mentions *Film Ratings*, so I will query that.
2. *Act:* `execute_sql({"query": "SELECT COUNT(*) AS total FROM `Film Ratings`"})`
3. *Obs:* Returns `(25,)` – but this counts rating rows, not films.
4. *Think:* I will answer with 25.
5. *Act:* `commit_final_answer({"answers": ["25"]})`
   → **Failure:** wrong source table.

**Correct trajectory (skill applied)**
1. *Think:* The question asks for "total number of films" – I need a table with a `Film` (or `Title`) column.
2. *Act:* `execute_sql({"query": "SHOW COLUMNS FROM `Film Ratings`"})`
3. *Obs:* Columns are Year, Film, Rotten Tomatoes, … – `Film` exists, but this table records ratings, not a film list.
4. *Think:* Search other tables for a distinct `Film` column without rating fields.
5. *Act:* `execute_sql({"query": "SHOW TABLES"})` then iterate until finding a table like `Films` that has `Film` and `Director` columns.
6. *Obs:* `Films` table has columns `Film`, `Director`, `Year`.
7. *Think:* Build the correct COUNT query.
8. *Act:* `execute_sql({"query": "SELECT COUNT(DISTINCT `Film`) AS total FROM `Films` WHERE `Director` = 'John Doe'"})`
9. *Obs:* Returns `(25,)`
10. *Think:* Return the answer.
11. *Act:* `commit_final_answer({"answers": ["25"]})`
   → **Success:** counted films from the proper table.

## Success Indicators
- The agent runs a schema‑inspection step before the COUNT query.
- The final COUNT query references a table that includes the entity column mentioned in the question.
- The answer payload contains the numeric result inside `{"answers": [...]}`.

## Failure Indicators
- The agent selects a table solely based on the name appearing in the prompt without checking column relevance.
- The COUNT query is issued against a table that lacks the entity column.
- The answer is returned without the required JSON payload format.
