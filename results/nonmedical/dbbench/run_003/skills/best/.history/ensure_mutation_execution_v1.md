---
description: Force the agent to perform and verify INSERT/UPDATE/DELETE before answering.
name: ensure_mutation_execution
provenance:
  action: ADD
  epoch: 0
  fixes: 6
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - 36
  - 25
  - 71
  - 108
  - 107
  - 253
  - 145
  - 75
  - 275
  - 45
  update_cycle: 2
tags: []
version: 1
---

# Ensure Mutation Execution for INSERT/UPDATE/DELETE Tasks

## Pattern Description
You must treat any instruction that explicitly asks to add, insert, update, change, set, modify or delete a row as a *mutation* task. Before you ever call `commit_final_answer` you must (1) construct the appropriate `INSERT`, `UPDATE` or `DELETE` statement, (2) execute it with `execute_sql`, (3) run a targeted `SELECT` to verify the change, and only then call `commit_final_answer`. Skipping the mutation or answering after only a `SELECT` is a failure.

## When to Use This Skill
- The user instruction contains verbs like **add**, **insert**, **new record**, **update**, **change**, **set**, **modify**, **delete**, **remove** followed by column names or values.
- The task description includes a list of column/value pairs (e.g., "Insert 'Sydney …' with Country='Australia', City='Sydney'") or an explicit `SET` clause for an update.
- The instruction does **not** ask for a pure query (no words such as *how many*, *list*, *show* without mutation keywords).

## Common Failure Patterns
- Executing only a `SELECT` and then calling `commit_final_answer` (mutation missing).
- Running a `SELECT` to check existence and then answering "No" without actually inserting the row.
- Answering with a textual statement instead of using `commit_final_answer` after a mutation.
- Forgetting to verify the mutation with a `SELECT` before answering.

## Recommended Patterns
**Pattern 1: Identify mutation type**
1. Scan the instruction for mutation keywords.
2. Decide whether the operation is `INSERT`, `UPDATE`, or `DELETE`.
3. Record the target table name.

**Pattern 2: Schema discovery**
```sql
DESCRIBE `table_name`;
```
Use the result to order columns correctly and to know which columns need back‑ticks.

**Pattern 3: Build and run the mutation**
- **INSERT**
```sql
INSERT INTO `table_name` (`col1`, `col2`, ...) VALUES ('val1', 'val2', ...);
```
- **UPDATE**
```sql
UPDATE `table_name` SET `colA`='valA', `colB`='valB' WHERE `primary_key`='key';
```
- **DELETE**
```sql
DELETE FROM `table_name` WHERE `primary_key`='key';
```
Execute the statement with `execute_sql`.

**Pattern 4: Verify the change**
Run a focused `SELECT` that should return the affected row(s).
```sql
SELECT * FROM `table_name` WHERE <same condition used in UPDATE/DELETE>;
```
Observe the result – it must contain the new/changed data.

**Pattern 5: Commit the answer**
Only after a successful verification call:
```json
commit_final_answer({"answers": ["<short confirmation message>"]})
```
The payload should be a list, even if the answer is a single word.

## Example Application
**Task (failure example):**
> "The `Location Listing` includes the `Name` 'Central Park', the `Location` '59th to 110th Street', the `City` 'New York City', and the `Listing date` 'July 21, 1858'."

**Wrong trajectory (what the skill prevents):**
1. *Think*: The instruction mentions values, but I treat it as a query.
2. *Act*: `execute_sql({"query": "SELECT * FROM `Location Listing` WHERE ..."})`
3. *Obs*: No rows returned.
4. *Think*: Answer "No".
5. *Act*: `commit_final_answer({"answers": ["No"]})`
*Result*: No INSERT performed – mutation missing.

**Correct trajectory (skill applied):**
1. *Think*: The instruction uses "includes" and provides full column/value set → mutation (INSERT).
2. *Act*: `execute_sql({"query": "DESCRIBE `Location Listing`;"})`
3. *Obs*: Column list returned.
4. *Think*: Build INSERT with back‑ticked columns.
5. *Act*: `execute_sql({"query": "INSERT INTO `Location Listing` (`Name`,`Location`,`City`,`Listing date`) VALUES ('Central Park','59th to 110th Street','New York City','July 21, 1858');"})`
6. *Obs*: MySQL reports 1 row affected.
7. *Think*: Verify insertion.
8. *Act*: `execute_sql({"query": "SELECT * FROM `Location Listing` WHERE `Name`='Central Park' AND `Location`='59th to 110th Street' AND `City`='New York City' AND `Listing date`='July 21, 1858';"})`
9. *Obs*: Row returned with exact values.
10. *Think*: Mutation succeeded, answer succinctly.
11. *Act*: `commit_final_answer({"answers": ["Record inserted"]})`

## Success Indicators
- The agent executes an `INSERT`, `UPDATE` or `DELETE` before any `commit_final_answer`.
- A verification `SELECT` is performed and returns the expected row.
- The final answer is sent via `commit_final_answer` with a list payload.

## Failure Indicators
- The agent calls `commit_final_answer` after only a `SELECT`.
- No mutation SQL appears in the trace for a task that contains mutation keywords.
- The final answer is plain text inside the assistant message rather than a tool call.

---
*Tags*: ["insert", "add", "update", "change", "modify", "delete", "mutation"]
