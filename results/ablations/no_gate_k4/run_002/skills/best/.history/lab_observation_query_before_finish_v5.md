---
description: "Handle empty Observation results with task\u2011specific placeholder\
  \ or default no\u2011result message"
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 4
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task4_27
  - task5_19
  - task5_3
  - task4_20
  - task2_30
  - task4_4
  - task10_10
  - task4_15
  update_cycle: 1
tags:
- lab
- observation
- no-result
- placeholder
version: 5
---

# lab_observation_query_before_finish

## Pattern Description
You must decide what scalar answer to return when a GET /Observation search yields no entries. If the task text explicitly defines a placeholder value (e.g., `-1`, `null`, or a custom string), return that exact placeholder. If the task does **not** specify a placeholder, return the generic no‑result message `"no result"`. This prevents mismatches between the agent’s FINISH payload and the expected answer format.

## When to Use This Skill
- When a task asks for the most recent value of a lab (e.g., magnesium, potassium, HbA1c) **and** you have performed a GET Observation that returns `total: 0`.
- When the task description contains a phrase like “the answer should be **-1** if a measurement … is not available” or any other explicit placeholder.
- When the task does **not** mention a placeholder but still expects a scalar answer.

## Common Failure Patterns
- Returning `-1` while the skill expects the generic string `"no result"` (or vice‑versa).
- Returning a JSON array with extra explanatory text instead of the exact placeholder.
- Ignoring the task‑provided placeholder and always using the default message.

## Recommended Patterns
**Pattern 1: Detect task‑provided placeholder**
1. Scan the task description for a placeholder pattern using a simple regex (e.g., `"-?\d+"` or quoted words like `"no result"`).
2. If a placeholder is found, store it as `expected_placeholder`.
3. After the Observation GET, check `Bundle.total`.
4. If `total == 0`:
   - If `expected_placeholder` is set, `FINISH([expected_placeholder])`.
   - Else `FINISH(["no result"])`.

**Pattern 2: Fallback verification**
- Verify that the FINISH payload is a single‑element array containing exactly the placeholder string (no extra spaces or quotes).

## Example Application
**Task:** “What’s the most recent magnesium level of the patient S6474456 within last 24 hours? The answer should be a single number converted to mg/dL, and it should be **-1** if a measurement within last 24 hours is not available.”

**Step‑by‑step:**
1. `GET /Observation?code=MG&patient=S6474456&date=ge2023‑11‑12T10:15:00&date=le2023‑11‑13T10:15:00`
2. Response `Bundle.total = 0`.
3. Detect placeholder `-1` in the task text.
4. `FINISH(["-1"])`.

**CORRECT output:** `FINISH(["-1"])`
**WRONG output:** `FINISH(["no result"])` or `FINISH(["-1", "extra text"])`

## Success Indicators
- FINISH payload is a one‑element array containing exactly the placeholder defined by the task (or the default `"no result"`).
- No extra explanatory strings are present.

## Failure Indicators
- FINISH payload contains a different placeholder than the one described in the task.
- FINISH payload includes additional text or an array with more than one element.
