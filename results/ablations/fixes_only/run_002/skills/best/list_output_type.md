---
description: Ensures FINISH returns a plain list of separate strings rather than combined
  sentences.
name: list_output_type
provenance:
  action: ADD
  epoch: 0
  fixes: 12
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task5_19
  - task1_20
  - task9_5
  - task9_1
  - task10_8
  - task5_16
  - task9_28
  - task1_10
  - task10_20
  - task10_21
  update_cycle: 1
tags: []
version: 1
---

# List Output Type

## Pattern Description
You must always format the final answer as a JSON list where each required piece of information occupies its own string element. This prevents concatenating multiple data points (e.g., a lab value and its date) into a single sentence. The pattern applies to any task that asks for more than one distinct answer component, especially when the instruction mentions "value and when it was recorded" or similar phrasing.

## When to Use This Skill
- When the task asks for a lab/value **and** a date/time, e.g., "What’s the last HbA1c value and when was it recorded?".
- When the instruction explicitly says the answer should be a list or when the context includes a placeholder like `FINISH([])` expecting list items.
- When the response would naturally contain multiple independent fields (value, date, unit, status, etc.).

## Common Failure Patterns
- Returning a single combined string: `FINISH(["6.1% on 2023-10-13"])`.
- Adding extra explanatory text inside the list element: `FINISH(["The HbA1c is 6.1% recorded on 2023-10-13."])`.
- Omitting required elements, leaving the list empty or with the wrong count.

## Recommended Patterns
**Pattern 1: Separate extraction**
1. Identify each required field in the FHIR response.
   - Lab value: `valueQuantity.value` or `valueString` (include unit if present).
   - Result date: `effectiveDateTime` or `issued`.
2. Store each field in its own variable.
3. Build the FINISH payload with **one string per variable**.

   ```
   value_str = "6.1%"
   date_str = "2023-10-13"
   FINISH([value_str, date_str])
   ```

**Pattern 2: Fallback when a field is missing**
- If the date is missing, still return a list with the available value and a placeholder like `"unknown"`.
- If the value is missing, return `"N/A"` for that position.

**Pattern 3: Formatting rules**
- Do **not** add any extra words, punctuation, or explanations inside the list elements.
- Keep the value string exactly as it appears in the resource (including the unit symbol if present).
- Use ISO‑8601 date format (`YYYY-MM-DD`) for dates.

## Example Application
**Task:** "What’s the last HbA1c (hemoglobin A1C) value in the chart for patient S3114648 and when was it recorded?"

**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S3114648`.
2. From the most recent entry, extract:
   - `valueQuantity.value` = `6.1` and `valueQuantity.unit` = `%` → combine to `"6.1%"`.
   - `effectiveDateTime` = `2023-10-13T08:45:00Z` → keep date part `"2023-10-13"`.
3. Construct the output:
   ```
   FINISH(["6.1%", "2023-10-13"])
   ```

**Correct output:** `FINISH(["6.1%", "2023-10-13"])`
**Wrong output:** `FINISH(["6.1% on 2023-10-13"])`

## Success Indicators
- FINISH payload is a JSON array with one element per required answer piece.
- Each element is a plain string without extra wording.
- The number of elements matches the number of distinct data points requested.

## Failure Indicators
- FINISH contains a single concatenated string.
- List elements contain explanatory text or punctuation beyond the raw value.
- Missing elements or extra elements beyond what the task asked for.

---
*Tag: formatting, answer_structure*
