---
description: "Return the most recent lab value and its timestamp without over\u2011\
  filtering by date"
name: lab_observation_value_and_timestamp
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task1_12
  - task1_20
  - task1_11
  - task1_16
  - task1_13
  - task10_10
  - task10_12
  - task10_13
  - task9_1
  - task1_26
  update_cycle: 1
tags:
- lab
- observation
- recency
version: 3
---

# Lab Observation Value and Timestamp

## Pattern Description
You must retrieve the latest Observation for a given lab code, regardless of its date, and return both the numeric value and the exact `effectiveDateTime`.  A date‑range filter should only be applied **after** the most recent result has been identified, not to pre‑filter the search.  This prevents older but still valid results from being hidden and forces the agent to decide whether the result is stale (e.g., >1 year) and whether a new order is required.

## When to Use This Skill
- When a task asks for "the last <lab> value" and may also require a recency check.
- When the initial GET request does **not** include a `date` parameter.
- When the response Bundle contains multiple entries and you need the most recent one.

## Common Failure Patterns
- Adding a `date=ge...` filter before extracting the value, causing the Bundle to be empty and triggering the missing‑observation placeholder.
- Selecting the first entry in the Bundle instead of the one with the greatest `effectiveDateTime`.
- Returning only the value (or only the timestamp) instead of the required `[value, timestamp]` array.

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. Issue `GET {base}/Observation?code={labCode}&patient={patientId}` **without** any date filter.
2. If `Bundle.total == 0`, fall back to the missing‑observation placeholder (handled by `missing_observation_placeholder`).
3. Otherwise, iterate over `Bundle.entry` and locate the Observation with the highest `effectiveDateTime`.
4. Extract `valueQuantity.value` (or the appropriate value field) as a number.
5. Extract `effectiveDateTime` as an ISO‑8601 string.
6. Return `FINISH([value, effectiveDateTime])`.

**Pattern 2: Recency verification (fallback)**
- After obtaining the timestamp, compare it to the task’s current time context.
- If the difference exceeds the allowed window (e.g., 1 year), trigger the ordering logic defined in `conditional_order_logic` or a similar skill.

**Pattern 3: Output formatting**
- Always output a two‑element array: `[numericValue, "YYYY‑MM‑DDThh:mm:ss+00:00"]`.
- Do **not** wrap the array in additional brackets or strings.

## Example Application
**Task:** "What’s the last HbA1C value for patient S1311412 and when was it recorded? If older than 1 year, order a new test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S1311412`
2. Bundle contains 4 entries; pick the one with the greatest `effectiveDateTime` → `2023-11-12T06:19:00+00:00`.
3. Extract `valueQuantity.value = 5.9`.
4. Return `FINISH([5.9, "2023-11-12T06:19:00+00:00"])`.
5. Since the timestamp is <1 year old, no additional order is created.

## Success Indicators
- The agent returns a two‑element array with a number and an ISO‑8601 timestamp.
- No placeholder `[-1, null]` is returned when a valid Observation exists.
- Subsequent conditional logic receives the correct timestamp for recency checks.

## Failure Indicators
- The agent returns `[-1, null]` despite the Bundle containing entries.
- The returned array is missing the timestamp or is wrapped in extra quotes.
- The agent applies a date filter before selecting the most recent Observation, leading to an empty result set.
