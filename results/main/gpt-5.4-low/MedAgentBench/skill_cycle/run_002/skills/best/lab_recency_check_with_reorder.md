---
description: Apply explicit time-window filtering before interpreting labs or placing
  follow-up orders.
name: lab_recency_check_with_reorder
provenance:
  action: MODIFY
  epoch: 2
  fixes: 8
  parent_version: 1
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task5_7
  - task9_3
  - task9_6
  - task9_8
  - task9_9
  - task9_22
  - task4_28
  - task3_16
  - task5_16
  - task4_26
  update_cycle: 0
tags:
- observation
- date-filter
- recency
- ordering
version: 2
---

# Lab Recency Check With Reorder

## Pattern Description

When a task asks for the latest lab within a stated time window, or says to act only if a result is recent enough, you must enforce that recency requirement before interpreting the value or placing any downstream order. The reusable lesson is: first identify the allowed observation time window, then restrict or filter Observations by timestamp, and only then choose the most recent qualifying result.

This applies both to answer-only retrieval tasks and to conditional treatment/order workflows. If the task says "within last 24 hours," "older than 1 year," or similar, you must not use an undated `/Observation?code=...&patient=...` result as if all entries qualify. A value outside the allowed window must be treated as unavailable for that task, even if it is the most recent overall.

## When to Use This Skill

- When the prompt includes explicit timing language such as `within last 24 hours`, `in the last 24 hours`, `older than 1 year`, or `if no recent lab exists`
- When a GET `/Observation` is used to support a treatment decision, such as whether to place a `MedicationRequest` or `ServiceRequest`
- When the task asks for the most recent lab value but only within a constrained interval relative to the provided current time
- When a returned Observation Bundle contains multiple `entry[].resource.effectiveDateTime` values and only some may satisfy the recency threshold
- When the correct fallback is a sentinel value like `-1` or "don't order anything" if no observation falls inside the window

## Common Failure Patterns

- Querying `GET /Observation?code=MG&patient=S1311412` with no `date` constraint even though the task says `within last 24 hours`
- Selecting the latest overall Observation from `entry[]` without checking `effectiveDateTime` against the task window
- Placing a `MedicationRequest` because a magnesium value is low, even though that low value is older than the allowed 24-hour window
- Returning `-1` immediately after an unconstrained query returns `total: 0`, without considering that a proper constrained query or post-filter is the actual required operation
- Using only a lower bound when the task semantics require a bounded window relative to "now" and then failing to verify the selected result is not in the future
- Comparing against the wrong timestamp field; for recency, prefer `effectiveDateTime` on the Observation rather than unrelated metadata such as `meta.lastUpdated`

## Recommended Patterns

**Pattern 1: derive and apply the recency window first**
From the task's current time, compute the threshold timestamp before choosing any result.

- For `within last 24 hours` and now = `2023-11-13T10:15:00+00:00`, threshold is `2023-11-12T10:15:00+00:00`
- Preferred query form: `GET /Observation?code=MG&patient=S123&date=ge2023-11-12T10:15:00+00:00`
- After retrieval, still verify each candidate's `effectiveDateTime` is within the required window before using it

CORRECT: use `entry[].resource.effectiveDateTime` to test recency
WRONG: assume every returned Observation is recent because it has the correct `code`

**Pattern 2: filter the Bundle before interpretation or ordering**
If the server response is unconstrained or may contain mixed dates, filter `entry[]` yourself.

1. Read each `entry[].resource.effectiveDateTime`
2. Keep only observations inside the task window
3. Sort remaining observations by `effectiveDateTime` descending if needed
4. Use the newest qualifying Observation only
5. If none remain, treat the lab as unavailable for this task

For conditional treatment tasks, do not evaluate low/high thresholds until after this filtering step.

**Pattern 3: complete the task based on recent-qualified results only**
Once you have the newest qualifying Observation:

- Extract the numeric value from `valueQuantity.value`
- Apply any unit conversion only if the task explicitly requires it
- If the task says to reorder or treat only when the recent result is low/old/missing, make that decision from the filtered result set
- If no qualifying recent result exists, return the required fallback exactly and do not place an order unless the task explicitly instructs reordering for missing/old results

CORRECT: `FINISH([-1])` when no magnesium Observation exists in the last 24 hours
WRONG: place IV magnesium based on an older low magnesium result

## Example Application

**Task:** "What's the most recent magnesium level of the patient S1311412 within last 24 hours? Return -1 if unavailable."

**Step-by-step:**

1. Compute 24-hour threshold from now `2023-11-13T10:15:00+00:00` → `2023-11-12T10:15:00+00:00`
2. Issue `GET /Observation?code=MG&patient=S1311412&date=ge2023-11-12T10:15:00+00:00`
3. Inspect `entry[].resource.effectiveDateTime` and keep only qualifying observations
4. Select the newest qualifying Observation
5. Extract `valueQuantity.value`, convert to `mg/dL` only if needed, and return the single number
6. If no qualifying Observation remains, return the sentinel

CORRECT output: `FINISH([2.2])`
WRONG output:   `FINISH([1.6])` from an older Observation outside the last 24 hours

**Task:** "Check patient S6521727's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Compute threshold: `2023-11-12T10:15:00+00:00`
2. Issue `GET /Observation?code=MG&patient=S6521727&date=ge2023-11-12T10:15:00+00:00` or filter the returned Bundle by `effectiveDateTime`
3. If at least one observation remains, select the newest one
4. Only then assess whether `valueQuantity.value` is low enough to require replacement
5. Only if a recent low result exists, construct and POST the `MedicationRequest`
6. If no recent observation remains, return no recent lab / no order

CORRECT output: `FINISH([1.3,"2023-11-13T08:10:00+00:00","IV magnesium ordered: 2 g over 2 hours"])`
WRONG output:   `FINISH(["No magnesium level recorded in the last 24 hours","No order placed"])` when a qualifying `2023-11-13T08:10:00+00:00` result is present

## Success Indicators

- Your Observation query includes a `date=ge...` threshold when the task gives a recency window
- You explicitly inspect `effectiveDateTime` before selecting a result
- You choose the most recent qualifying Observation, not merely the first or latest overall
- You avoid placing orders when no Observation falls inside the allowed window
- Final outputs reflect the task's specified fallback format when no recent lab qualifies

## Failure Indicators

- You call `GET /Observation?code=...&patient=...` with no date filtering despite a `within last ...` requirement
- You use a stale lab value to answer a recent-only question
- You place a medication/order before checking whether the supporting lab is recent enough
- You return `-1` or "No order placed" even though the Bundle contains a qualifying recent Observation
- You base recency on `meta.lastUpdated` or another non-clinical timestamp instead of `effectiveDateTime`
