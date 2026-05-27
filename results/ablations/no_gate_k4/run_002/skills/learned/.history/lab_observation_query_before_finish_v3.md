---
description: "Handle empty Observation search results and return a scalar no\u2011\
  result message"
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task4_7
  - task2_30
  - task8_19
  - task9_22
  - task8_3
  - task8_21
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  update_cycle: 1
tags: []
version: 3
---

# lab_observation_query_before_finish

## Pattern Description
You must query for a specific lab Observation and, before finishing, ensure that the result is a **scalar string** that either contains the converted lab value or a clear "no recent result" message. The skill centralises the logic for detecting an empty FHIR Bundle, extracting the most recent value, converting units, and formatting the final FINISH payload as a plain string (not a JSON array). This prevents the agent from emitting placeholder lists like `["-1"]` which break downstream verification.

## When to Use This Skill
- When a task asks for the most recent value of a lab (e.g., magnesium, HbA1c) within a time window.
- When the task specifies a fallback value (e.g., `-1`) **or** a natural‑language no‑result sentence.
- Immediately after receiving a GET `/Observation` Bundle response.

## Common Failure Patterns
- `total: 0` but the agent still calls `FINISH(["-1"])` (list instead of scalar).
- Returning the placeholder string `"-1"` without checking whether the Bundle actually contains entries.
- Forgetting to convert the extracted `valueQuantity.value` to the required unit before finishing.
- Using the wrong field (`valueString` instead of `valueQuantity`).

## Recommended Patterns
**Pattern 1: Detect empty Bundle and emit scalar no‑result message**
1. Inspect `response.total` (or count of `entry`).
2. If `total == 0` **or** `entry` is missing, call:
   ```
   FINISH("No recent {code} result; no replacement ordered.")
   ```
   Replace `{code}` with the lab code from the request (e.g., `magnesium`).
3. Do **not** wrap the message in brackets or quotes that produce a list.

**Pattern 2: Extract and convert a present value**
1. Sort `entry` by `effectiveDateTime` descending and pick the first.
2. Extract `valueQuantity.value` (numeric) and `valueQuantity.unit`.
3. If the required output unit differs, apply conversion (e.g., mmol/L → mg/dL for magnesium: multiply by 2.03).
4. Build a scalar string containing only the numeric value **or** the value with unit if the task demands it, e.g.:
   ```
   FINISH("3.5")
   ```
   or
   ```
   FINISH("3.5 mg/dL")
   ```
5. Ensure the FINISH argument is a plain string, not an array.

**Pattern 3: Verification before finish**
- After constructing the FINISH payload, run the `verify_before_finish` rule implicitly: the argument must be a scalar string. If it is an array, raise an internal error and fallback to the no‑result message.

## Example Application
**Task:** "What’s the most recent magnesium level of patient S2937751 within last 24 hours?"

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=MG&patient=S2937751&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`
2. Receive Bundle with `total: 0`.
3. Apply Pattern 1 → `FINISH("No recent magnesium result; no replacement ordered.")`.

**CORRECT output:** `FINISH("No recent magnesium result; no replacement ordered.")`
**WRONG output:** `FINISH(["-1"])`

## Success Indicators
- FINISH is called with a plain string, never an array.
- For empty results the string contains the phrase "No recent … result".
- For present results the string contains only the numeric value (or value+unit) as required.

## Failure Indicators
- FINISH receives `[...]` (list) or a JSON object.
- The agent returns `"-1"` when the Bundle actually contains entries.
- Unit conversion is omitted or applied incorrectly, leading to mismatched units.
- The no‑result message is missing or malformed (e.g., empty string).
