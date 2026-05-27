---
description: "Return a structured placeholder (value\u2011timestamp pair) when a lab\
  \ Observation search yields no entries"
name: missing_observation_placeholder
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_28
  - task10_20
  - task4_10
  - task5_17
  - task9_6
  - task4_27
  - task8_29
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags: []
version: 2
---

# missing_observation_placeholder

## Pattern Description
You must provide a machine‑readable placeholder whenever a GET request for a lab Observation returns an empty Bundle but the downstream task expects a value‑timestamp pair (e.g., HbA1c, fasting glucose). Instead of a free‑text sentence, return a two‑element array where the first element is `null` (or a sentinel like `-1`) and the second element is `null`. This keeps the answer type consistent with the successful case that returns `[value, "timestamp"]`.

## When to Use This Skill
- When a task asks for "the last <lab> value and when it was recorded" and the Observation search (`GET .../Observation?...`) returns `total: 0`.
- The expected FINISH output format is a JSON array of length 2 (numeric value, ISO‑8601 timestamp).
- Example tasks: HbA1c, fasting glucose, serum creatinine, etc., where the answer must be `[value, "timestamp"]`.

## Common Failure Patterns
- Returning a free‑text string such as `"No HbA1c result found for patient X; no new test ordered."` – wrong type (string instead of array).
- Returning a single‑element array (e.g., `[-1]`) when the caller expects two elements.
- Omitting the placeholder entirely and leaving the agent to finish without an answer.

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. After issuing the GET request, inspect the `total` field in the Bundle response.
2. If `total == 0`, trigger the placeholder logic.

**Pattern 2: Emit structured placeholder**
- CORRECT: `FINISH([null, null])`  (or `FINISH([-1, null])` if the numeric field uses `-1` as a sentinel for "not available").
- WRONG: `FINISH(["No result found"])` or any free‑text string.

**Pattern 3: Preserve downstream decision flow**
- If the task includes conditional logic (e.g., "if the result is > 1 year old, order a new test"), the placeholder should still allow the condition to evaluate safely. Use `null` so that date comparisons fail gracefully, and the agent can decide not to place an order.

## Example Application
**Task:** "What’s the last HbA1c value in the chart for patient S1234567 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1c lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S1234567`
2. Receive Bundle with `"total": 0`.
3. Apply missing_observation_placeholder:
   - Emit `FINISH([null, null])`.
4. The agent sees a `null` timestamp, determines the "older than 1 year" check cannot be satisfied, and therefore does **not** place a ServiceRequest.

**Correct output:** `FINISH([null, null])`
**Incorrect output:** `FINISH(["No HbA1c result found for patient S1234567; no new test ordered."])`

## Success Indicators
- FINISH output is a two‑element JSON array when the Observation bundle is empty.
- No free‑text placeholder appears in the answer.
- Subsequent conditional logic (date comparison, ordering) behaves as expected (usually resulting in no order).

## Failure Indicators
- FINISH returns a string or an array of the wrong length.
- The agent attempts to order a new test based on a placeholder value.
- Tests that expect a numeric‑timestamp pair fail type validation.

---
*Tags*: ["placeholder", "lab_observation", "answer_format"]
