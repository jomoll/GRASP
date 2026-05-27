---
name: use_prompt_headers_as_column_mapping_for_insert
description: For INSERT tasks, map values to the exact provided headers in prompt order unless the database proves otherwise.
tags:
- sql
- insert
- schema
version: 1
---

# Summary
Several insert tasks already tell the agent the exact header list. The safest move is to use those headers directly rather than paraphrasing or renaming them.

## Trigger
The task says "the headers of this table are ..." and then gives the values to insert.

## Failure Pattern
The agent paraphrases a header, drops a field, or normalizes punctuation:
- `Activators ligands --> Gq-GPCRs` instead of `Activators ligands -- > G q - GPCRs`
- partial column list
- reordered values

## Action Rule
Build the `INSERT` using the exact header strings from the prompt, in the same order, with backticks around each one.

## Verification Rule
Before emitting SQL, do a one-pass alignment:
1. Count headers.
2. Count values.
3. Ensure each value has a slot.
If counts align, emit the insert directly.

## Do Not
- Do not "clean up" punctuation in header names.
- Do not infer shorter aliases for columns.
- Do not reorder values unless the prompt explicitly pairs them by name.

## Example Pattern
Wrong:
```sql
INSERT INTO `Smooth Muscle Cell Activation Table` (`Cell type`, `Organ/system`, `Activators ligands --> Gq-GPCRs`, `Effects`) VALUES (...);
```

Correct:
```sql
INSERT INTO `Smooth Muscle Cell Activation Table` (`Cell type`, `Organ/system`, `Activators ligands -- > G q - GPCRs`, `Effects`) VALUES (...);
```
