---
description: Validate FINISH output for Observation queries and reject placeholder
  -1 unless explicitly allowed
name: list_output_observation_skill
provenance:
  action: MODIFY
  epoch: 8
  fixes: 3
  parent_version: 4
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task8_29
  - task10_12
  - task9_3
  update_cycle: 0
tags: []
version: 5
---

# Observation Output Validation

## Pattern Description
You must ensure that any FINISH response that originates from an Observation lookup contains a concrete, correctly‑typed result. A valid Observation answer is either:
- a numeric value **and** an ISO‑8601 datetime string (e.g., `[5.2, "2022-08-09T15:33:00+00:00"]`), or
- a single numeric sentinel **only when the task text explicitly states that `-1` is the expected “no‑result” value**.
If the FINISH payload does not meet one of these forms, the skill should abort the current answer, trigger any applicable fallback (e.g., ordering a repeat lab), and never return a raw `-1` placeholder.

## When to Use This Skill
- After a GET request to an `Observation` resource that is intended to provide a lab or vital‑sign value.
- The task description **does not** contain phrasing such as "answer should be -1 if" or "use -1 when no measurement is available".
- The agent is about to call `FINISH` with a list that contains `-1` or any non‑numeric / non‑datetime elements.

## Common Failure Patterns
- `FINISH([-1])` returned for a lab query where the task expects a value and a date.
- `FINISH(["5.2", "2022-08-09"])` – value is a string, date is not ISO‑8601.
- `FINISH([5.2])` – missing required datetime component.
- Returning a numeric sentinel when the task never mentioned `-1` as a valid answer.

## Recommended Patterns
**Pattern 1: Primary validation**
1. Parse the task description. If it contains the exact phrase `"should be -1 if"` (case‑insensitive), mark `-1` as an allowed sentinel.
2. Inspect the FINISH payload:
   - If it is a two‑element list, verify that the first element is a number and the second element matches the ISO‑8601 regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[Z+].*$`.
   - If it is a single‑element list containing `-1`, allow it **only** when step 1 marked the sentinel as permitted.
3. If validation fails, abort the current FINISH and proceed to the appropriate fallback (e.g., create a ServiceRequest for a repeat lab).

**Pattern 2: Fallback for missing or invalid data**
- When the Observation bundle has `total = 0` **or** validation in Pattern 1 fails, automatically invoke the conditional ordering skill (if a LOINC code for ordering is provided in the task context) to place a new lab request.
- After the POST succeeds, call `FINISH` with the newly created order’s identifier **or** with a placeholder that matches the task’s expected format (e.g., `["order‑placed"]`).

**Pattern 3: Formatting the final output**
- Always output a JSON‑compatible list.
- Do **not** embed explanatory text, units, or free‑form strings inside the list.
- Example of correct output: `FINISH([5.2, "2022-08-09T15:33:00+00:00"])`
- Example of wrong output: `FINISH(["5.2 mmol/L", "2022‑08‑09"])`

## Example Application
**Task:** "What’s the last HbA1C value for patient S123456 and when was it recorded? If the result is older than 1 year, order a new test."

**Step‑by‑step:**
1. GET `.../Observation?code=A1C&patient=S123456`.
2. Receive a Bundle with `total = 0`.
3. Validation sees an empty result → fails primary check.
4. Because the task mentions ordering a new test, invoke the conditional ordering skill to POST a `ServiceRequest` for LOINC 4548‑4.
5. FINISH with the ordered value and date **only if** a recent observation existed; otherwise, FINISH with the order confirmation (e.g., `FINISH(["order‑placed"])`).

**Correct output:** `FINISH(["order‑placed"])`
**Incorrect output:** `FINISH([-1])`

## Success Indicators
- FINISH always contains either a numeric‑datetime pair or an allowed `-1` sentinel.
- No task that expects a value returns `FINISH([-1])` unless the description explicitly permits it.
- When observations are missing, a new ServiceRequest is created and its ID (or a clear order flag) appears in the FINISH payload.

## Failure Indicators
- FINISH payload includes `-1` for a task that never mentioned `-1` as a valid answer.
- FINISH contains strings, units, or malformed dates.
- Observation bundles with `total = 0` are ignored without triggering the conditional ordering fallback.
