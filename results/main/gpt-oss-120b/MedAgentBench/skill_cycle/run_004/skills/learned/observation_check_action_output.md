---
description: Make ServiceRequest ordering for labs return an empty array instead of
  raw observation data
name: observation_check_action_output
provenance:
  action: MODIFY
  epoch: 3
  fixes: 6
  parent_version: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task10_17
  - task10_18
  - task10_24
  - task10_13
  update_cycle: 1
tags:
- lab
- service_request
- observation
version: 2
---

# Observation Check Action Output

## Pattern Description
You must ensure that any task whose primary purpose is to *check* a lab Observation and, based on that check, *order* a new lab ServiceRequest does **not** return the raw Observation payload as the final answer. The correct final output is an empty array (or the minimal required answer) because the ordering action is the side‑effect, not the data to be reported.

## When to Use This Skill
- When a task asks for the *last* value of a lab (e.g., HbA1c, potassium) **and** adds a condition such as “if the result is older than 1 year, order a new test”.
- When the agent has already performed a `POST /ServiceRequest` for a lab LOINC code.
- The task does **not** request the Observation to be echoed back; it only wants the value **or** the ordering side‑effect.

## Common Failure Patterns
- Returning `FINISH([{"value":5.2,"date":"2022-08-09T..."}])` after a successful `POST /ServiceRequest` for a lab.
- Mixing medication‑order logic (covered by the existing skill) with lab‑order logic, leaving the lab case unhandled.
- Forgetting to suppress the Observation payload when the ordering condition is met.

## Recommended Patterns
**Pattern 1: Detect Lab‑Order Decision**
1. After extracting the latest Observation, compare its `effectiveDateTime` (or `issued`) to the current time.
2. If the date is older than the threshold **and** the task specifies ordering a new lab, construct a `ServiceRequest` with the appropriate LOINC code.
3. **Do not** include the extracted Observation in the final `FINISH` payload. Instead, return an empty array `FINISH([])` or the minimal required answer (e.g., `FINISH([-1])` when no recent value exists).

**Pattern 2: Fallback When No Observation Exists**
- If the GET for the Observation returns an empty bundle, still create the `ServiceRequest` if the task demands a new test, and finish with `FINISH([])`.

**Pattern 3: Explicit Output Formatting**
- Use numeric_answer_formatting to ensure any numeric values are plain numbers, but **only** when the task explicitly asks for the value (i.e., no ordering required).

## Example Application
**Task:** “What’s the last HbA1c value for patient S6500497 and when was it recorded? If the result date is > 1 year old, order a new HbA1c lab test.”

**Step‑by‑step:**
1. `GET /Observation?code=A1C&patient=S6500497` → extract `valueQuantity.value` and `effectiveDateTime`.
2. Compare `effectiveDateTime` to `now`. It is older than 1 year.
3. `POST /ServiceRequest` with LOINC `4548-4` (HbA1c) and patient reference.
4. **Do not** return the extracted Observation. Call `FINISH([])` (or `FINISH([-1])` if the task expects a sentinel when no recent value).

**Correct output:** `FINISH([])`
**Incorrect output:** `FINISH([{"value":5.2,"date":"2022-08-09T15:33:00+00:00"}])`

## Success Indicators
- After a lab ServiceRequest is posted, the final `FINISH` payload is an empty array (or the task‑specified sentinel).
- No Observation fields appear in the final answer when the task’s primary action is ordering.
- The `POST /ServiceRequest` request is present in the trace before the `FINISH` call.

## Failure Indicators
- The final `FINISH` contains the raw Observation JSON despite a ServiceRequest having been created.
- The agent returns a non‑array (e.g., object or string) when the task expects an empty array.
- The ordering logic runs but the Observation payload is still echoed back.
