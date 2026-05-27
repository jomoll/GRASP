---
description: Avoid returning placeholder [-1] when a required Observation is missing;
  decide ordering and output correctly.
name: missing_observation_placeholder_handling
provenance:
  action: ADD
  epoch: 4
  fixes: 15
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task9_5
  - task9_6
  - task10_10
  - task10_24
  - task10_8
  - task10_18
  - task8_7
  - task9_9
  - task9_14
  - task1_20
  update_cycle: 0
tags: []
version: 1
---

# Missing Observation Placeholder Handling

## Pattern Description
When a task asks for the latest value of a lab or measurement, the agent often queries the Observation endpoint. If the search returns an empty bundle, the agent may be tempted to return a placeholder value like `[-1]`. This placeholder is ambiguous and can cause downstream logic to misinterpret the result, especially when the instruction includes conditional ordering (e.g., "order a new test if the result is older than one year"). The pattern teaches the agent to treat an empty result set as *no recent data* and to follow the task‑specific decision flow instead of emitting a generic placeholder.

## When to Use This Skill
- When a GET `/Observation` (or similar) returns `total: 0`.
- The task expects a numeric value **or** a date, and also contains a conditional order clause (e.g., "if older than X, order a new test").
- The expected answer format is a JSON array of values **or** an empty array, never a sentinel like `-1`.

## Common Failure Patterns
- Returning `FINISH([-1])` after an empty Observation bundle.
- Omitting the required ServiceRequest creation when the instruction says to order a new test.
- Mixing placeholder `-1` with a valid array (e.g., `FINISH([value, -1])`).

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. After the GET request, inspect `bundle.total`.
2. If `total == 0`, treat the observation as *missing*.

**Pattern 2: Follow task‑specific conditional logic**
- **If the task only wants a value** (e.g., magnesium level within 24 h) and specifies `-1` for "not available", return `FINISH([-1])` **only** for that task type.
- **If the task includes an ordering rule** (e.g., HbA1c older than 1 year or missing), **do not** return `-1`. Instead:
  - Create the appropriate `ServiceRequest` (use the LOINC code supplied in the context).
  - After posting, call `FINISH([])` to indicate no numeric answer is available.

**Pattern 3: Consistent output formatting**
- For tasks that expect a numeric answer, output a JSON array of numbers (e.g., `[7.2]`).
- For tasks that expect *no* answer because a new order was placed, output an empty array `[]`.
- Never mix sentinel values with real data.

## Example Application
**Task:** "What’s the last HbA1C value for patient S0789363 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0789363`
2. Inspect the bundle: `total == 0` → no recent result.
3. Because the instruction says to order a new test when the result is >1 year **or missing**, create a `ServiceRequest` with LOINC `4548-4`.
4. `POST http://localhost:8080/fhir/ServiceRequest { … }`
5. Call `FINISH([])` – an empty array signals that no numeric HbA1c is available, and the order has been placed.

**Correct output:** `FINISH([])`
**Wrong output:** `FINISH([-1])` (placeholder) or `FINISH([value, -1])`.

## Success Indicators
- The agent posts a `ServiceRequest` when the instruction requires ordering and the Observation bundle is empty.
- The final `FINISH` call contains either a proper numeric array or an empty array, never `[-1]` for tasks that include ordering logic.

## Failure Indicators
- The agent returns `FINISH([-1])` after an empty Observation bundle for a task that mentions ordering.
- The agent skips the required `POST` for a new test despite the missing or stale result.
- The final output mixes placeholder values with real data.
