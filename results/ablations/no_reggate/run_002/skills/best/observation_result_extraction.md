---
description: Extracts numeric value and timestamp from Observation bundles **only
  when the bundle contains at least one result**. If the bundle is empty, the skill
  does **not** emit a FINISH response, allowing downstream logic (e.g., ordering a
  new test) to run. This prevents premature sentinel `[-1]` outputs on tasks that
  require further handling when no observation is present.
name: observation_result_extraction
provenance:
  action: ADD
  epoch: 2
  fixes: 5
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task5_19
  - task5_3
  - task1_20
  - task10_10
  - task9_1
  - task9_20
  - task9_22
  update_cycle: 1
tags: []
version: 1
---

# Observation Result Extraction (Guarded)

## Trigger Condition
- Activate **only** when the GET response is a FHIR `Bundle` and `Bundle.total > 0`.
- If `Bundle.total == 0`, **do not** produce a FINISH response; simply exit the skill so other rules can handle the "no result" case (e.g., create a ServiceRequest).

## Core Extraction Rule (when total > 0)
1. Identify the most recent entry (usually `entry[0].resource`).
2. Extract the measured value:
   - If `valueQuantity` exists → use `valueQuantity.value` (numeric) and optionally `valueQuantity.unit`.
   - Else if `valueString` exists → attempt to parse a numeric value from the string.
3. Extract the timestamp:
   - Prefer `effectiveDateTime`.
   - If missing, fall back to `issued`.
4. Return a two‑element list: `FINISH([value, "timestamp"])`.

## Fallback (no observation)
- When `Bundle.total == 0`, **do nothing** (no FINISH). This lets other skills decide whether to order a new test or respond with a different sentinel.

## Example
**Task:** "What’s the last HbA1C value for patient S0789363 and when was it recorded? If the result is > 1 year old, order a new HbA1c test."
- GET Observation → `Bundle.total == 0` → skill **does not** finish.
- Subsequent rule detects the missing result and creates a ServiceRequest, then may finish with an appropriate response.

## Success Indicators
- FINISH output contains a numeric value and ISO‑8601 timestamp **only** when the bundle has a result.
- No `[-1]` appears for empty bundles; ordering logic can proceed.

## Failure Indicators
- FINISH returns `[-1]` despite `Bundle.total > 0`.
- FINISH is emitted for an empty bundle, preventing downstream ordering steps.

## Tags
[]
