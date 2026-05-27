---
description: "Avoid ordering a new HbA1c when a recent result (\u2264\u202F1\u202F\
  year) already exists"
name: prevent_unnecessary_hba1c_order
provenance:
  action: ADD
  epoch: 4
  fixes: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_27
  - task9_20
  - task10_13
  - task9_1
  - task9_8
  - task9_28
  - task5_7
  - task10_20
  - task4_4
  - task10_15
  update_cycle: 1
tags: []
version: 1
---

# Prevent Unnecessary HbA1c Order

## Pattern Description
You must ensure that a new HbA1c (LOINC 4548‑4) lab order is only placed when the patient does not have a **most recent** HbA1c observation dated within the past 365 days. The pattern first extracts the latest Observation with `code=A1C` (or the LOINC code) for the target patient, compares its `effectiveDateTime` (or `issued` if `effectiveDateTime` is missing) to the current context time, and decides whether to order or simply report the existing value.

## When to Use This Skill
- When a task asks for "the last HbA1c value and its date; if the result is older than 1 year, order a new HbA1c test".
- When the agent has already performed a `GET /Observation?code=A1C&patient=Patient/<id>` and received a Bundle of results.
- When the task expects the answer in the form `FINISH([value, "date-time"])` and **must not** create a ServiceRequest if the existing result is recent.

## Common Failure Patterns
- Ordering a ServiceRequest **before** checking the recency of the existing observation.
- Using the wrong date field (`issued` vs `effectiveDateTime`) leading to an incorrect age calculation.
- Comparing dates without normalising time zones, causing a false‑positive "older than 1 year".
- Returning the value as a string with a percent sign (e.g., `"5.8%"`) instead of a numeric value.
- Emitting `FINISH([-1])` or an empty array when a recent result exists.

## Recommended Patterns
**Pattern 1: Extract and evaluate the most recent HbA1c**
1. From the Observation Bundle, locate entries where `resource.code.coding` contains `code="4548-4"` (or `code="A1C"`).
2. For each matching entry, read `effectiveDateTime` if present; otherwise fall back to `issued`.
3. Sort the dates descending and pick the first (most recent) date.
4. Parse the date as an ISO‑8601 timestamp and compare it to the current context time (`now`).
5. Compute the difference in days. If `difference <= 365`, the result is recent.

**Pattern 2: Decision logic**
- **If recent**: 
  - Extract the numeric value from `valueQuantity.value` (or from `valueString` after stripping non‑numeric characters). 
  - Return `FINISH([value, "<ISO‑date>"])` **without** creating a ServiceRequest.
- **If no observation** **or** the most recent date is older than 365 days:
  - Proceed to create a `ServiceRequest` for HbA1c using LOINC 4548‑4.
  - After successful POST, return the newly ordered status **or** the older value with its date if the task also asks for it.

**Pattern 3: Formatting rules**
- Always output the numeric value **without** a trailing `%` sign.
- Date must be an ISO‑8601 string exactly as received (e.g., `"2022-09-09"` or `"2023-11-09T10:06:00+00:00"`).
- The FINISH payload must be a JSON array of two elements: `[value, "date"]`.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6521727 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1c lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=Patient/S6521727`
2. From the returned Bundle, find the Observation with the newest `effectiveDateTime` (e.g., `2022-09-09`).
3. Compute days between `2022-09-09` and the context time `2023-11-13T10:15:00+00:00` → 399 days > 365.
4. Because it is older, `POST` a `ServiceRequest` with LOINC 4548‑4.
5. Return `FINISH([5.8, "2022-09-09"])` (the older value) **or** the newly ordered status as required.

**If the most recent date had been `2023-03-01` (≈ 255 days):**
- Skip the POST.
- Return `FINISH([5.8, "2023-03-01"])`.

## Success Indicators
- No `POST /ServiceRequest` is issued when the most recent HbA1c date is ≤ 365 days old.
- The FINISH payload contains a numeric value and an ISO‑8601 date string.
- The agent logs show the date comparison step and the decision to skip ordering.

## Failure Indicators
- A ServiceRequest for HbA1c is posted despite a recent observation.
- The FINISH payload includes a string with a percent sign or omits the date.
- The agent reports `FINISH([-1])` or an empty array when a recent result exists.
- Date comparison uses the wrong field (`issued` when `effectiveDateTime` is present) and yields an incorrect age.
