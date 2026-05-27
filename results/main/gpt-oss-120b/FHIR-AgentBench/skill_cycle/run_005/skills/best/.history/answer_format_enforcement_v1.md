---
description: Ensures the final answer matches the expected type (boolean, numeric,
  date, list, dict) inferred from the question.
name: answer_format_enforcement
provenance:
  baseline_fixes: 4
  baseline_regressions: 6
  epoch: 0
  failure_mode: answer_format_wrong_type
  fixes: 3
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - 00b98d0bf4d50497625b257e
  - 01389011a3cea028b226b95b
  - 017d9aef746962d1c3d9d52e
  - 02a069698a803a8419fa294c
  - 04572e0972a7993db0621881
  - 098b1301820b7d581a339d0f
  - 09b1b086d491d385b6744dd6
  - 0a43e2fe814473ab9035db70
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must invoke this skill for any FHIR query where the question implies a specific answer type (e.g., Boolean questions starting with *Was/Did/Has/Is*, numeric aggregations using *total/count/sum/average*, date queries using *When/What time*, list or dictionary responses, etc.). The skill runs after you have generated a raw answer but before you output it to the user.

## Procedure
1. **Infer expected type** from the instruction:
   - If the question begins with *Was*, *Did*, *Has*, *Is*, *Are*, or contains *any*, *none*, *boolean*, expect a **Boolean** answer represented as the strings `"Yes"` or `"No"`.
   - If the question contains words like *total*, *sum*, *count*, *number of*, *average*, *minimum*, *maximum*, *difference*, expect a **Numeric** answer (int or float).
   - If the question starts with *When*, *What time*, *date of*, or asks for a timestamp, expect a **DateTime** string in ISO‑8601 format (`YYYY-MM-DDThh:mm:ss±hh:mm`).
   - If the question asks for *list*, *all*, *first/last* items, expect a **List** (JSON array of strings or numbers).
   - If the question asks for a structured result (e.g., *difference*, *details*, *object*), expect a **Dictionary** (JSON object).
2. **Validate the generated answer**:
   - For **Boolean**: the answer must be a string exactly equal to `"Yes"` or `"No"` (case‑insensitive). If the raw answer is a Python `bool`, convert it to the appropriate string.
   - For **Numeric**: the answer must be an `int` or `float`. If the raw answer is a string that can be parsed as a number, convert it. If it is a complex object, extract the numeric field.
   - For **DateTime**: the answer must be a string that matches the ISO‑8601 pattern. If the raw answer is a `datetime` object, call `.isoformat()`. If it is a string in another format, attempt to parse with `dateutil.parser.isoparse` and re‑emit ISO format.
   - For **List**: the answer must be a Python list. If the raw answer is a comma‑separated string, split on commas, strip whitespace, and produce a list.
   - For **Dictionary**: the answer must be a dict. If the raw answer is a JSON‑encoded string, parse it.
3. **If validation fails**:
   - Attempt a sensible conversion as described above.
   - If conversion is impossible, raise an `answer_not_generated_exception` with a clear message (e.g., *"Cannot produce a numeric answer for the requested total"*).
4. **Output** the validated (or converted) answer in its proper JSON‑compatible form.

## Checks
- Confirm the inferred expected type matches the question intent.
- Verify the final answer is of the correct Python type **and** that its serialized form matches the required format (string for Boolean/DateTime, number for Numeric, list/dict for structured answers).
- Ensure no placeholder strings like *"No medication was prescribed..."* are returned when a date or numeric value is required.
- Preserve units only when explicitly requested; otherwise return the bare numeric value.

## Avoid
- Returning raw Python objects (e.g., `datetime` objects) without converting them to strings.
- Leaving Boolean answers as `True`/`False` instead of the required `"Yes"`/`"No"` strings.
- Outputting numbers inside a string (e.g., `"3075.0"`) when a numeric type is expected.
- Providing empty strings or `None` when the question demands a concrete value.
- Ignoring the inferred answer type and defaulting to a generic string.
