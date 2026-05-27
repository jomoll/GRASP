---
description: "Guarantee a safe fallback answer when no result is found to prevent\
  \ undefined\u2011answer errors."
name: answer_fallback
provenance:
  baseline_fixes: 1
  baseline_regressions: 4
  epoch: 8
  failure_mode: answer_not_generated_exception
  fixes: 4
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - 01bb1845215fb7cc77678534
  - 0702bc77d929f78085010bb0
  - 0a36ca6e9f221dc69fc7f8de
  - 0a8c46b684e72300d29c18aa
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill when the question expects a concrete answer (date, value, name, etc.) but the retrieved FHIR resources contain no matching entries, causing the answer variable to be undefined or `None` and potentially raising an exception.

## Procedure
1. **After all retrieval, filtering and reasoning steps** – just before returning the final answer – check whether the variable `answer` exists in the current Python execution context.
2. If `answer` is not defined, or its value is `None`, assign a generic fallback string appropriate to the query type:
   - For existence‑type questions (e.g., *"Has patient X had any lab test?"*), set `answer = "No"`.
   - For date/value/name queries, set `answer = "No data found"` (or a more specific phrase like "No matching observation found" if the skill can infer the resource type from the question).
3. Ensure the fallback answer conforms to the expected answer format (string, boolean, numeric, list, or dict) inferred from the question. If the expected type is boolean, use `False` instead of a string.
4. Proceed to the **answer_format_enforcement** skill (or any formatting checks) with this guaranteed `answer` value.

## Checks
- Verify that the `answer` variable is now defined and not `None`.
- Confirm the fallback matches the expected answer type (e.g., boolean for yes/no questions, string for dates/names, numeric for quantities, list/dict for collections).
- Ensure the fallback message is concise and does not expose internal debugging details.

## Avoid
- Returning Python `None` or leaving the `answer` variable unset, which leads to `answer_not_generated_exception`.
- Using overly specific fallback text that may mislead the user; keep it generic unless the question clearly demands a particular phrasing.
- Forgetting to re‑run the **answer_format_enforcement** step after setting the fallback, which could still cause type mismatches.
