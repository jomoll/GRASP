---
description: "Return a value\u2011timestamp placeholder when no Observation entries\
  \ are found"
name: missing_observation_placeholder
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task9_22
  - task9_1
  - task2_1
  - task9_5
  - task1_20
  - task9_9
  - task10_10
  - task5_3
  - task1_10
  - task9_8
  update_cycle: 1
tags: []
version: 3
---

# missing_observation_placeholder

## Pattern Description
You must provide a structured placeholder whenever a GET /Observation search returns an empty bundle. The placeholder should contain both a sentinel value (`-1`) **and** an explicit `null` timestamp so downstream logic can distinguish “no result” from a real result that happens to be `-1`.

## When to Use This Skill
- When a GET request to `/Observation` with any code/patient/date filter returns `total: 0`.
- When the task asks for a lab value **and** a date (e.g., “What’s the last HbA1C value and when was it recorded?”).
- When the task expects a placeholder to drive staleness or ordering logic.

## Common Failure Patterns
- Only the numeric sentinel is returned: `FINISH([-1])` – the timestamp is missing.
- Returning an empty array `FINISH([])` instead of a placeholder.
- Using a string placeholder like `"no data"` which breaks numeric comparisons.

## Recommended Patterns
**Pattern 1: core placeholder construction**
1. Detect that the Bundle `total` field is `0`.
2. Build a two‑element array: first element is `-1` (value sentinel), second element is `null` (timestamp).
3. Call `FINISH([ -1, null ])`.

**Correct:** `FINISH([-1, null])`
**Wrong:** `FINISH([-1])` or `FINISH([])`

**Pattern 2: fallback for downstream logic**
- Any downstream rule that checks the timestamp must first verify that the second element is not `null` before comparing dates.

## Example Application
**Task:** “What’s the last HbA1C value and when was it recorded?”
**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S12345`.
2. Inspect the Bundle: if `total == 0`, construct placeholder.
3. `FINISH([-1, null])`.
4. Downstream staleness logic will see the `null` timestamp and treat the result as missing.

## Success Indicators
- The agent’s FINISH output is a two‑element array with `-1` and `null` when no Observation exists.
- Subsequent decision logic (e.g., ordering a repeat test) correctly triggers because the timestamp is `null`.

## Failure Indicators
- FINISH output contains only one element or an empty array.
- The timestamp field is omitted, causing date comparisons to raise errors.
