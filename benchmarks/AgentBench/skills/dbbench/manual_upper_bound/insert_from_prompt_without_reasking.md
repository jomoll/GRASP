---
name: insert_from_prompt_without_reasking
description: When an INSERT task already provides the row values and headers, construct the INSERT directly instead of asking for more information.
tags:
- sql
- insert
- protocol
version: 1
---

# Summary
A recurring INSERT failure is refusing the task and asking for the "actual question" even though the prompt already specifies the row to insert.

## Trigger
The prompt states that data "was inserted" or instructs the agent to insert a row, and it includes the table name plus all headers and values.

## Failure Pattern
The agent responds with something like:
- "Please provide the question..."
- "I understand the schema, what would you like me to do?"
instead of issuing an `INSERT`.

## Action Rule
If the prompt gives the target table, headers, and row values, write the `INSERT` immediately. Do not ask clarifying questions unless a required value is truly missing.

## Verification Rule
Before writing the SQL, check that each provided value can be aligned to one header. If yes, proceed directly to `INSERT`.

## Do Not
- Do not ask the user to restate the task.
- Do not start with `SHOW TABLES` when the table name is already given.
- Do not convert an INSERT task into a QA task.

## Example Pattern
Wrong:
```text
I understand the database structure. Please provide the question you would like me to answer.
```

Correct:
```sql
INSERT INTO `population_data` (`Particulars`, `Total`, `Male`, `Female`) VALUES ('schools', '25', '15', '10');
```
