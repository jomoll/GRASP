---
description: "Calculate averages for a vital sign over separate recent time windows\
  \ (e.g., 6\u202Fh and 12\u202Fh)."
name: average_vital_sign_over_multiple_windows
provenance:
  action: ADD
  epoch: 1
  fixes: 7
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task3_10
  - task3_30
  - task1_13
  - task8_29
  - task3_16
  - task6_26
  - task3_29
  - task8_23
  - task2_15
  - task3_17
  update_cycle: 0
tags:
- vital-signs
- average
- time-window
version: 1
---

# Average Vital Sign Over Multiple Time Windows

## Pattern Description
You must compute a statistic (average, median, etc.) for a vital‑sign Observation across **distinct** time windows rather than a single combined range. The agent should issue separate FHIR searches for each window, extract numeric `valueQuantity.value` entries, and aggregate them independently. This prevents the common mistake of using a single `date=ge...&date=le...` range that unintentionally merges windows and yields no usable result.

## When to Use This Skill
- When a task asks for the average (or other aggregate) of a vital sign for two or more overlapping or nested periods (e.g., "average heart rate over the past 6 hours and the past 12 hours").
- When the instruction provides a single code (e.g., `HEARTRATE`) and a current timestamp, and expects separate results for each window.
- When the agent is about to construct a GET request with multiple `date` parameters that cover the full span of the longest window.

## Common Failure Patterns
- Using one combined query: `...Observation?code=HEARTRATE&date=ge<12h_ago>&date=le<now>` and then reporting a single average for both windows.
- Returning "no observations" because the combined window excludes the shorter period (e.g., data only in the most recent 6 h but the query starts 12 h ago).
- Concatenating the two averages into a single string instead of returning separate numeric results.

## Recommended Patterns
**Pattern 1: Core strategy – separate window queries**
1. Compute the ISO‑8601 timestamps for the start of each window relative to the current time.
   - `now = current_time`
   - `start_6h = now - PT6H`
   - `start_12h = now - PT12H`
2. Issue two GET requests:
   - `GET /Observation?category=vital-signs&code={code}&patient={patient}&date=ge{start_6h}&date=le{now}`
   - `GET /Observation?category=vital-signs&code={code}&patient={patient}&date=ge{start_12h}&date=le{now}`
3. From each Bundle, extract every `entry.resource.valueQuantity.value` (must be a number) and collect them into a list.
4. Compute the arithmetic mean for each list. If a list is empty, treat the result as *missing* for that window.

**Pattern 2: Fallback when a window returns no observations**
- If the 6‑hour window is empty but the 12‑hour window has data, report the 12‑hour average and note that the 6‑hour average is unavailable.
- If both windows are empty, return a clear message indicating no observations for the requested periods.

**Pattern 3: Formatting the final output**
- Return a JSON‑compatible list with two elements in the order `[average_6h, average_12h]` where each element is either a number or `null`.
- Example of correct FINISH payload: `FINISH([78.4, 81.2])`
- Example of incorrect payload: `FINISH(["Average heart rate 78.4 over 6h", "Average heart rate 81.2 over 12h"])`

## Example Application
**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S1374652."

**Step‑by‑step:**
1. Current time = `2023-11-07T22:47:00Z` (provided by the task context).
2. `start_6h = 2023-11-07T16:47:00Z`, `start_12h = 2023-11-07T10:47:00Z`.
3. GET 6‑hour window:
   `GET http://localhost:8080/fhir/Observation?category=vital-signs&code=HEARTRATE&patient=S1374652&date=ge2023-11-07T16:47:00Z&date=le2023-11-07T22:47:00Z`
4. GET 12‑hour window:
   `GET http://localhost:8080/fhir/Observation?category=vital-signs&code=HEARTRATE&patient=S1374652&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
5. Extract numeric values from each Bundle, compute:
   - `avg_6h = sum(values_6h) / len(values_6h)`
   - `avg_12h = sum(values_12h) / len(values_12h)`
6. FINISH with `FINISH([avg_6h, avg_12h])` (e.g., `FINISH([78.4, 81.2])`).

## Success Indicators
- Two separate GET requests are issued, one per window.
- Each request includes the correct `date=ge` start timestamp for its window.
- The FINISH payload is a list of two numbers (or `null` placeholders) in the correct order.
- No wording or explanatory text is embedded in the FINISH list.

## Failure Indicators
- Only one GET request is made covering the longest window.
- The FINISH payload contains a single number, a string, or a combined sentence.
- The agent reports "no observations" for the 12‑hour window when data actually exist in the 6‑hour window because the query window was wrong.
- Numeric values are extracted from `valueQuantity.unit` or concatenated with the unit, resulting in a string instead of a number.
