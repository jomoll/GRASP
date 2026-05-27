---
description: "Ensures the final answer is a plain scalar (string, number, date\u2011\
  time, or Yes/No) when the user explicitly requests a single attribute, while avoiding\
  \ over\u2011aggressive extraction that can corrupt correct answers."
name: enforce_output_type
provenance:
  baseline_fixes: 1
  baseline_regressions: 4
  epoch: 9
  failure_mode: answer_format_wrong_type
  fixes: 6
  probe_score: 8
  regressions: 1
  triggering_sample_ids:
  - 03d470fc8e41f5dd8568f771
  - 0702bc77d929f78085010bb0
  - 074c7225bee20e2006c6db58
  - 0cd11d35e8ac3515e3c55d6c
  update_cycle: 1
tags: []
version: 1
---

## When to use
Invoke this skill **only** when the user query clearly asks for a single attribute (e.g., a medication name, organism, date/time, numeric value, or a Yes/No answer) **and** the provisional answer (`answer`) is a composite Python object (list or dict).

## Procedure
1. **Determine the expected scalar type** from the query keywords:
   - *String* (medication/organism/etc.) → look for words like `medication`, `drug`, `organism`, `culture`, `specimen`.
   - *Date‑time* → words `date`, `time`, `when`, `first`, `last`.
   - *Numeric* → words `value`, `amount`, `difference`, `count`, `total`, `average`, `minimum`, `maximum`.
   - *Yes/No* → yes/no phrasing (`has`, `did`, `was`, `any`, `count of visits`, etc.).
2. **Check the provisional answer**:
   - If `answer` is **not** a list or dict, **do nothing** – the answer is already a scalar.
   - If `answer` is a list with a **single scalar element**, unwrap it and use that element.
   - If `answer` is a dict, continue to step 3.
3. **Extract the primary field** **only from a predefined whitelist** of keys that match the expected type:
   - For *string* answers: `medication`, `med_name`, `drug_name`, `organism`, `title`.
   - For *date‑time* answers: `date`, `authoredOn`, `performedDateTime`, `effectiveDateTime`, `effectivePeriod` (the `start` sub‑field).
   - For *numeric* answers: `value`, `count`, `difference`, `quantity`, `valueQuantity` (the `value` sub‑field).
   - For *Yes/No* answers: `boolean`, `valueBoolean`.
   - **Do not** fall back to any other keys (e.g., `code`, `id`, `reference`). If none of the whitelisted keys are present, **leave the answer unchanged**.
4. **Normalize the extracted value**:
   - Strip surrounding whitespace.
   - Dates → format as `YYYY‑MM‑DDTHH:MM:SS` (no timezone offset).
   - Numbers → ensure they are returned as a JSON number, not a quoted string.
   - Yes/No → convert booleans or "True"/"False" strings to exactly `"Yes"` or `"No"`.
5. **If extraction fails** (no whitelisted key found), **do not replace** the original answer; propagate it unchanged so downstream logic can decide how to handle the missing data.

## Checks
- Confirm the final answer is a single scalar of the expected type.
- Verify date strings are ISO‑8601 without timezone information.
- Ensure numeric answers are not quoted.
- Ensure Yes/No answers are capitalised exactly as `"Yes"` or `"No"`.

## Avoid
- Over‑writing a correct scalar answer with a generic message.
- Extracting unrelated fields such as `code`, `id`, or any nested object that is not in the whitelist.
- Returning the original composite structure when a scalar is required.
- Adding trailing whitespace or timezone information to dates.
- Guessing a value when the required field cannot be found; simply leave the answer unchanged.
