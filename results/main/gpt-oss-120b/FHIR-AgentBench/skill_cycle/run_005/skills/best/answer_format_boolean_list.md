---
description: "Convert Yes/No textual answers to a list of booleans and enforce the\
  \ expected list\u2011of\u2011bool type"
name: answer_format_boolean_list
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 15
  failure_mode: answer_format_wrong_type
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 0577ee51b3ad3c9fcf8fbbae
  update_cycle: 1
tags:
- format
- boolean
- list
version: 1
---

## When to use
You must invoke this skill whenever the question clearly expects a list of boolean values (e.g., "Did patient X receive medication A, B, or C?" or any "Yes/No" list) and the agent’s raw answer is a list of textual strings such as "Yes"/"No".

## Procedure
1. **Infer expected type** – Examine the question for patterns that imply a list of booleans (keywords like "any of", commas separating items, or explicit "Yes/No" phrasing).  
2. **Detect raw answer shape** – If the current answer is a Python `list` whose elements are strings, proceed; otherwise skip this skill.
3. **Normalize each element** – For each element `s` in the list:
   - `norm = s.strip().lower()`
   - Map `norm` to a boolean:
     - `{"yes", "true", "1"}` → `True`
     - `{"no", "false", "0"}` → `False`
   - If `norm` is not in the mapping, raise a format‑mismatch error so that `answer_fallback` can be triggered.
4. **Replace answer** – Substitute the original list with the new list of booleans.
5. **Single‑value fallback** – If the expected type is a list but the raw answer is a single Yes/No string, convert it to a one‑element boolean list.

## Checks
- Verify that the final answer is a `list` where **every** element is of type `bool`.
- Ensure the list length matches the number of items implied by the question (e.g., three medications → list length = 3).
- Confirm no string values remain; if conversion fails, abort and let `answer_fallback` produce a safe default.

## Avoid
- Converting non‑boolean answers (numeric, dates, free‑text) into booleans.
- Leaving mixed‑type lists (e.g., `[True, "No"]`).
- Applying the skill when the question expects a single boolean or a different datatype.
