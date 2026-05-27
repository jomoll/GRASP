---
description: Return a numeric -1 placeholder for missing numeric lab observations
  instead of a string.
name: handle_missing_observation_numeric_placeholder
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 8
  regressions: 0
  triggering_sample_ids:
  - task4_6
  - task5_19
  - task1_20
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task2_14
  - task2_6
  update_cycle: 1
tags:
- observation
- placeholder
- numeric
- error_handling
version: 1
---

# handle_missing_observation_numeric_placeholder

## Pattern Description
You must detect when a FHIR Observation search returns no results and the task expects a single numeric value (e.g., most recent magnesium, potassium, or HbA1c). In that case, return the numeric sentinel `-1` **as a number**, not as a quoted string, wrapped in a FINISH call. This prevents the agent from emitting an invalid answer placeholder like `"-1"` which downstream consumers treat as a string error.

## When to Use This Skill
- After a `GET .../Observation?...` request where the task asks for "the most recent <lab> level" or similar numeric result.
- The task description explicitly states that `-1` should be used when no measurement is available.
- The response bundle has `"total": 0` (no matching Observation resources).

## Common Failure Patterns
- Returning `FINISH(["-1"])` – the placeholder is a string, not a number.
- Omitting the FINISH call entirely after detecting an empty bundle.
- Returning a free‑text message when the specification requires the numeric sentinel.

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. Inspect the JSON response from the Observation GET.
2. If `bundle.total == 0` (or the `entry` array is missing/empty), proceed to Pattern 2.

**Pattern 2: Emit numeric placeholder**
- Use the exact syntax: `FINISH([-1])` (no quotes around -1).
- Do **not** wrap the number in an array of strings or add extra text.

**Pattern 3: Fallback for non‑numeric tasks**
- If the task expects a textual explanation (e.g., "No magnesium level recorded…"), follow the task‑specific wording instead of the numeric sentinel.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1733937 within last 24 hours? The answer should be a single number converted to mg/dL, and it should be -1 if a measurement within last 24 hours is not available."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1733937&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. Receive bundle with `"total": 0`.
3. Apply Pattern 1 → bundle empty.
4. Apply Pattern 2 → `FINISH([-1])`.

**Correct output:** `FINISH([-1])`
**Wrong output:** `FINISH(["-1"])` or `FINISH(["No magnesium level…"])` when the spec demands the numeric sentinel.

## Success Indicators
- The agent emits `FINISH([-1])` (numeric) whenever an empty Observation bundle is detected for a numeric‑value task.
- No quoted `"-1"` appears in the final answer.
- The output matches the exact format required by the task description.

## Failure Indicators
- The final FINISH call contains `"-1"` (string) instead of `-1` (number).
- The agent returns a free‑text message when the task explicitly requires the numeric sentinel.
- The agent proceeds to further processing after an empty bundle instead of terminating with the placeholder.
