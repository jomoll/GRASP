---
description: Robustly extract numeric lab values and timestamps from Observation bundles,
  handling empty results and varied value formats.
name: observation_lookup_and_value_extraction
provenance:
  action: MODIFY
  epoch: 4
  fixes: 5
  parent_version: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task10_16
  - task9_22
  - task9_8
  update_cycle: 1
tags: []
version: 3
---

# Observation Value Extraction with Robust Fallback

## Pattern Description
You must reliably pull the most recent numeric result and its recording time from a FHIR Observation search. The pattern works for any lab or vital‑sign code (e.g., HbA1c, potassium, magnesium) and tolerates the many ways FHIR can store a value: `valueQuantity`, `valueString` with units, or a `component` array. It also defines a clear fallback when the bundle contains no matching Observation, allowing downstream conditional logic (e.g., ordering a repeat test) to proceed.

## When to Use This Skill
- When a task asks for the *last* value of a lab observation and the date it was recorded (e.g., “What’s the last HbA1c value and when was it recorded?”).
- When subsequent logic depends on the age of that result (e.g., order a new test if the result is > 1 year old).
- When the Observation bundle may be empty, or the value may be stored in different fields.

## Common Failure Patterns
- `total: 0` in the Observation bundle but the agent still tries to extract a value, leading to `FINISH([-1])` without triggering downstream ordering.
- Numeric value hidden in `valueString` (e.g., "5.4 %") instead of `valueQuantity.value`.
- Units concatenated with the number, causing the agent to return a string instead of a pure number.
- Multiple Observation entries returned; the agent picks the first unsorted entry, which may be stale.

## Recommended Patterns
**Pattern 1: Core extraction strategy**
1. Verify the bundle `total` > 0. If not, go to *Pattern 2*.
2. Sort `entry.resource` objects by `effectiveDateTime` (or `issued` if the former is missing) in descending order.
3. From the first (most recent) entry:
   - If `valueQuantity` exists, set `numeric = valueQuantity.value`.
   - Else if `valueString` exists, apply a regex `/[-+]?[0-9]*\.?[0-9]+/` to capture the first number.
   - Else if `component` array exists, locate the component whose `code.coding.code` matches the requested observation code and extract its `valueQuantity.value`.
4. Set `timestamp = effectiveDateTime` (fallback to `issued`).
5. Return `FINISH([numeric, "timestamp"])`.

**Pattern 2: Empty‑bundle fallback**
1. If the bundle `total` is 0, return `FINISH([-1])` **without** a timestamp.
2. Set an internal flag `observation_missing = true` so that downstream skills (e.g., `conditional_lab_result_age_order`) can decide to order a new test.

**Pattern 3: Formatting rule**
- The numeric part must be a plain number (no units, no surrounding text).
- The timestamp must be an ISO‑8601 string.
- Do **not** embed explanatory text in the FINISH payload.

## Example Application
**Task:** “What’s the last HbA1c value for patient S0658561 and when was it recorded?”

**Step‑by‑step:**
1. `GET /Observation?code=A1C&patient=S0658561` → receives a Bundle with `total = 1`.
2. Sort entries (only one entry, so it is the most recent).
3. Entry contains `valueQuantity.value = 5.4` and `effectiveDateTime = "2023-11-02T06:53:00+00:00"`.
4. Return `FINISH([5.4, "2023-11-02T06:53:00+00:00"])`.

**When the bundle is empty:**
1. `GET /Observation?code=A1C&patient=S2016972` → Bundle `total = 0`.
2. Apply *Pattern 2* → `FINISH([-1])`.
3. The next skill (`conditional_lab_result_age_order`) sees the missing flag and creates a ServiceRequest for a new HbA1c.

## Success Indicators
- `FINISH` payload contains a two‑element array `[number, "ISO‑8601"]` for bundles with results.
- For empty bundles, payload is exactly `[-1]` and downstream ordering logic is triggered.
- No units or free‑text appear in the numeric element.

## Failure Indicators
- Payload includes a string like `"5.4 %"` or concatenated units.
- Timestamp is missing or malformed.
- Agent returns `FINISH([-1])` when a valid Observation exists.
- Downstream ordering skill never runs despite an empty bundle because the missing flag was not set.
