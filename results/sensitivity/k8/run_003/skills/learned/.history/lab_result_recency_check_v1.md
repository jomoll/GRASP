---
description: Check observation date and decide whether to order a repeat lab based
  on a recency threshold
name: lab_result_recency_check
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task1_10
  - task9_1
  - task10_27
  - task5_3
  - task10_18
  - task1_20
  - task9_6
  - task9_28
  - task9_20
  - task1_7
  update_cycle: 1
tags:
- lab
- recency
- ordering
- service_request
version: 1
---

# Lab Result Recency Check for Ordering

## Pattern Description
You must verify how recent the most recent observation for a given LOINC (or other) code is before deciding to order a repeat test. The core capability is to extract the latest `effectiveDateTime` (or `issued` when `effectiveDateTime` is absent), compare it to the task's reference time (usually the current time supplied in the task context), and apply a configurable recency threshold (e.g., 1 year). If the latest result is newer than the threshold, **do not** create a `ServiceRequest`; simply report the value and its date. If the result is older than the threshold **or** no result exists, create the appropriate `ServiceRequest` and report the missing/old status.

## When to Use This Skill
- When a task asks for the "last <lab> value" **and** includes a conditional ordering clause such as "If the result is older than X, order a new test".
- When the instruction mentions a specific code (e.g., LOINC `4548-4` for HbA1c) and a time‑based rule.
- When the agent is about to POST a `ServiceRequest` for a lab repeat and must first verify the recency of existing results.

## Common Failure Patterns
- Ignoring the observation date and always ordering a repeat test.
- Using the wrong timestamp field (`issued` vs `effectiveDateTime`) leading to inaccurate age calculation.
- Comparing dates as strings instead of proper ISO‑8601 date objects, causing off‑by‑one‑day errors.
- Applying the threshold to the *first* entry in the bundle instead of the most recent one.
- Posting a `ServiceRequest` even when a recent result exists, resulting in `unnecessary_service_request_created` failures.

## Recommended Patterns
**Pattern 1: Extract and evaluate the most recent result**
1. `GET {api_base}/Observation?code={code}&patient={patientId}`
2. From the returned `Bundle`, locate the entry with the greatest `effectiveDateTime` (or `issued` if `effectiveDateTime` is missing).
3. Parse the timestamp into a datetime object.
4. Compute the difference between the task's reference time (provided in the task context) and the result timestamp.
5. If `difference <= threshold` (e.g., 365 days), **skip** ordering.
6. If `difference > threshold` **or** no entries are returned, proceed to Pattern 2.

**Pattern 2: Conditional ServiceRequest creation**
- Build a `ServiceRequest` with the appropriate `code` (LOINC or SNOMED) and `subject` reference.
- Include a clear `note.text` explaining why the order is placed (e.g., "No recent HbA1c within 1 year; ordering repeat test.").
- POST the resource only when Pattern 1 indicates the need.

**Pattern 3: FINISH output formatting**
- If a recent result exists: `FINISH(["{value}{unit} recorded on {date}"])`.
- If no recent result: `FINISH([-1])` **or** a descriptive message when the task expects a string.

## Example Application
**Task:** "What’s the last HbA1C value for patient S6521727 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=4548-4&patient=S6521727`
2. Identify the entry with the newest `effectiveDateTime` → `2022-09-09T08:30:00+00:00`.
3. Compute days between task reference time `2023-11-13T10:15:00+00:00` and `2022-09-09` → 430 days (>365).
4. Since > 1 year, construct a `ServiceRequest` for LOINC `4548-4` with a note explaining the ordering reason and POST it.
5. `FINISH(["5.8% recorded on 2022-09-09"])` (or `FINISH([-1])` if the task expects a sentinel value).

**Correct vs. Incorrect:**
- **CORRECT**: No `ServiceRequest` is posted when the date difference is ≤ 365 days.
- **WRONG**: Posting a `ServiceRequest` regardless of the date, leading to unnecessary orders.

## Success Indicators
- The agent posts a `ServiceRequest` **only** when the most recent observation is older than the threshold or absent.
- The FINISH output contains the correct value and date when a recent result exists.
- No `unnecessary_service_request_created` warnings appear in the log.

## Failure Indicators
- A `ServiceRequest` is posted even though a recent observation (≤ threshold) was found.
- The agent reports an old result but still returns `-1` or an empty array.
- Date parsing errors cause the agent to treat a recent result as missing.
