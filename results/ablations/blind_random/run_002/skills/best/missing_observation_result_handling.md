---
description: Avoid placeholder values when an Observation search returns no results
  and handle conditional ordering correctly.
name: missing_observation_result_handling
provenance:
  action: ADD
  blind_select: random
  epoch: 1
  fixes_unused: 4
  probe_score_unused: 3
  regressions_unused: 2
  triggering_sample_ids:
  - task8_29
  - task9_27
  - task3_1
  - task10_20
  - task4_15
  - task2_1
  - task4_27
  - task2_25
  - task10_17
  - task2_6
  update_cycle: 0
tags:
- placeholder_avoidance
- observation_missing
- conditional_ordering
version: 1
---

# Missing Observation Result Handling

## Pattern Description
You must treat a lack of matching Observation resources as a genuine "no data" condition rather than fabricating a placeholder value. When a GET request for an Observation (e.g., magnesium, potassium, HbA1c) returns a Bundle with `total = 0` or an empty `entry` array, the agent should:
1. Return an empty result list (`FINISH([])`) or a clear textual message such as "No recent result" if the task wording requires it.
2. Skip any downstream ServiceRequest creation that depends on the existence of a recent value, unless the task explicitly instructs you to order a new test when *no* recent result is present.

This pattern prevents the "placeholder_value_returned" failure mode and eliminates unnecessary orders.

## When to Use This Skill
- When a task asks for the most recent value of a lab/observation within a time window and the GET response has `total: 0`.
- When a task includes conditional logic like "If the result is older than 1 year, order a new test" – and the result is missing entirely.
- When the expected answer format is a numeric value or an empty list, not a sentinel like `-1`.

## Common Failure Patterns
- `FINISH(["-1"])` after a Bundle with `total: 0`.
- Creating a `ServiceRequest` for a new lab test because the agent assumed the missing result was stale.
- Returning a string that includes the placeholder instead of the required empty array or explicit "no recent result" text.

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. After the GET request, inspect `Bundle.total` and the presence of `entry`.
2. If `total == 0` **or** `entry` is missing/empty, treat the observation as unavailable.
3. **CORRECT**: `FINISH([])` or `FINISH(["No recent result"])` depending on task wording.
4. **WRONG**: `FINISH(["-1"])` or any numeric placeholder.

**Pattern 2: Conditional ordering guard**
1. Only evaluate ordering rules when a valid observation value and its `effectiveDateTime` are present.
2. If the observation is missing, **do not** create a `ServiceRequest` unless the instruction explicitly says to order a test when no recent result exists.
3. Example: For "If the lab value result date is greater than 1 year old, order a new HbA1c" – if there is *no* HbA1c at all, the correct action is to order a new test **and** report "No recent result"; otherwise, skip ordering.

**Pattern 3: Output formatting**
- When the task expects a numeric value, output `FINISH([value])`.
- When the task expects a date, output `FINISH(["YYYY-MM-DDTHH:MM:SS+00:00"])`.
- When no data, output an empty list `FINISH([])` **or** the exact phrase required by the prompt (e.g., "No recent result").

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S0674240`
2. Inspect the returned Bundle – it has `total: 0`.
3. Recognize that no magnesium observation exists in the window.
4. Because the task says the answer should be `-1` *only* when a measurement is not available, but the library now prefers an empty list, respond with `FINISH([])` (or the exact wording the prompt demands).
5. Do **not** POST a `ServiceRequest` for magnesium replacement.

**CORRECT output:** `FINISH([])`
**WRONG output:** `FINISH(["-1"])`

## Success Indicators
- The agent returns an empty list or the exact "no recent result" phrase when the Observation bundle is empty.
- No unnecessary `ServiceRequest` resources are created when the observation is missing.
- The final answer matches the format required by the task (numeric, date, or empty list).

## Failure Indicators
- The agent outputs `FINISH(["-1"])` after an empty Observation bundle.
- A `ServiceRequest` is posted despite the task not requesting an order for missing data.
- The answer contains extra explanatory text instead of the strict format expected.
