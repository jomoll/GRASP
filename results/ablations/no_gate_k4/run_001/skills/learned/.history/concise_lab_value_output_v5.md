---
description: Ensure timestamp is included when task wording requests the lab date
name: concise_lab_value_output
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 4
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
tags: []
version: 5
---

# Concise Lab Value Output

## Pattern Description
You must return lab results in the exact shape the task expects. When the prompt asks for *both* the value **and** the time it was recorded, output a two‑element array `[value, timestamp]`. If the prompt asks only for the value, return the scalar. This rule applies to any Observation, not just electrolytes.

## When to Use This Skill
- The task wording contains phrases like “when was it recorded”, “date of the result”, “timestamp”, or explicitly requests a pair.
- The agent has already performed a GET on `Observation?code=<code>&patient=<id>` and has the Observation bundle.

## Common Failure Patterns
- Returning only the numeric value (`5.9`) when the task also asked for the date.
- Returning a string that mixes value and date (e.g., `"5.9 on 2023‑11‑12"`).
- Omitting the timestamp field entirely, leading to missing‑date failures.

## Recommended Patterns
**Pattern 1: Detect Date Request**
1. Scan the task description for keywords: `date`, `when`, `recorded`, `timestamp`, `when was it recorded`.
2. Set a flag `need_timestamp = true` if any are found.

**Pattern 2: Extract Value and Timestamp**
1. From the Observation entry, read `valueQuantity.value` (or `valueString` for non‑numeric labs).
2. Read `effectiveDateTime` if present; otherwise fall back to `issued`.
3. Convert the timestamp to ISO‑8601 string exactly as received.

**Pattern 3: Format Output**
- If `need_timestamp` is true → `FINISH([value, "timestamp"])`.
- Else → `FINISH([value])`.

**Pattern 4: Missing Observation Fallback**
- If the bundle has `total: 0`, invoke the `missing_observation_placeholder` skill to return `[-1, null]` (or `[-1]` when no date is needed).

## Example Application
**Task:** “What’s the last HbA1C value for patient S1311412 and when was it recorded?”

**Steps:**
1. Detect the phrase “when was it recorded” → `need_timestamp = true`.
2. GET returns Observation with `valueQuantity.value = 5.9` and `effectiveDateTime = "2023-11-12T06:19:00+00:00"`.
3. Output `FINISH([5.9, "2023-11-12T06:19:00+00:00"])`.

**Task without date request:** “What’s the last HbA1C value for patient S1311412?”
- `need_timestamp = false` → output `FINISH([5.9])`.

## Success Indicators
- FINISH returns a two‑element array whenever the prompt asks for a date.
- The timestamp string matches the `effectiveDateTime` from the Observation exactly.
- No extra text or combined strings appear in the output.

## Failure Indicators
- Output is a single scalar when a date was requested.
- Timestamp is missing, malformed, or placed in a free‑text string.
- The agent posts an order because it mis‑interpreted the missing‑date case.
