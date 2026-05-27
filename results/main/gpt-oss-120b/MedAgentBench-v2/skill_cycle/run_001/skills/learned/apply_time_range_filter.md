---
description: Add date range filters to Observation queries for recent period calculations
name: apply_time_range_filter
provenance:
  action: ADD
  epoch: 2
  fixes: 4
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task8_7
  - task8_29
  - task1_10
  - task3_30
  - task8_23
  - task3_1
  - task3_12
  - task4_11
  - task3_17
  - task6_2
  update_cycle: 0
tags:
- time_filter
- observation
- average
version: 1
---

# Apply Time Range Filters for Recent Observation Queries

## Pattern Description
You must always restrict Observation searches to the time window that the task explicitly requests.  When a clinical instruction asks for a value "over the past N hours" (or days, weeks, etc.), the query should include `date=ge` (greater‑or‑equal) and `date=le` (less‑or‑equal) parameters that are calculated relative to the current time supplied in the task context.  This prevents the agent from averaging all historic measurements, which leads to incorrect clinical decisions.

## When to Use This Skill
- When a task asks for an average, maximum, minimum, or any aggregate of a vital sign or lab value over a recent period (e.g., "past 6 hours", "last 12 months").
- When the instruction mentions a relative time phrase such as "past X hours", "last Y days", "within the previous week".
- When the task provides a "Current time" value in the context that can be used as the reference point for the filter.

## Common Failure Patterns
- Query missing any `date` parameter, returning the full history (e.g., `GET .../Observation?code=HEARTRATE&patient=...`).
- Using a static absolute date (e.g., `date=2023-01-01`) instead of a relative calculation.
- Adding only a lower bound (`date=ge`) but forgetting the upper bound (`date=le`), which can include future‑dated placeholder entries.
- Computing the window incorrectly (e.g., 6 hours instead of 12 hours) due to mis‑parsing the instruction.

## Recommended Patterns
**Pattern 1: Core strategy – build a relative date filter**
1. Parse the instruction to extract the numeric duration and unit (hours, days, weeks, months).
2. Retrieve the `Current time` value from the task context (ISO‑8601 string).
3. Compute `start = CurrentTime - duration` and `end = CurrentTime`.
4. Format the dates as `YYYY-MM-DDThh:mm:ss+00:00` (preserve timezone if present).
5. Append both parameters to the Observation GET URL:
   ```
   GET /fhir/Observation?code=HEARTRATE&patient=XYZ&date=ge{start}&date=le{end}
   ```
   **CORRECT** example:
   `GET http://localhost:8080/fhir/Observation?code=HEARTRATE&patient=S6315806&date=ge2023-11-07T16:47:00+00:00&date=le2023-11-07T22:47:00+00:00`
   **WRONG** example (no filter):
   `GET http://localhost:8080/fhir/Observation?code=HEARTRATE&patient=S6315806`

**Pattern 2: Fallback – verify the response contains at least one entry within the window**
- After the GET, scan the returned `Bundle.entry` objects.
- For each Observation, compare its `effectiveDateTime` (or `issued`) to the computed window.
- If **no** entry falls inside the window, treat the result as "no data for the requested period" and report accordingly instead of using unrelated older data.

**Pattern 3: Formatting the final answer**
- Compute the average only from the filtered observations.
- Return a concise FINISH payload:
  ```
  FINISH(["Average heart rate over the past 6 hours: 77 bpm; Average heart rate over the past 12 hours: 81 bpm"])
  ```
- Do **not** embed explanatory text or the raw timestamp list inside the FINISH array.

## Example Application
**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6315806."

**Step‑by‑step:**
1. Extract `Current time = 2023-11-07T22:47:00+00:00` from the context.
2. Compute windows:
   - 6‑hour window start = `2023-11-07T16:47:00+00:00`
   - 12‑hour window start = `2023-11-07T10:47:00+00:00`
3. Issue two GET requests (or a single request with a broader window and filter locally):
   ```
   GET http://localhost:8080/fhir/Observation?code=HEARTRATE&patient=S6315806&date=ge2023-11-07T10:47:00+00:00&date=le2023-11-07T22:47:00+00:00
   ```
4. From the returned bundle, separate observations into the two sub‑windows and compute each average.
5. Construct the FINISH output exactly as shown in Pattern 3.

**CORRECT output:**
`FINISH(["Average heart rate over the past 6 hours: 77 bpm; Average heart rate over the past 12 hours: 77 bpm"] )`

## Success Indicators
- The GET URL includes both `date=ge` and `date=le` parameters.
- The agent reports "no data" only when the filtered bundle contains zero entries for the requested window.
- The FINISH payload contains only the numeric averages and unit, no extra narrative.

## Failure Indicators
- The GET request omits any `date` filter or uses a static date unrelated to the current time.
- The agent averages values that fall outside the computed window.
- The FINISH output includes explanatory sentences or raw timestamps instead of the concise average string.

---
*Apply this skill before any aggregation of Observation data that is scoped to a recent time period.*
