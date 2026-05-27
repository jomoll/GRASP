---
description: "Require appropriate FHIR date filters for any query that depends on\
  \ recent or time\u2011windowed data"
name: enforce_date_filter_on_time_bound_queries
provenance:
  action: ADD
  epoch: 0
  fixes: 4
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task1_10
  - task3_27
  - task9_1
  - task3_16
  - task1_20
  - task6_26
  - task3_3
  - task8_26
  - task2_22
  - task3_30
  update_cycle: 1
tags:
- date_filter
- temporal_logic
- procedure
- observation
- query_validation
version: 1
---

# Enforce Date Filters on Time‑Bound FHIR Queries

## Pattern Description
You must ensure that every FHIR `GET` request used to answer a task that involves a time constraint includes an explicit `date` filter that matches the required window. This prevents the agent from using stale or unrelated records when the instruction asks for "most recent", "past X hours", "more than 12 months ago", or any similar temporal condition. The rule applies to all resource types (Procedure, Observation, MedicationRequest, ServiceRequest, etc.) whenever the task description or context mentions a time‑based decision.

## When to Use This Skill
- The instruction asks for a value **within a recent window** (e.g., "average heart rate over the past 6 hours").
- The instruction asks to act based on **age of a prior event** (e.g., "if the CT was performed more than 12 months ago").
- The instruction checks **duration of a device or procedure** (e.g., "catheter in place for more than 48 hours").
- The instruction compares a date to the **current time** (e.g., "last influenza vaccine > 365 days ago").
- Any task that includes phrases like *past X hours*, *last Y days*, *more than Z months*, *older than*, *duration*, or *since*.

## Common Failure Patterns
- `GET /Procedure?code=IMGCT0491,IMGIL0001&patient=S12345` – **no `date` parameter** at all.
- `GET /Observation?code=HEARTRATE&patient=S12345` – missing `date` range for hourly averages.
- Using a placeholder like `date=ge1900-01-01` which is effectively unfiltered.
- Adding a `date` filter that does **not** reflect the required window (e.g., `date=ge2022-01-01` for a "past 6‑hour" calculation).

## Recommended Patterns
**Pattern 1: Determine required window and add precise date filter**
1. Parse the task description to extract the required time window (e.g., "past 6 hours", "more than 12 months", "48 hours").
2. Compute the cutoff datetime relative to the current time supplied in the task context.
3. Append a `date` query parameter that exactly matches the window:
   - For "past N hours": `date=ge{ISO8601_timestamp_N_hours_ago}`
   - For "more than N months ago": `date=le{ISO8601_timestamp_N_months_ago}` (or combine `ge`/`le` as needed).
4. Include any other required filters (e.g., `code`, `patient`, `category`).

**CORRECT**: `GET http://localhost:8080/fhir/Observation?code=HEARTRATE&patient=S12345&date=ge2023-11-07T16:47:00+00:00`
**WRONG**: `GET http://localhost:8080/fhir/Observation?code=HEARTRATE&patient=S12345`

**Pattern 2: Verify date filter before issuing the request**
- Inspect the constructed URL string.
- If the `date=` component is missing or does not match the required window, **block** the request and raise a diagnostic message (e.g., `ERROR: Missing or incorrect date filter for time‑bound query`).
- Only proceed to `GET` when the filter is present and correct.

**Pattern 3: Fallback when date cannot be determined**
- If the task does not provide a current timestamp, request clarification before querying.
- Do not guess a default wide range; instead, respond with `NEED_INFO` indicating the required time reference.

## Example Application
**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S6500497."

**Step‑by‑step:**
1. Extract window sizes: 6 h and 12 h.
2. Current time from context: `2023-11-07T22:47:00+00:00`.
3. Compute cutoffs:
   - 6 h ago → `2023-11-07T16:47:00+00:00`
   - 12 h ago → `2023-11-07T10:47:00+00:00`
4. Issue two GETs with precise filters:
   - `GET .../Observation?code=HEARTRATE&patient=S6500497&date=ge2023-11-07T16:47:00+00:00`
   - `GET .../Observation?code=HEARTRATE&patient=S6500497&date=ge2023-11-07T10:47:00+00:00`
5. Extract `valueQuantity.value` from each bundle, compute averages, and construct output.

**CORRECT output:** `FINISH([78.2, 80.5])`
**WRONG output:** `FINISH(["Average heart rate over past 6 hours: 78 bpm"] )` (missing second window, no date filter used).

## Success Indicators
- Every `GET` URL for a time‑bound task contains a `date=` parameter that exactly matches the required window.
- The agent does not produce a `FINISH` answer until the filtered data has been retrieved and processed.
- Logs show the computed cutoff timestamps used in the request.

## Failure Indicators
- A `GET` request is sent without a `date` filter for a task that mentions a time window.
- The agent answers with a statement like "No heart rate observations found" when the query lacked the required date range.
- The agent proceeds to order or report based on a stale date (e.g., using `date=ge1900-01-01`).
