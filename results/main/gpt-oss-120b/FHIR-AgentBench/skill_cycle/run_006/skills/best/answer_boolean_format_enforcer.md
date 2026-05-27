---
description: Enforces boolean type for yes/no questions instead of string answers.
name: answer_boolean_format_enforcer
provenance:
  baseline_fixes: 1
  baseline_regressions: 2
  epoch: 4
  failure_mode: answer_format_wrong_type
  fixes: 3
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - 05a0dd22ccfcd8bac854d247
  - 074c7225bee20e2006c6db58
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill for any question that asks a binary yes/no about a patient (e.g., "Did patient X have ...?", "Has patient Y been given any ...?"). The expected answer type is a Boolean, not a string.

## Procedure
1. After your normal retrieval, filtering, and reasoning steps, you will have an intermediate answer that may be a string like "Yes", "No", "True", "False" (case‑insensitive, possibly with surrounding whitespace).
2. Normalize the intermediate answer:
   - Strip surrounding whitespace.
   - Convert to lower‑case.
3. Map the normalized value to a Boolean:
   - If it matches any of `"yes"`, `"true"`, `"1"`, set the answer to `true`.
   - If it matches any of `"no"`, `"false"`, `"0"`, set the answer to `false`.
   - If it does not match any of the above, raise a format error – the question expects a Boolean answer.
4. Return **only** the Boolean value (`true` or `false`) as the final answer; do not include any explanatory text.

## Checks
- Verify the original question is a yes/no style query.
- Ensure the final answer is a native Boolean (`true`/`false`), not a quoted string.
- Confirm no extra characters or whitespace are present.
- If the answer cannot be mapped, abort and report a format‑type failure.

## Avoid
- Returning "Yes"/"No" strings or any other textual representation.
- Adding explanatory phrases such as "The answer is Yes".
- Applying this skill to non‑binary questions (e.g., numeric, date, or free‑text answers).
