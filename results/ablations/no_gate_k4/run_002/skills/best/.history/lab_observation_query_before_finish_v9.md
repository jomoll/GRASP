---
description: "Return a clear \u201CNo result found\u201D message instead of the \u201C\
  -1\u201D placeholder when a lab query returns no entries"
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 4
  no_gate: true
  parent_version: 8
  triggering_sample_ids:
  - task4_27
  - task9_9
  - task5_16
  - task9_27
  - task2_26
  - task5_19
  - task2_16
  - task10_24
  - task9_14
  - task10_21
  update_cycle: 0
tags: []
version: 9
---

# Lab Observation Query Before Finish

## Pattern Description
You must ensure that any GET request for a lab Observation that returns an empty Bundle is handled explicitly. Instead of propagating the internal placeholder "-1", the agent should produce a human‑readable message indicating that the requested result does not exist. This prevents downstream logic (e.g., ordering a repeat test) from acting on a phantom value.

## When to Use This Skill
- When a task asks for the most recent value of a lab (e.g., HbA1c, magnesium) and the agent issues a `GET /Observation?...` request.
- The response Bundle has `total = 0` (no matching Observation entries).
- The task expects a numeric value **or** a decision based on the recency of that value.

## Common Failure Patterns
- FINISH output contains `"-1"` as the lab value.
- Subsequent conditional ordering logic treats `-1` as a valid numeric result and creates an unnecessary ServiceRequest.
- The placeholder is returned without any explanatory text.

## Recommended Patterns
**Pattern 1: Detect empty result set**
1. After the GET request, inspect `Bundle.total`.
2. If `total == 0` **or** `entry` array is missing/empty, do **not** attempt to extract a value.
3. Set `lab_value = null` and `lab_date = null`.
4. Prepare a FINISH payload that includes a clear message, e.g., `"No HbA1c result found"`.

**Pattern 2: Propagate the missing‑result state**
- When `lab_value` is null, downstream conditional ordering skills must see this and skip ordering.
- Use a sentinel string like `"NO_RESULT"` in the internal variable but never expose it to the user.

**Pattern 3: Formatting the final answer**
- If the task only asks for the value/date, return `FINISH(["No result found"])`.
- If the task also includes a conditional order, return both parts, e.g., `FINISH(["No result found", "No order placed"])`.

## Example Application
**Task:** "What’s the last HbA1C value for patient S0789363 and when was it recorded? If the result is >1 year old, order a new test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0789363&_sort=-date&_count=1`
2. Inspect the returned Bundle – `total: 0`.
3. Set `lab_value = null`, `lab_date = null`.
4. Because there is no result, construct the FINISH output:
   - `FINISH(["No HbA1c result found", "No order placed"])`

**Correct output:** `FINISH(["No HbA1c result found", "No order placed"])`
**Wrong output:** `FINISH(["-1", "HbA1C lab test ordered"])`

## Success Indicators
- The FINISH array never contains the literal string "-1" for lab values.
- Empty bundles are reported as "No … result found".
- Subsequent ordering skills receive a null/absent value and therefore do not create a ServiceRequest.

## Failure Indicators
- FINISH still includes "-1".
- An order is placed even though the GET returned `total: 0`.
- The agent logs a warning about missing fields but proceeds anyway.
