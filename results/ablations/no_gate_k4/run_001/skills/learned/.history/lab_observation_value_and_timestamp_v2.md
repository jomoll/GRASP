---
description: "Add date\u2011range filter enforcement for recency\u2011aware lab queries"
name: lab_observation_value_and_timestamp
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_16
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags:
- date_filter
- lab_observation
- recency
version: 2
---

# Lab Observation Value and Timestamp with Date‑Range Filter Enforcement

## Pattern Description
You must extract the most recent numeric lab result **and** its recording timestamp, but only after ensuring the Observation search is limited to the time window required by the task. Many tasks ask for a value *if it is recent* (e.g., “within the last 24 hours”) or *if it is older than X* (e.g., “greater than 1 year old, order a new test”). This skill adds the appropriate `date=ge…` (and optional `date=le…`) parameters to the GET request before any extraction occurs, guaranteeing that stale or missing data do not cause incorrect answers or unnecessary orders.

## When to Use This Skill
- The instruction references a lab Observation **and** a recency condition (e.g., “within last 24 hours”, “older than 1 year”, “if the result date is greater than …”).
- The task provides a known observation code (e.g., `A1C`, `MG`, `K`).
- You need to decide whether to order a new test based on the age of the existing result.

## Common Failure Patterns
- GET request omits any `date` filter, returning all historic observations; the agent then returns `null` or an outdated value.
- Agent orders a replacement test without first confirming the result is out‑of‑date because the date was never inspected.
- The extracted timestamp is ignored, leading to wrong decision logic.

## Recommended Patterns
**Pattern 1: Derive the required date window from the task**
1. Scan the task text for phrases like:
   - "within last X hours/days"
   - "greater than X year(s) old"
   - "older than X months"
2. Compute the ISO‑8601 start datetime (`start_dt`) as `now - X` using the task’s current time context.
3. If the task also limits an upper bound (e.g., “recorded before …”), compute `end_dt` = now or the specified upper bound.
4. Build the GET URL:
   ```
   GET {base}/Observation?code={CODE}&patient={MRN}&date=ge{start_dt}&date=le{end_dt}
   ```
   - Omit the `date=le…` clause if no upper bound is needed.
5. Issue the GET request **before** any extraction.

**Pattern 2: Fallback if the original query lacked a date filter**
1. Detect that the last issued GET for the same `code`/`patient` did not contain `date=` parameters.
2. Re‑issue the GET with the computed date filter (as in Pattern 1).
3. Continue with extraction on the filtered bundle.

**Pattern 3: Extraction and decision**
1. From the first entry in the returned Bundle, read:
   - `valueQuantity.value` → numeric result.
   - `effectiveDateTime` (or `issued` if `effectiveDateTime` missing) → timestamp.
2. Return the pair as `FINISH([value, "timestamp"])`.
3. If the task requires ordering when the result is older than a threshold, compare the extracted timestamp to the threshold and, if needed, POST a `ServiceRequest` using the provided LOINC code.

## Example Application
**Task:** “What’s the last HbA1C value for patient S2823623 and when was it recorded? If the result is older than 1 year, order a new HbA1C lab test.”

**Step‑by‑step:**
1. Current time = `2023‑11‑13T10:15:00+00:00`. Compute `start_dt = 2022‑11‑13T10:15:00+00:00` (now minus 1 year).
2. Issue GET:
   ```
   GET http://localhost:8080/fhir/Observation?code=A1C&patient=S2823623&date=ge2022-11-13T10:15:00+00:00
   ```
3. Extract `valueQuantity.value = 5.0` and `effectiveDateTime = "2023-11-09T10:06:00+00:00"`.
4. Return `FINISH([5.0, "2023-11-09T10:06:00+00:00"])`.
5. Since the timestamp is newer than the 1‑year cutoff, **do not** create an order.

**Success Indicators**
- The GET URL contains a `date=ge…` (and optionally `date=le…`) clause.
- FINISH outputs a numeric value and an ISO‑8601 timestamp.
- An order is only posted when the extracted timestamp fails the recency check.

**Failure Indicators**
- GET URL lacks any `date=` parameter.
- FINISH returns `null` or a value without a timestamp.
- An order is placed without verifying the result’s age.
