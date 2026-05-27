---
description: Enforce that the final answer matches the expected type (boolean, numeric,
  date, list, dict) inferred from the question.
name: answer_format_enforcement
provenance:
  baseline_fixes: 4
  baseline_regressions: 3
  epoch: 3
  failure_mode: answer_format_wrong_type
  fixes: 4
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 01389011a3cea028b226b95b
  - 0424a90b6986dc6ca2da8b3b
  - 0702bc77d929f78085010bb0
  update_cycle: 1
tags: []
version: 2
---

## When to use
You must invoke this skill for any question whose answer is expected to be a **single typed value** – e.g., a boolean (yes/no), a numeric amount, a date/time, or a structured list/dict. Detect the expected type from the question using keywords such as:
- **Date/Time**: "when", "date", "time", "last", "first", "since", "on", "occurred", "discharge", "admission", "test" together with a month/year pattern.
- **Numeric/Amount**: "how many", "total", "amount", "dose", "value", "difference", "minimum", "maximum", "average", "count", "sum", "difference in".
- **Boolean**: "did", "has", "was", "any", "ever", "occurred", "performed", "prescribed", "given" – typically answered with Yes/No.
- **List/Dict**: "list of", "all", "names of", "details of", "counts of", "distinct".
If the question does not contain any of these cues, default to a free‑form string answer.

## Procedure
1. **Infer Expected Type** – Scan the user question for the keyword sets above and set `expected_type` to one of `date`, `numeric`, `boolean`, `list`, `dict`, or `text`.
2. **Generate Answer** – Run the normal retrieval, filtering, and reasoning steps to produce a provisional answer `ans`.
3. **Validate Format** –
   - **date**: Accept ISO‑8601 strings (`YYYY-MM-DD` or `YYYY‑MM‑DDThh:mm:ss±hh:mm`). If `ans` is a sentence containing a date, extract the first ISO‑8601 substring. If none, mark as invalid.
   - **numeric**: Accept `int` or `float`. If `ans` is a worded number or contains extra text, strip non‑numeric characters and convert. If conversion fails, invalid.
   - **boolean**: Accept `True/False`, `Yes/No` (case‑insensitive). Normalize to `Yes`/`No`.
   - **list** / **dict**: Ensure the object is a JSON‑serializable list or dict. If the answer is a comma‑separated string, split into a list.
   - **text**: No validation needed.
4. **Re‑format or Fail** –
   - If validation succeeds, replace `ans` with the correctly formatted value.
   - If validation fails, **do not** return a free‑form explanation. Instead, return a brief error like `"Unable to determine a valid <type> answer."` so the higher‑level controller can retry or report failure.
5. **Proceed to Output** – Send the validated (or error) answer to the user.

## Checks
- Confirm the inferred `expected_type` matches the question intent.
- For **date** answers: must be a proper ISO‑8601 string; timezone offset optional.
- For **numeric** answers: must be a JSON number (no surrounding quotes).
- For **boolean** answers: must be exactly `"Yes"` or `"No"` (case‑preserved).
- For **list/dict** answers: must be valid JSON structures, not plain sentences.
- Ensure the answer pertains to the resources queried (hospital encounters, observations, etc.) and does not contain unrelated explanatory text.

## Avoid
- Returning full sentences like "No calcium, total test was performed…" when the question expects a datetime.
- Leaving units or extra wording in numeric answers (e.g., "5 mg" instead of `5`).
- Providing boolean answers as "True"/"False" when the user expects "Yes"/"No".
- Supplying an empty string or `null` when a typed answer is required; instead return a clear "Unable to determine …" message.
- Ignoring the inferred type and falling back to free‑form text.
