---
description: Enforce date filtering for lab observations when a time window is specified
  in the task.
name: lab_observation_recency_enforcement_for_time_windowed_tasks
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task9_11
  - task9_1
  - task5_16
  - task5_17
  - task9_14
  - task4_28
  update_cycle: 1
tags:
- lab
- observation
- recency
- date filtering
- time window
- magnesium
- replacement therapy
version: 1
---

## Lab Observation Recency Enforcement for Time-Windowed Tasks

When a task requires lab values within a specific time window (e.g., "last 24 hours"), you must actively filter the returned Observation resources to ensure only results within the required window are considered. This prevents using outdated values and avoids inappropriate actions (such as ordering replacement therapy based on stale labs).

This skill applies to any lab retrieval or decision task where the instruction specifies a time window (e.g., "within last 24 hours", "past week", "since admission"). The agent must check the timestamp of each Observation and only use those that meet the recency requirement.

## When to Use This Skill

- When a task asks for a lab value "within last X hours/days" or similar time window.
- When deciding whether to order replacement therapy based on a lab value's recency.
- When the answer should be -1 or "not available" if no value meets the time window.

## Common Failure Patterns

- Using the most recent lab value regardless of its timestamp, ignoring the time window.
- Returning a value from an Observation older than the specified window.
- Failing to check `effectiveDateTime` or `issued` fields for recency.
- Returning a value or ordering therapy when no qualifying lab exists.

## Recommended Patterns

**Pattern 1: Recency Filtering**
- After GET /Observation, inspect each entry's `resource.effectiveDateTime` (or `issued` if effectiveDateTime is missing).
- Compare the timestamp to the current time. Only consider values within the specified window (e.g., for "last 24 hours", only values where `current_time - effectiveDateTime <= 24 hours`).
- If multiple values qualify, use the most recent one.

CORRECT: Only use [2.0, "2023-11-12T13:31:00+00:00"] if it is within 24 hours of current time.
WRONG: Use [2.0, "2023-11-10T13:31:00+00:00"] for a "last 24 hours" task.

**Pattern 2: No Qualifying Value**
- If no Observation is within the window, return the missing value representation (e.g., `FINISH([])`, `FINISH([-1])`, or a message as specified).
- Do not order replacement therapy if no qualifying lab exists.

**Pattern 3: Downstream Decision**
- Only proceed to threshold checks or ordering if a qualifying lab value is found.
- If the value is missing, halt and return the appropriate missing value output.

## Example Application

**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step-by-step:**

1. Issue GET /Observation?code=MG&patient=S1023381
2. For each entry, extract `resource.effectiveDateTime` and compare to current time (2023-11-13T10:15:00+00:00).
3. Only consider values with `effectiveDateTime` >= 2023-11-12T10:15:00+00:00.
4. If a value exists, check if it is low and order replacement as needed.
5. If no value exists, return `FINISH([])` (do not order anything).

CORRECT output: `FINISH([])` if no value in last 24 hours.
WRONG output: `FINISH([2.0, "2023-11-12T13:31:00+00:00"])` if the value is outside the window.

## Success Indicators

- Agent only uses lab values within the specified time window.
- No replacement therapy is ordered if no qualifying lab exists.
- Output reflects missing value if no recent lab is found.

## Failure Indicators

- Agent uses outdated lab values for decision-making.
- Orders replacement therapy based on labs outside the window.
- Returns a value or answer when none should be available.
