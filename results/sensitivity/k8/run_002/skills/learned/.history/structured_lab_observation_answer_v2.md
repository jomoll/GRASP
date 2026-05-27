---
description: Add logic to output raw numeric sentinel for tasks that expect a single
  number instead of a structured object.
name: structured_lab_observation_answer
provenance:
  action: MODIFY
  epoch: 0
  fixes: 12
  parent_version: 1
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task4_26
  - task9_28
  - task5_17
  - task9_3
  - task8_21
  - task4_23
  - task9_27
  - task10_24
  - task8_9
  - task4_11
  update_cycle: 1
tags: []
version: 2
---

# Structured Lab Observation Answer

## Pattern Description
You must extract laboratory Observation results from FHIR bundles and return them in the format the task explicitly requests.  Most tasks need a structured object `{value, unit, date, order_placed}` but a subset of tasks explicitly state that the answer should be *a single number* (e.g., “answer should be a single number converted to mg/dL, and it should be -1 if a measurement within last 24 hours is not available”).  In those cases you must return only the numeric value (or the sentinel `-1`) and **not** the full structured object.

## When to Use This Skill
- When a task asks for a lab value and the instruction mentions returning separate fields (`value`, `unit`, `date`, etc.).
- When a task says the answer must be a *single number* or *just the value* (keywords: "single number", "just the value", "numeric answer", "should be -1 if not available").
- When the observation is missing or outside the required time window.

## Common Failure Patterns
- Returning a structured object (`{"value":-1,"unit":"mg/dL",...}`) for a task that expects only `-1` → `answer_format_wrong_type`.
- Propagating the sentinel `-1` inside a structured payload when the task expects a raw number.
- Forgetting to convert units before returning the raw number.

## Recommended Patterns
**Pattern 1: Determine required answer shape**
1. Scan the task description for any of the keywords: `"single number"`, `"just the value"`, `"numeric answer"`, `"should be -1"`.
2. If any keyword is present, set `output_mode = "raw"`; otherwise `output_mode = "structured"`.

**Pattern 2: Extract the most recent observation within the time window**
1. GET the Observation bundle with the appropriate `code` and `patient` parameters.
2. From each `entry.resource`, keep only those where `effectiveDateTime` (or `issued`) is within the last 24 hours.
3. Choose the observation with the greatest `effectiveDateTime`.
4. If none are found, set `value = -1` (raw mode) or `value = null` (structured mode).

**Pattern 3: Convert units and build the response**
- If the observation uses a different unit, convert to the target unit required by the task (e.g., mmol/L → mg/dL for magnesium: multiply by 2.0).
- **Raw mode**: `FINISH([numeric_value])` where `numeric_value` is the converted number or `-1`.
- **Structured mode**: `FINISH([{"value": numeric_value, "unit": "mg/dL", "date": "YYYY-MM-DDTHH:MM:SS+00:00", "order_placed": false}])`.

**Pattern 4: Fallback handling**
- If the Observation bundle is empty or malformed, treat as missing and apply the same missing‑value logic as above.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1733937 within last 24 hours? The answer should be a single number converted to a unit of mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step‑by‑step:**
1. Detect keyword *single number* → `output_mode = "raw"`.
2. GET `http://localhost:8080/fhir/Observation?code=MG&patient=S1733937`.
3. Parse bundle; no observation in the last 24 h → `value = -1`.
4. Because `output_mode` is raw, return `FINISH([-1])`.

**Correct output:** `FINISH([-1])`
**Wrong output:** `FINISH([{"value":-1,"unit":"mg/dL","date":null,"order_placed":false}])`

## Success Indicators
- The agent returns a plain number (or `-1`) for tasks that explicitly request a single numeric answer.
- Unit conversion is applied correctly before returning the number.
- Structured objects are only returned for tasks that ask for separate fields.

## Failure Indicators
- The agent returns a JSON object when the task description demanded a raw number.
- The sentinel `-1` appears inside a structured payload for a raw‑mode task.
- The returned number is in the wrong unit or not converted.
