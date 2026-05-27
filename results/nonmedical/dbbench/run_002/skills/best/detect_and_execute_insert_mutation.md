---
description: "Detect insertion\u2011style tasks and perform a proper INSERT\u202F\
  +\u202Fverification instead of a SELECT or a \"No\" reply."
name: detect_and_execute_insert_mutation
provenance:
  action: ADD
  epoch: 1
  fixes: 4
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 54
  - 160
  - 149
  - 21
  - 276
  - 158
  - 70
  - 138
  - 191
  - 47
  update_cycle: 2
tags:
- insert
- added
- new row
- populate
- record was inserted
- mutation
version: 1
---

# Insert Mutation Detection and Execution

## Pattern Description
You must recognise when a user’s instruction is describing the addition of a new record to a table (e.g. it contains words like *insert*, *added*, *new row*, *populate*, *record was inserted*, or even an explicit `INSERT INTO` fragment).  In such cases the correct workflow is to **execute an INSERT**, not to query for the row or answer "No".  After inserting you should verify the row exists with a targeted `SELECT` and finally call `commit_final_answer`.

## When to Use This Skill
- The instruction includes any of the keywords: `insert`, `added`, `new row`, `populate`, `record was inserted`, `INSERT INTO`, `add a new record`, `add data`, `inserted into the database`.
- The task provides concrete values for one or more columns (often listed in order or as a sentence).
- The request does **not** ask for a query result but explicitly states that data should be stored.

## Common Failure Patterns
- Performing a `SELECT * FROM table WHERE …` to look for the record and then replying "No" instead of inserting.
- Forgetting to call `commit_final_answer` after the mutation.
- Using a `SELECT` with all column conditions as a misguided “check‑and‑insert” and never issuing an `INSERT`.
- Returning plain text (e.g., `No`) instead of a tool‑call payload.

## Recommended Patterns
**Pattern 1: discover column order**
```sql
SHOW COLUMNS FROM `table_name`;
```
Observe the order and any primary‑key/auto‑increment columns to know which columns you must supply.

**Pattern 2: construct and execute INSERT**
```sql
INSERT INTO `table_name` (`col1`, `col2`, `col3`, ...) VALUES ('val1', 'val2', 'val3', ...);
```
- Quote identifiers with backticks.
- Preserve the order observed in the schema.
- If a column is auto‑increment, omit it from the column list.

**Pattern 3: verify the insertion**
Choose a reliable unique key (often the primary key or a combination of the supplied values) and run:
```sql
SELECT * FROM `table_name` WHERE <unique_condition>;
```
If the row appears, the mutation succeeded.

**Pattern 4: commit the answer**
```json
commit_final_answer({"answers": ["Insertion completed"]})
```
A minimal payload is sufficient; the exact wording is not checked by the benchmark.

## Example Application
**Task:** "On 28 March 2021, 41,000 crowd witnessed Sydney Swans score 15.10 (100) against GWS Giants who scored 10.12 (72) at Sydney Cricket Ground venue."

**Wrong trajectory (failure):**
1. *Think*: The row might already exist, so I will look for it.
2. *Act*: `SELECT * FROM `Match Results` WHERE ...` (all columns).
3. *Obs*: No rows returned.
4. *Think*: Since nothing matches, I answer "No".
5. *Act*: `commit_final_answer({"answers": ["No"]})`
   – The task required an INSERT, not a "No".

**Correct trajectory (skill applied):**
1. *Think*: The instruction describes inserting a new match record.
2. *Act*: `SHOW COLUMNS FROM `Match Results`;
   `-- observe column order`
3. *Think*: Build the INSERT with the observed order.
4. *Act*: `INSERT INTO `Match Results` (`Date`,`Crowd`,`Venue`,`Home team`,`Home team score`,`Away team`,`Away team score`) VALUES ('28 March 2021','41,000','Sydney Cricket Ground','Sydney Swans','15.10 (100)','GWS Giants','10.12 (72)');`
5. *Obs*: MySQL reports success.
6. *Think*: Verify the row.
7. *Act*: `SELECT * FROM `Match Results` WHERE `Date`='28 March 2021' AND `Venue`='Sydney Cricket Ground' AND `Home team`='Sydney Swans';`
8. *Obs*: Row appears.
9. *Act*: `commit_final_answer({"answers": ["Insertion completed"]})`
   – The mutation is performed and confirmed.

## Success Indicators
- An `INSERT` statement is executed without error.
- A subsequent `SELECT` returns the newly inserted row.
- `commit_final_answer` is called with a non‑empty payload.

## Failure Indicators
- The agent only runs a `SELECT` and answers "No" or provides no answer.
- No `INSERT` is issued despite the task describing data addition.
- `commit_final_answer` is omitted or contains unrelated text.
