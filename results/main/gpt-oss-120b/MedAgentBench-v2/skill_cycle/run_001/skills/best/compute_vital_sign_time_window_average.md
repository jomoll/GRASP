---
description: "Calculate averages for vital\u2011sign observations over 6\u2011hour\
  \ and 12\u2011hour windows"
name: compute_vital_sign_time_window_average
provenance:
  action: ADD
  epoch: 3
  fixes: 9
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task6_26
  - task8_5
  - task3_30
  - task8_7
  - task2_14
  - task3_27
  - task2_15
  - task1_20
  - task3_1
  - task8_29
  update_cycle: 0
tags:
- vital-signs
- average
- time-window
version: 1
---

# Compute Vital‑Sign Time‑Window Averages

## Pattern Description
You must derive separate average values for a vital‑sign Observation (e.g., heart rate) over two distinct recent time windows: the most recent 6 hours and the most recent 12 hours. The skill is reusable for any observation code that reports a numeric `valueQuantity`. It changes behavior by preventing a premature `FINISH([null, null])` when the required data has been retrieved but not yet aggregated.

## When to Use This Skill
- After a **GET** request to `/Observation` with `category=vital-signs` and a specific `code` (e.g., `HEARTRATE`) that returns a Bundle containing one or more entries.
- The task explicitly asks for **average** values over the past 6 hours and 12 hours.
- The agent has already performed the two range‑filtered GETs (6 h window and 12 h window) but has not yet produced a numeric result.

## Common Failure Patterns
- Returning `FINISH([null, null])` because the skill that should compute the average never ran.
- Extracting `valueQuantity.value` as a string or including the unit (`valueQuantity.unit`).
- Using the wrong field such as `valueString` or `valueCodeableConcept` instead of the numeric `valueQuantity.value`.
- Ignoring the case where the Bundle `total` is 0, leading to division‑by‑zero or `null` values.

## Recommended Patterns
**Pattern 1: Core aggregation strategy**
1. Verify the GET response is a `Bundle` with `resourceType="Bundle"`.
2. If `total == 0`, set the corresponding window average to `null`.
3. Otherwise, iterate over `entry[].resource` (each should be an `Observation`).
4. For each Observation, read `valueQuantity.value` **as a number**.
5. Sum all numeric values and divide by the count to obtain the average.
6. Round to two decimal places (optional) and store the result.

```text
CORRECT: avg = sum(entry[i].resource.valueQuantity.value) / count
WRONG: avg = "" + entry[i].resource.valueQuantity.value   // concatenates as string
WRONG: avg = entry[i].resource.valueQuantity   // includes unit
```

**Pattern 2: Fallback when no observations**
- If both windows return `total == 0`, return `[null, null]`.
- If only one window has data, return `[average6h, null]` or `[null, average12h]` as appropriate.

**Pattern 3: FINISH formatting**
- After computing the two averages, call:
  `FINISH([average6h, average12h])`
- Do **not** embed explanatory text inside the FINISH array; only the numeric (or `null`) values.

## Example Application
**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6268253."

**Step‑by‑step:**
1. Issue the two GETs (already done by the agent):
   - `GET /Observation?category=vital-signs&code=HEARTRATE&patient=S6268253&date=ge2023-11-07T16:47:00Z&date=le2023-11-07T22:47:00Z`
   - `GET /Observation?category=vital-signs&code=HEARTRATE&patient=S6268253&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
2. For each response, apply Pattern 1 to compute `avg6h` and `avg12h`.
3. Apply Pattern 2 if a response has `total == 0`.
4. Call `FINISH([avg6h, avg12h])`.

**Correct output example:** `FINISH([78.4, 80.1])`
**Incorrect output example:** `FINISH(["Heart rate avg 78.4", null])`

## Success Indicators
- The agent calls `FINISH` with a two‑element array containing numbers or `null`.
- No explanatory strings appear inside the FINISH payload.
- The computed averages match manual calculation from the returned Observation values.

## Failure Indicators
- `FINISH([null, null])` despite the GET responses containing Observation entries.
- FINISH payload includes text or units (e.g., `"78 bpm"`).
- The skill is not invoked after the GETs, leaving the task incomplete.

---
*This skill works in conjunction with `apply_time_range_filter` (to ensure the correct date parameters) and `require_query_before_finish` (to guarantee a GET occurs before any FINISH).*
