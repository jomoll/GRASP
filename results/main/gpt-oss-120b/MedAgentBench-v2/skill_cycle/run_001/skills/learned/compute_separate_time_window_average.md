---
description: "Split a vital\u2011sign Observation query into 6\u2011hour and 12\u2011\
  hour windows and return each average."
name: compute_separate_time_window_average
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task3_29
  - task2_1
  - task3_3
  - task8_26
  - task3_7
  - task6_19
  - task2_14
  - task3_27
  - task1_20
  - task2_30
  update_cycle: 1
tags: []
version: 1
---

# Compute Separate Time Window Average for Vital Signs

## Pattern Description
You must calculate separate averages for a vital‑sign code (e.g., `HEARTRATE`) over two distinct recent periods: the last 6 hours and the last 12 hours.  The skill isolates the two time windows, extracts numeric values from `valueQuantity.value`, computes each mean, and returns both numbers in a single `FINISH` call.  This prevents the agent from issuing a single broad query and then incorrectly reporting “no data” for one window when data exist for the other.

## When to Use This Skill
- The task asks for *average* of a vital‑sign (heart rate, respiratory rate, etc.) **over the past 6 hours and the past 12 hours**.
- The instruction explicitly mentions two separate windows (e.g., “average heart rate over the past 6 hours and the past 12 hours”).
- The patient identifier and observation code are known, and the current time is provided in the task context.

## Common Failure Patterns
- A single GET request with a 12‑hour filter is used, then the same result is reused for the 6‑hour average, leading to inaccurate or missing values.
- The agent returns a single message like `"No heart rate data available for the past 12 hours (and thus also none in the past 6 hours)."` without performing two distinct queries.
- Extraction of the value includes the unit string (`valueQuantity.value` concatenated with `valueQuantity.unit`).
- The final `FINISH` payload contains free‑text instead of a numeric array.

## Recommended Patterns
**Pattern 1: Query each window separately**
1. **Build the 6‑hour query**
   ```
   GET {base}/Observation?category=vital-signs&code={CODE}&patient={PATIENT}&date=ge{NOW_MINUS_6H}&date=le{NOW}
   ```
2. **Build the 12‑hour query**
   ```
   GET {base}/Observation?category=vital-signs&code={CODE}&patient={PATIENT}&date=ge{NOW_MINUS_12H}&date=le{NOW}
   ```
3. **Extract numeric values** from each bundle entry:
   - Locate `entry[i].resource.valueQuantity.value` (must be a number).
   - Ignore entries where `valueQuantity` is missing or not a number.
4. **Compute the average** for each window:
   - `avg6 = sum(values6) / count(values6)`
   - `avg12 = sum(values12) / count(values12)`
   - If a window has zero values, set the result to `null`.
5. **Return the result** in a strict array format:
   ```
   FINISH([avg6, avg12])
   ```
   - `null` is allowed for a window with no data.

**Pattern 2: Fallback when a window returns no observations**
- If the 6‑hour bundle is empty, set `avg6 = null` but still compute `avg12`.
- If the 12‑hour bundle is empty, set `avg12 = null`.
- Do **not** infer the missing window from the other window.

**Pattern 3: Formatting rule**
- The `FINISH` payload must be a JSON‑compatible array of numbers (or `null`).
- Do **not** embed explanatory text, units, or sentences inside the array.
- Example of correct output: `FINISH([78.4, 80.1])`.
- Example of wrong output: `FINISH(["Average heart rate: 78.4 bpm"] )`.

## Example Application
**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S3032536."

**Step‑by‑step:**
1. Determine current time from context: `2023‑11‑07T22:47:00+00:00`.
2. Compute window start times:
   - `nowMinus6h = 2023‑11‑07T16:47:00+00:00`
   - `nowMinus12h = 2023‑11‑07T10:47:00+00:00`
3. Issue two GET requests:
   - `GET /fhir/Observation?category=vital-signs&code=HEARTRATE&patient=S3032536&date=ge2023-11-07T16:47:00+00:00&date=le2023-11-07T22:47:00+00:00`
   - `GET /fhir/Observation?category=vital-signs&code=HEARTRATE&patient=S3032536&date=ge2023-11-07T10:47:00+00:00&date=le2023-11-07T22:47:00+00:00`
4. Extract all `valueQuantity.value` numbers from each bundle.
5. Compute `avg6` and `avg12` (e.g., `avg6 = 78.2`, `avg12 = 79.5`).
6. Return:
   ```
   FINISH([78.2, 79.5])
   ```

## Success Indicators
- Two separate GET requests are issued, one with a 6‑hour filter and one with a 12‑hour filter.
- The agent extracts only the numeric `valueQuantity.value` fields.
- The final `FINISH` call contains an array of two elements (numbers or `null`).
- No free‑text explanation is embedded in the array.

## Failure Indicators
- Only one GET request is made for the 12‑hour window.
- The agent re‑uses the 12‑hour result for the 6‑hour average.
- The `FINISH` payload contains a sentence or includes units.
- The agent reports “no data for both windows” without attempting the second query.
