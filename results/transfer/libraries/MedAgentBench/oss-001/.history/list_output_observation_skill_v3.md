---
description: Enforce exact list length and field types for Observation answers
name: list_output_observation_skill
provenance:
  action: MODIFY
  epoch: 2
  fixes: 11
  parent_version: 2
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task5_19
  - task5_3
  - task10_10
  - task10_12
  - task9_1
  - task9_20
  - task9_22
  update_cycle: 1
tags: []
version: 3
---

# Observation List Output Formatting and Length Enforcement

## Pattern Description
You must ensure that any FINISH response for an Observation‑related task is a **compact list** containing **only the required primitive values**.  The list should include the observation value (or a placeholder such as `-1`) and, when the task explicitly asks for the measurement date, an ISO‑8601 datetime string.  No additional explanatory text, status messages, or extra elements are allowed.  This keeps the agent’s output predictable for downstream logic and prevents the "answer_list_separate_fields" regression.

## When to Use This Skill
- The task description mentions a lab/value/date, e.g., "most recent potassium level" or "last serum magnesium level within last 24 hours".
- The agent has just performed a GET on the `Observation` endpoint and is about to call `FINISH`.
- The expected answer format is a JSON list (e.g., `[value, "date"]` or `[-1]`).

## Common Failure Patterns
- `FINISH([3.8, "2023-11-12T12:23:00+00:00", "No potassium replacement needed"])` – extra explanatory string.
- `FINISH([5.9])` when the task also asked for the date.
- Returning a dictionary or nested list instead of a flat list of primitives.
- Omitting the date field when the task explicitly requests it.

## Recommended Patterns
**Pattern 1: Core list construction**
1. After parsing the Observation bundle, extract:
   - `valueQuantity.value` (or `valueString` parsed to a number) → `obs_value`.
   - `effectiveDateTime` → `obs_date`.
2. Determine the required shape from the task text:
   - If the text contains the word *date* or a phrase like "when was it recorded", the list must be `[obs_value, obs_date]`.
   - Otherwise a single‑element list `[obs_value]` is sufficient.
3. Validate:
   - List length matches the required shape (1 or 2).
   - All elements are primitives (`number` or ISO‑8601 `string`).
   - No extra strings or objects are present.
4. Call `FINISH` with the validated list.

**Pattern 2: Fallback when extraction fails**
- If the Observation bundle is empty or the required fields are missing, construct a placeholder list:
  - For value‑only tasks: `[-1]`.
  - For value‑and‑date tasks: `[-1, "" ]` (empty string for missing date).
- Immediately `FINISH` with the placeholder list.

**Pattern 3: Formatting guard**
- Before any `FINISH`, run a quick sanity check:
  ```python
  if not isinstance(answer, list) or not (1 <= len(answer) <= 2):
      raise AssertionError("Observation answer must be a list of 1 or 2 primitives")
  for el in answer:
      if not isinstance(el, (int, float, str)):
          raise AssertionError("Observation answer elements must be primitives")
  ```
- If the check fails, fall back to the placeholder list from Pattern 2.

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium. Also return the measurement date."

**Step‑by‑step:**
1. `GET http://.../Observation?code=K&patient=S6309742`
2. Parse the bundle, find the newest entry:
   - `valueQuantity.value` → `3.8`
   - `effectiveDateTime` → `"2023-11-12T12:23:00+00:00"`
3. Task asks for the date, so build `[3.8, "2023-11-12T12:23:00+00:00"]`.
4. Validate list length = 2 and element types.
5. `FINISH([3.8, "2023-11-12T12:23:00+00:00"])`

## Success Indicators
- `FINISH` output is a flat list of 1 or 2 items, all primitives.
- When a date is required, the second element is a correctly formatted ISO‑8601 string.
- No extra explanatory text appears in the list.

## Failure Indicators
- `FINISH` contains three or more elements.
- Any element is a dictionary, list, or contains free‑form sentences.
- Required date field is missing while the task mentions a date.
- The list includes placeholder text like "No potassium replacement needed".
