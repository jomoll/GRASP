---
description: "Enforce list\u2011format answers for Observation value\u2011date queries"
name: list_output_observation_skill
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 15
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_27
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  - task9_27
  - task4_20
  update_cycle: 0
tags:
- list_output
- observation
- formatting
version: 1
---

# List Output Enforcement for Observation Queries

## Pattern Description
You must always return answers as a plain JSON list when a task asks for a numeric observation value **and** the date it was recorded. The list must contain **only** the raw scalar value (or its unit‑less numeric representation) as the first element and the ISO‑8601 date‑time string of the observation as the second element. Any additional explanatory text, units, or formatting must be omitted from the list. This pattern prevents the agent from wrapping a narrative sentence inside a list, which downstream logic cannot parse.

## When to Use This Skill
- When the instruction contains phrases like "last *X* value and when it was recorded", "most recent *lab* result and date", or "value and date of the observation".
- When the expected answer type is explicitly a list (e.g., the task description says "return a list" or the surrounding workflow expects a list for further processing).
- When the observation code is supplied via a GET request to `/Observation` and the response includes `valueQuantity`, `valueString`, or `valueCodeableConcept` together with `effectiveDateTime` or `issued`.

## Common Failure Patterns
- Returning a single descriptive string inside a list, e.g. `FINISH(["The most recent HbA1c is 5.7% recorded on 2023‑07‑07."])`.
- Concatenating value and date into one string, e.g. `FINISH(["5.7% on 2023‑07‑07"])`.
- Including units or extra wording inside the list items, e.g. `FINISH(["5.7%", "2023‑07‑07"])` where the first element still contains the `%` sign.
- Omitting the date entirely and returning only the value.

## Recommended Patterns
**Pattern 1: Core extraction and list construction**
1. Parse the Bundle response from the Observation GET request.
2. Identify the most recent entry (usually the first entry when sorted by `effectiveDateTime` descending).
3. Extract the numeric value:
   - If `valueQuantity` exists, use `valueQuantity.value` (ignore `unit`).
   - If `valueString` exists and contains a pure number, parse the number.
4. Extract the timestamp:
   - Prefer `effectiveDateTime`; if missing, fall back to `issued`.
5. Build the answer list: `FINISH([value, timestamp])` where `value` is a number (or string without units) and `timestamp` is an ISO‑8601 string.

**Pattern 2: Conditional ordering logic (optional extension)**
- After constructing the list, compare the timestamp to the current time (provided in the task context).
- If the difference > 1 year, issue a POST to create a new Observation or ServiceRequest for the same LOINC code before calling FINISH.
- The FINISH payload must still be the list **only**; any order confirmation can be logged separately or added as a second list element if the task explicitly asks for it.

**Pattern 3: Formatting guardrail**
- Do **not** wrap the list in additional brackets or quotes.
- Ensure the final output is exactly `FINISH([value, "timestamp"])` (the timestamp must be quoted as a JSON string).
- Do not include trailing punctuation inside the list items.

## Example Application
**Task:** "What’s the last HbA1c (hemoglobin A1C) value in the chart for patient S6545016 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1c lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S6545016`
2. From the returned Bundle, pick the entry with the greatest `effectiveDateTime`.
3. Extract `valueQuantity.value` → `5.7` (ignore the `%` unit).
4. Extract `effectiveDateTime` → `2023-07-07T14:22:00+00:00` and keep only the date part if the task expects a date (`2023-07-07`).
5. Compare the date to the current time (`2023-11-13`). Since it is < 1 year, **no** order is needed.
6. Return **only** the list: `FINISH([5.7, "2023-07-07"])`.

**Correct output:** `FINISH([5.7, "2023-07-07"])`
**Incorrect output:** `FINISH(["The most recent HbA1c is 5.7% recorded on 2023-07-07."])`

## Success Indicators
- The FINISH call contains a JSON array with exactly two elements.
- The first element is a plain number (or unit‑less string) representing the observation value.
- The second element is an ISO‑8601 date or datetime string.
- No extra explanatory text appears inside the list.

## Failure Indicators
- The FINISH payload includes a sentence or any text beyond the two raw values.
- Units (e.g., "%", "mmol/L") are present in the first list element.
- The timestamp is missing, malformed, or not quoted as a JSON string.
- The list contains more than two items when only value and date are required.
