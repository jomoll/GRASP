---
description: "Detect and replace placeholder [-1] FINISH answers for lab\u2011value\
  \ queries"
name: placeholder_result_detection
provenance:
  action: ADD
  epoch: 1
  fixes: 10
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task5_17
  - task9_6
  - task8_29
  - task5_7
  - task9_27
  - task9_14
  - task9_20
  - task10_12
  - task10_21
  update_cycle: 0
tags:
- placeholder
- lab_result
- order_logic
version: 1
---

# Placeholder Result Detection and Handling

## Pattern Description
You must guard against returning the sentinel value `[-1]` when a task explicitly asks for the latest numeric lab result (e.g., "last HbA1C value"). The placeholder is only valid for queries that define `-1` as a legitimate answer (such as "most recent magnesium level, return -1 if none"). For all other lab‑value queries you must either extract a real value/date or, if no recent result exists, create an appropriate order before finishing.

## When to Use This Skill
- The task description contains phrases like **"last *X* value"**, **"most recent *X*"**, or **"what’s the *X*"** where *X* is a lab observation (HbA1c, potassium, etc.) **and** the expected answer is a numeric value (not a sentinel).
- After a GET request the agent is about to call `FINISH([-1])`.
- The GET response `Bundle.total` is `0` (no observations) **or** the newest observation is older than the business‑logic threshold (e.g., > 1 year for HbA1c).

## Common Failure Patterns
- `FINISH([-1])` emitted for an HbA1c query even though the task expects a numeric result.
- GET response shows `"total": 0` but the agent still finishes with `[-1]` instead of ordering a new test.
- Returning `[-1]` for a potassium or magnesium query that does **not** define `-1` as a valid answer.
- Using the placeholder for any lab where the task later requires an order based on staleness.

## Recommended Patterns
**Pattern 1: Detect placeholder before finishing**
1. Inspect the pending `FINISH` argument. If it is exactly `[-1]` **and** the task description matches the *lab‑value* pattern above, intervene.
2. Examine the most recent GET response for that observation:
   - If `Bundle.total == 0`, treat as *no result*.
   - If `Bundle.total > 0`, locate the entry with the greatest `effectiveDateTime` (or `issued`).
3. Determine staleness:
   - Parse the current context time (e.g., `2023-11-13T10:15:00+00:00`).
   - If the latest observation date is older than the allowed window (e.g., 1 year for HbA1c), mark as *stale*.
4. **If no result or stale:**
   - Construct a `ServiceRequest` POST using the ordering LOINC code supplied in the task context (e.g., `4548-4` for HbA1c).
   - Include `authoredOn` = current time, `status` = `active`, `intent` = `order`, `priority` = `stat`, and reference the patient.
   - After successful POST, **do not** finish with `[-1]`; instead finish with the extracted value/date **if available**, or with a message indicating the order was placed.
5. **If a fresh result exists:**
   - Extract `valueQuantity.value` (or `valueString` if appropriate) as a number.
   - Extract the corresponding `effectiveDateTime`.
   - `FINISH([value, "date"])`.

**Pattern 2: Fallback for allowed sentinel**
- If the task explicitly states that `-1` is the correct answer when no measurement is available (e.g., magnesium level tasks), allow `FINISH([-1])` and skip the above steps.

**Pattern 3: Output formatting**
- Always return a JSON‑compatible array: either `[numeric_value, "ISO‑8601 timestamp"]` or a short explanatory string when an order is placed.
- Never embed explanatory sentences inside the array.

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S1234567 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S1234567`
2. Response shows `total = 0` → no result.
3. Because the task expects a numeric value, do **not** `FINISH([-1])`.
4. Build and `POST` a `ServiceRequest` with LOINC `4548-4`.
5. After POST succeeds, `FINISH(["Order placed for new HbA1c test"])` **or** simply omit the finish until a future result arrives.

**If a fresh result existed:**
1. Locate the newest entry, e.g., `effectiveDateTime = "2023-07-07T11:27:00+00:00"` and `valueQuantity.value = 5.7`.
2. `FINISH([5.7, "2023-07-07T11:27:00+00:00"])`.

## Success Indicators
- No `FINISH([-1])` appears for tasks that request a numeric lab value.
- Fresh lab values are extracted correctly and returned as `[value, "date"]`.
- When no recent value exists, a `ServiceRequest` POST is issued before finishing.

## Failure Indicators
- The agent still emits `FINISH([-1])` for a HbA1c or similar lab query.
- The agent orders a test but also includes `[-1]` in the final answer.
- The agent extracts a string or unit‑containing value instead of a pure number.
