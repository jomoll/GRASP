---
description: "Enforce correct array shape and sentinel handling only for tasks that\
  \ explicitly request a lab/value\u2011timestamp answer. The rule now first checks\
  \ the task description for keywords indicating a value\u2011timestamp query before\
  \ applying any shape validation or sentinel substitution. Sentinel handling is applied\
  \ **only** when the description contains an explicit \"should be -1\" clause. All\
  \ other tasks (e.g., ServiceRequest ordering) are ignored by this skill."
name: answer_format_enforcement_array
provenance:
  action: MODIFY
  epoch: 3
  fixes: 5
  parent_version: 1
  probe_score: 2
  regressions: 4
  triggering_sample_ids:
  - task8_23
  - task8_3
  - task10_16
  - task8_19
  - task8_14
  - task8_9
  - task9_3
  - task8_21
  - task10_10
  update_cycle: 1
tags: []
version: 2
---

# Answer Format Enforcement for Lab Result Arrays (Refined)

## Scope Guard
1. **Activate only when the task description indicates a value‑timestamp query.**
   - The description must contain **both** of the following (case‑insensitive):
     - a keyword suggesting a numeric result is required (`"value"`, `"result"`, `"HbA1C"`, `"potassium"`, `"magnesium"`, etc.)
     - a keyword indicating a timestamp is required (`"when"`, `"recorded"`, `"date"`, `"time"`).
   - If either keyword is missing, the skill does nothing and the agent may finish with any payload.

## Pattern 1: Validate array shape (when activated)
1. After extracting the observation, build `result = [value, timestamp]` where:
   - `value` is a plain number (`valueQuantity.value`).
   - `timestamp` is the ISO‑8601 string from `effectiveDateTime` or `issued`.
2. Verify `Array.isArray(result) && result.length===2 && typeof result[0]==='number' && typeof result[1]==='string'`.
3. If the check passes, call `FINISH(result)`.
4. If the check fails, **do not** modify the payload; fall through to Pattern 2.

## Pattern 2: Sentinel handling (only when the description explicitly permits it)
1. Inspect the original task description for the exact phrase **"should be -1"** (case‑insensitive).
2. If the phrase is present **and** no observation was found (`Bundle.total == 0`), return `FINISH([-1])`.
3. If the phrase is absent and no observation was found, return an empty array `FINISH([])`.
4. In all other cases (observation present, or phrase absent but observation missing), do **not** replace the agent’s existing payload.

## Pattern 3: Fallback for unexpected data
- Log a warning (optional) and return `FINISH([])` **only** if the guard in Scope Guard was satisfied and both Pattern 1 and Pattern 2 decided that no valid result exists.

## Example Application (unchanged logic, but now guarded)
**Task:** "What’s the last HbA1C value in the chart for patient S6521727 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."
1. Guard matches (contains "value" and "recorded").
2. Observation exists → Pattern 1 builds `[5.8, "2022-09-09T15:33:00+00:00"]` and validates shape.
3. Because shape is valid, `FINISH([5.8, "2022-09-09T15:33:00+00:00"])` is called (the ordering step is independent).

**Task:** "Order orthopedic surgery referral for patient S2863714 …"
1. Guard does **not** match (no "value"/"recorded" keywords).
2. Skill does nothing; the agent’s original `FINISH(["ServiceRequest created"])` is left untouched.

## Success Indicators
- FINISH calls for value‑timestamp tasks return a two‑element numeric/string array, `[]`, or `[-1]` **exactly** as dictated by the task description.
- FINISH calls for unrelated tasks (e.g., ServiceRequest creation) are unaffected.
- Sentinel `-1` appears only when the description explicitly contains the phrase "should be -1".

## Failure Indicators
- FINISH returns `[-1]` for a task that never mentioned a sentinel.
- FINISH returns an array with wrong element types for a value‑timestamp task.
- The skill modifies FINISH payloads for tasks that do not request a value‑timestamp answer.
