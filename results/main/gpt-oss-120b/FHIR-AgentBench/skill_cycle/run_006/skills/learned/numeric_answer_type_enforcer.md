---
description: Ensures numeric (int/float) answers for questions asking for averages,
  counts, differences, etc.
name: numeric_answer_type_enforcer
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 11
  failure_mode: answer_format_wrong_type
  fixes: 6
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - 0577ee51b3ad3c9fcf8fbbae
  - 072f960a91e48e6fe38d81a1
  - 0d22f4703425e474ebd63580
  update_cycle: 0
tags:
- answer_format
- numeric
version: 1
---

## When to use
Trigger this skill when the user question explicitly asks for a numeric result, such as:
- averages, means, or median values (e.g., "average oxygen level", "mean heart rate")
- counts or totals (e.g., "how many drugs", "number of ICU visits", "total volume")
- differences, deltas, or changes (e.g., "difference between the first and second measurement", "change in blood pressure")
- extrema (e.g., "maximum weight", "minimum systolic blood pressure")
- any phrasing that includes words like *average, mean, number, count, total, sum, difference, change, delta, max, minimum, highest, lowest*.
If the question does not request a numeric value, do not apply this skill.

## Procedure
1. **Detect numeric intent** – Scan the user instruction for the trigger keywords above. If none are found, skip the skill.
2. **Execute the normal retrieval/logic** – Let existing skills gather the required data and compute the raw answer.
3. **Validate answer type**
   - If the answer is already an `int` or `float`, accept it.
   - If the answer is a string that looks like a number (e.g., "42", "3.14", "45 kg"), attempt to parse the leading numeric component using a regular expression. Preserve any trailing unit after successful parsing.
   - If parsing fails, set the answer to `null` and raise a *format error*.
4. **Format the final answer**
   - For pure numbers, return the value with no surrounding quotes.
   - If a unit was extracted, return the string `<number> <unit>` (e.g., `45 kg`).
   - Do not prepend explanatory text; the answer must be the bare numeric representation.
5. **Log the enforcement** – Record that the numeric enforcer was applied for debugging.

## Checks
- **Answer type**: must be `int` or `float` (or a string that can be parsed into one).
- **Units**: if the original data includes a unit, it must be retained after parsing.
- **No extra wording**: the final output should contain only the numeric value (and optional unit), no sentences.
- **Scope**: only run on questions identified in *When to use*.

## Avoid
- Returning boolean strings (`"true"/"false"`) for numeric queries.
- Providing full sentences or explanations when a plain number is required.
- Dropping units that are part of the original measurement.
- Applying the skill to non‑numeric queries, which would corrupt legitimate textual answers.
