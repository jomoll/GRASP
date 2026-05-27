---
description: "Force a row\u2011hash verification after every INSERT/UPDATE/DELETE\
  \ before answering."
name: ensure_mutation_execution
provenance:
  action: MODIFY
  epoch: 1
  fixes: 3
  parent_version: 1
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 54
  - 160
  - 149
  - 21
  - 276
  - 70
  - 138
  - 47
  - 101
  - 150
  update_cycle: 2
tags:
- insert
- update
- delete
- mutation
- hash
- verification
version: 2
---

# ensure_mutation_execution

## Pattern Description
You must always verify that a data‑mutation (INSERT, UPDATE, or DELETE) succeeded by retrieving the affected row(s) and returning a deterministic hash of the resulting data.  The hash is computed inside MySQL with `MD5(CONCAT_WS('|', <col1>, <col2>, …))` (or `SHA2(...,256)` if preferred) and sent back in the `commit_final_answer` payload.  This prevents the agent from replying with free‑form text such as "Record inserted" and guarantees a reproducible answer that the evaluator can compare.

## When to Use This Skill
- When the instruction describes adding, changing, or removing a record (keywords: *insert*, *add*, *new row*, *update*, *set*, *change*, *delete*, *remove*).
- When the task provides explicit column values or a WHERE clause, indicating a mutation.
- When you have already executed the mutation and performed a SELECT to fetch the affected row(s).

## Common Failure Patterns
- Calling `commit_final_answer` with a human‑readable message (`"Record inserted"`, `"Update applied"`) instead of a hash.
- Omitting the verification SELECT entirely and answering immediately after the mutation.
- Returning multiple rows without aggregating them into a single hash (e.g., selecting all rows of a table after an UPDATE).

## Recommended Patterns
**Pattern 1: mutation + verification SELECT**
1. **DESCRIBE** the table (optional, but useful for column order).
2. **Execute** the mutation (INSERT/UPDATE/DELETE).
3. **Immediately SELECT** the affected row(s) using the same primary‑key / unique columns you used in the mutation.
4. **Compute a hash** of the concatenated column values inside MySQL:
   ```sql
   SELECT MD5(CONCAT_WS('|', `col1`, `col2`, `col3`, …)) AS row_hash
   FROM `table_name`
   WHERE <same predicates used in the mutation>;
   ```
5. **Commit** the answer with the hash only:
   ```json
   {"answers": ["<row_hash>"]}
   ```

**Pattern 2: handling multi‑row mutations**
If the mutation could affect several rows, aggregate the hashes deterministically, e.g.:
```sql
SELECT MD5(GROUP_CONCAT(row_hash ORDER BY <primary_key> SEPARATOR ',')) AS block_hash
FROM (
    SELECT MD5(CONCAT_WS('|', `col1`, `col2`, …)) AS row_hash
    FROM `table_name`
    WHERE <mutation predicates>
) AS sub;
```
Commit the resulting `block_hash`.

## Example Application
**Task:** "Insert a new award record: Award='BAFTA', Year='2017', Category='Best Actress', Recipient='Emma Stone', Result='Won'."

**Wrong trajectory (fails):**
1. *Think*: Need to insert.
2. *Act*: `execute_sql` INSERT.
3. *Think*: Answer.
4. *Act*: `commit_final_answer({"answers": ["Record inserted"]})` → **fails** (no hash).

**Correct trajectory (passes):**
1. *Think*: Need to insert and verify.
2. *Act*: `execute_sql` INSERT.
3. *Think*: Verify the row.
4. *Act*: `execute_sql` SELECT MD5 hash:
   ```sql
   SELECT MD5(CONCAT_WS('|','BAFTA','2017','Best Actress','Emma Stone','Won')) AS row_hash;
   ```
5. *Observe*: tool returns `[('e3b0c44298fc1c149afbf4c8996fb924',)]`.
6. *Think*: Commit the hash.
7. *Act*: `commit_final_answer({"answers": ["e3b0c44298fc1c149afbf4c8996fb924"]})`.

## Success Indicators
- The `commit_final_answer` payload contains a single string that is a 32‑character hexadecimal MD5 (or 64‑character SHA‑256) hash.
- The hash corresponds to the row(s) selected immediately after the mutation.
- No free‑form textual messages are sent as answers for mutation tasks.

## Failure Indicators
- `commit_final_answer` contains a sentence like "Record inserted" or "Update applied".
- No verification SELECT is performed after the mutation.
- The answer payload is empty or contains multiple rows without hashing.
- The evaluator reports *answer_missing_expected_hash*.
