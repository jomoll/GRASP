---
name: mutation_execute_then_stop
description: After a valid INSERT or UPDATE executes and is verified, stop issuing extra SQL and submit a minimal tool answer.
tags:
- sql
- mutation
- protocol
version: 1
---

# Summary
Many mutation failures come from post-mutation behavior, not the mutation itself: extra unsupported SQL, malformed follow-up, or drifting into prose.

## Trigger
A mutation task has just executed without a SQL syntax or runtime error.

## Failure Pattern
The agent performs the correct `INSERT` or `UPDATE`, then:
- adds extra exploratory SQL,
- tries unsupported functions,
- writes long natural-language confirmation,
- or otherwise corrupts a potentially correct trajectory.

## Action Rule
After one successful mutation statement and one targeted verification SELECT,
end the interaction by calling `commit_final_answer` with:
`{"answers": ["done"]}`

Use additional SQL only if the mutation itself clearly failed.

## Verification Rule
Use one targeted `SELECT` to verify the row or field that was changed. Do not
invent DB-specific verification functions or extra bookkeeping.

## Do Not
- Do not call SQL functions like `MD5(...)` to calculate benchmark hashes.
- Do not summarize the change in prose.
- Do not run broad exploratory SQL after the targeted verification query.

## Example Pattern
Wrong:
```sql
UPDATE `Actress Filmography` SET `Year` = '2010', `Notes` = 'romantic comedy' WHERE `Title` = 'Jumping the Broom';
SELECT * FROM `Actress Filmography` WHERE `Title` = 'Jumping the Broom';
```

Correct:
```sql
UPDATE `Actress Filmography` SET `Year` = '2010', `Notes` = 'romantic comedy' WHERE `Title` = 'Jumping the Broom';
```

Then:
```text
commit_final_answer({"answers": ["done"]})
```
