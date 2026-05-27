---
description: Prevent ordering a new lab when a recent, parsable result already exists
name: lab_result_recency_check
provenance:
  action: MODIFY
  epoch: 2
  fixes: 10
  parent_version: 2
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - task8_26
  - task1_6
  - task10_13
  - task9_20
  - task8_9
  - task10_20
  - task10_27
  - task10_18
  - task8_23
  - task9_3
  update_cycle: 0
tags: []
version: 3
---

# Lab Result Recency Check and Order Suppression

## Pattern Description
You must verify that a lab result is both parsable **and** recent before deciding to order a repeat test. The core capability is to extract the latest numeric value and its `effectiveDateTime` (or `issued`) from a bundle of `Observation` resources, compare the date to the task's reference time, and **block any ServiceRequest creation** for that lab if the result is within the allowed freshness window (e.g., 1 year). This pattern stops unnecessary duplicate orders and keeps the care plan clean.

## When to Use This Skill
- When a task asks for "the last *X* value and to order a new *X* test if the result is older than *N* days/years".
- When the agent has already performed a `GET /Observation?code=...&patient=...` and holds the bundle response.
- When the agent is about to construct a `ServiceRequest` for the same LOINC code.

## Common Failure Patterns
- Extracting the value but ignoring the timestamp, leading to unconditional ordering.
- Using the wrong date field (`effectiveDateTime` vs `issued`) causing the recency check to always appear false.
- Returning `-1` for missing numeric value **and** still ordering because the date check is not gated on a successful numeric extraction.
- Posting a `ServiceRequest` before the recency logic runs, so the order is always placed.

## Recommended Patterns
**Pattern 1: Extract latest parsable result**
1. From the Observation bundle, iterate entries sorted by `effectiveDateTime` (or `issued` if the former is missing).
2. For each entry, attempt to parse `valueQuantity.value` **or** a numeric component in `valueString`.
3. Stop at the first entry where a numeric value is successfully parsed.
4. Record `latest_value` and `latest_date`.

```json
CORRECT: {
  "value": 5.8,
  "date": "2022-09-09T10:00:00+00:00"
}
WRONG: {
  "value": "5.8%",
  "date": null
}
```

**Pattern 2: Recency comparison**
1. Convert `latest_date` to a datetime object.
2. Compute `age_days = reference_time - latest_date`.
3. If `age_days <= allowed_days` (e.g., 365 for 1 year) **and** `latest_value` is not null, set `suppress_order = true`.
4. Otherwise `suppress_order = false`.

**Pattern 3: Order suppression rule**
- **Before** constructing any `ServiceRequest` for the same LOINC code, check `suppress_order`.
- If `true`, **skip** the POST entirely and finish with the extracted value/date only.
- If `false`, proceed to create the `ServiceRequest` as usual.

```json
CORRECT flow:
1. GET Observation bundle → extract 5.8% on 2022‑09‑09.
2. age = 340 days (< 365) → suppress_order = true.
3. No ServiceRequest POST.
4. FINISH([5.8, "2022-09-09T10:00:00+00:00"]).

WRONG flow:
1. Extract value.
2. Skip date check.
3. POST ServiceRequest regardless → duplicate order.
```

## Example Application
**Task:** "What’s the last HbA1C value for patient S6500497 and when was it recorded? If the result is > 1 year old, order a new HbA1c test."

**Step‑by‑step:**
1. `GET /Observation?code=A1C&patient=S6500497` → bundle with three entries.
2. Sort entries by `effectiveDateTime` descending.
3. Parse the first entry: `valueQuantity.value = 5.2`, `effectiveDateTime = 2022‑08‑09T09:30:00+00:00`.
4. Compute `age = 2023‑11‑13 - 2022‑08‑09 ≈ 460 days` → > 365, so `suppress_order = false`.
5. Because `suppress_order` is false, construct and POST a `ServiceRequest` with LOINC 4548‑4.
6. `FINISH([5.2, "2022-08-09T09:30:00+00:00"])`.

If the same patient had a result dated `2023‑03‑01`, step 4 would set `suppress_order = true` and the POST would be omitted.

## Success Indicators
- The agent finishes with the numeric value and date **without** a `POST /ServiceRequest` when a recent result exists.
- Log shows `suppress_order = true` and the POST step is skipped.
- The final output contains only the extracted value/date (or `-1` when no recent result).

## Failure Indicators
- A `POST /ServiceRequest` appears in the trace even though `age_days` is ≤ allowed threshold.
- The agent reports a value but still includes a note like "New test ordered".
- The extracted date is ignored in the decision logic, leading to unconditional ordering.
