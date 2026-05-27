---
description: "Ensure every value inserted in an INSERT exactly matches the phrasing\
  \ (including units, adjectives, and required fields) described in the task. This\
  \ skill only activates for genuine INSERT\u2011type mutations (keywords: INSERT,\
  \ add, record, new entry, added, hired) and when the instruction contains a value\
  \ that includes a non\u2011numeric qualifier (e.g., units, adjectives). It will\
  \ not run for SELECT/UPDATE/DELETE tasks, preventing unintended interference with\
  \ non\u2011mutation queries."
name: insert_values_match_task_description
provenance:
  action: ADD
  epoch: 2
  fixes: 3
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 108
  - 25
  - 198
  - 138
  - 75
  - 160
  - 276
  - 93
  - 159
  - 29
  update_cycle: 0
tags: []
version: 1
---

# Insert Values Must Match Task Description (Narrowed Trigger)

## When to Apply
- The **intended SQL operation** is an **INSERT** (or synonymous wording such as *add a new row*, *record*, *new entry*, *hired*).
- The natural‑language instruction contains at least one **value with a qualifier** (unit, adjective, composite phrase) that should be stored verbatim, e.g., `11.2km`, `40 horsepower`, `Actress Jane Doe`.
- The target column(s) are of type `TEXT`/`VARCHAR` (free‑form strings), not pure numeric columns.

## Guard Clause (prevents regression)
1. **Detect operation type**: before applying the skill, confirm the agent’s next SQL statement starts with `INSERT INTO` (case‑insensitive) **or** the instruction contains one of the mutation keywords *add*, *record*, *new entry*, *added*, *hired* **and** the agent plans an INSERT.
2. If the upcoming statement is a `SELECT`, `UPDATE`, or `DELETE`, **skip** this skill entirely.

## Procedure (unchanged core logic)
1. **Parse the instruction** and extract every exact fragment that maps to a column (including spaces, hyphens, parentheses, units, adjectives).
2. **Match fragments to column names** from `DESCRIBE <table>` (using fuzzy match when needed).
3. **Construct the INSERT** using back‑ticked column names and the **exact captured strings** as literals.
4. **Verify**: after the INSERT, run a `SELECT` that retrieves the newly inserted row and compare each returned value byte‑for‑byte with the captured fragment.
5. Only after successful verification, call `commit_final_answer`.

## Example (unchanged)
```sql
-- Correct insertion preserving unit
INSERT INTO `public_transportation_lines` (`Line`,`Colour`,`Route`,`Length`,`Stations`)
VALUES ('Schottentour','yellow','tram','11.2km','20');
```
```sql
SELECT `Line`,`Colour`,`Route`,`Length`,`Stations`
FROM `public_transportation_lines`
WHERE `Line`='Schotten​tour' AND `Length`='11.2km';
```
If the SELECT returns the exact row, then:
```json
{"answers": ["row inserted with exact values"]}
```

## Failure Handling
- If any column value differs from the captured fragment, **re‑read** the instruction, adjust the INSERT, and re‑run the verification before committing.
- If a required column has no corresponding fragment, **do not insert a placeholder**; instead, prompt for clarification or abort.

## Tags
["insert", "add", "added", "new", "record", "entry", "mutation"]
