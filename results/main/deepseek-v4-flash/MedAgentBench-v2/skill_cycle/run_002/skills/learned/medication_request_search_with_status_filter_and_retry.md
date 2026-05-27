---
description: When searching MedicationRequest, always include status=active and retry
  with broader parameters if empty
name: medication_request_search_with_status_filter_and_retry
provenance:
  action: ADD
  epoch: 4
  fixes: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task2_17
  - task8_14
  - task2_25
  - task6_26
  - task2_28
  - task4_23
  - task3_3
  - task2_6
  - task8_9
  - task4_28
  update_cycle: 1
tags:
- medication-request
- status-filter
- retry-strategy
- dvt-prophylaxis
version: 1
---

# MedicationRequest Search with Status Filter and Retry

## Pattern Description

When searching for medication orders (MedicationRequest), you must always include the `status=active` filter to avoid retrieving discontinued, completed, or cancelled orders that would lead to incorrect conclusions. Additionally, when the initial search returns zero results or no relevant results, you must retry with broader parameters before concluding no orders exist.

This skill applies to any task that requires verifying, counting, or acting upon active medication orders — such as DVT prophylaxis checks, opioid reviews, or vaccine order verification. The core lesson is that MedicationRequest searches require explicit status filtering and systematic retry logic, unlike Observation searches which may not need status filtering.

## When to Use This Skill

- When performing a GET on MedicationRequest to find active orders for a specific medication class (e.g., heparin, opioids, anticoagulants)
- When the task asks to "verify exactly one active order exists" or "check active orders"
- When the initial MedicationRequest search returns zero results but the task expects a medication to exist
- When constructing a MedicationRequest search and you need to ensure you're only seeing current, actionable orders

## Common Failure Patterns

- Searching `GET /MedicationRequest?patient=X` without `status=active` — returns all orders including discontinued, causing incorrect counts
- Searching with `text=heparin` as a fallback instead of retrying with broader date range or removing the text filter
- Concluding "no orders exist" after a single search without trying broader parameters (no date filter, no status filter)
- Using `text` parameter combined with `date` parameter — this causes a 400 error on some FHIR servers

## Recommended Patterns

**Pattern 1: Always include status=active in initial search**
When searching MedicationRequest, always append `&status=active` to the query. This ensures you only see orders that are currently in effect.

CORRECT: `GET /MedicationRequest?patient=S6415739&status=active`
WRONG:   `GET /MedicationRequest?patient=S6415739` (returns all statuses)

**Pattern 2: Retry with broader parameters when results are empty**
If the initial search returns zero results or no relevant results:
1. First retry without any `text` parameter (text+date combination causes 400 errors)
2. Then retry without any date filter to catch older orders
3. Then retry with a very broad date range (e.g., `date=ge2000-01-01`)

CORRECT sequence:
- `GET /MedicationRequest?patient=S6415739&status=active` (initial)
- If empty: `GET /MedicationRequest?patient=S6415739&status=active&date=ge2000-01-01` (broader date)

WRONG: `GET /MedicationRequest?patient=S6415739&text=heparin` (narrowing instead of broadening)

**Pattern 3: Verify results by inspecting medication fields**
After retrieving results, inspect each entry's `medicationCodeableConcept` or `medicationReference` to confirm it matches the target medication. Do not rely solely on `text` search.

## Example Application

**Task:** "Verify that patient S6415739 has exactly one active DVT prophylaxis order. If there are zero orders, create one. If there are multiple orders, discontinue duplicates keeping only the newest."

**Step-by-step:**

1. Issue initial search with status filter:
   `GET /MedicationRequest?patient=S6415739&status=active`

2. If results are empty, retry with broader date range:
   `GET /MedicationRequest?patient=S6415739&status=active&date=ge2000-01-01`

3. Inspect each entry's `medicationCodeableConcept.coding` for heparin/DVT prophylaxis codes (e.g., NDC codes for heparin 5000 units SC).

4. Count matching entries:
   - If 0: POST a new MedicationRequest for heparin 5000 units SC q8h prophylaxis
   - If 1: FINISH confirming exactly one active order exists
   - If >1: Discontinue all but the newest (by `authoredOn`), keeping only the most recent

CORRECT output: `FINISH(["Patient S6415739 has exactly 1 active DVT prophylaxis order (heparin 5000 units SC q8h). No action needed."])`
WRONG output:   `FINISH(["No heparin or DVT prophylaxis orders found."])` (when orders exist but weren't filtered by status)

## Success Indicators

- Agent includes `status=active` in all MedicationRequest searches
- Agent retries with broader parameters (no date filter, or very broad date range) before concluding no orders exist
- Agent correctly counts active orders and takes appropriate action (create, keep, or discontinue)
- Agent does not use `text` parameter combined with `date` parameter (avoids 400 errors)

## Failure Indicators

- Agent searches without `status=active` and misses active orders
- Agent searches with `text=heparin` as a fallback instead of broadening date range
- Agent concludes "no orders" after a single search without retrying
- Agent gets a 400 error from combining `text` and `date` parameters and does not recover
- Agent returns incorrect order counts due to including discontinued or completed orders
