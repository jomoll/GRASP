---
description: Guarantee that final answers are plain scalars with no surrounding text
name: enforce_output_type
provenance:
  baseline_fixes: 3
  baseline_regressions: 2
  epoch: 10
  failure_mode: answer_format_wrong_type
  fixes: 3
  parent_version: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - 02885cc1fb11efec74cb16fd
  - 074c7225bee20e2006c6db58
  - 09c4726f77bd8073eeb8d985
  update_cycle: 0
tags: []
version: 2
---

## When to use
You must invoke this skill whenever the user explicitly requests a single attribute (e.g., a date‑time, a numeric value, or a Yes/No answer). The expected answer is a plain scalar, not a sentence or phrase.

## Procedure
1. **Extract the raw value** using the appropriate retrieval/aggregation skill.
2. **Validate the type**:
   - If the question expects a date‑time, ensure the value parses with `datetime.fromisoformat` (allowing an optional timezone offset) and then re‑serialize with `isoformat()` **without** a trailing "Z" or extra whitespace.
   - If the question expects a number, coerce to `int` or `float` as appropriate.
   - If the question expects Yes/No, normalize to exactly `"Yes"` or `"No"` (capitalized, no punctuation).
3. **Strip any surrounding narrative**: remove leading/trailing words such as "The final answer is", "Answer:", or punctuation. The output should be exactly the scalar string produced in step 2.
4. **Return the scalar** as the sole content of the assistant's final message.

## Checks
- Confirm the output is a single token of the expected type (ISO‑8601 datetime, numeric, or Yes/No).
- Ensure no extra characters, whitespace, or explanatory text are present.
- Verify that the datetime is rounded to the hour if the question requires it, otherwise keep the original precision.
- If the value cannot be coerced to the expected type, fall back to a clear error message rather than an incorrectly formatted answer.

## Avoid
- Returning full sentences, prefixes, or suffixes around the answer.
- Including units (e.g., "kg", "mmHg") when the user asked for the raw value.
- Mixing multiple values into a single response when only one scalar is requested.
- Over‑aggressive extraction that silently drops the value; always either return a valid scalar or an explicit "None"/error.
