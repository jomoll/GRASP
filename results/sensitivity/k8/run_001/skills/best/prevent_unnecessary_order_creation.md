---
description: Avoid creating ServiceRequest orders unless the task explicitly requires
  and the ordering condition is satisfied
name: prevent_unnecessary_order_creation
provenance:
  action: ADD
  epoch: 0
  fixes: 13
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task5_16
  - task9_28
  - task8_14
  update_cycle: 1
tags: []
version: 1
---

# Prevent Unnecessary ServiceRequest Creation

## Pattern Description
You must only create a `ServiceRequest` (order) when the instruction explicitly asks for an order **and** any conditional clause (e.g., "if the result is older than 1 year") is satisfied. First retrieve the necessary data, evaluate the condition, and only then issue the POST. If the task only asks for a value or a report, do **not** place an order.

## When to Use This Skill
- The instruction contains a phrase like "If …, order …" or "place a new … test".
- The instruction asks only for a value/report with no ordering language.
- After a GET request you have the data needed to evaluate the ordering condition (e.g., a lab result date, a lab value, a medication level).

## Common Failure Patterns
- Posting a `ServiceRequest` before checking the condition (e.g., ordering HbA1c without verifying the result date).
- Creating an order when the instruction never mentions ordering (e.g., only "What’s the last HbA1c value?").
- Skipping the order when the condition is true because the agent assumed the request was informational only.

## Recommended Patterns
**Pattern 1: Detect ordering intent**
1. Scan the task description for keywords: `order`, `place`, `request`, `if … order`, `if … place`.
2. If none are found, set `should_order = false` and skip any POST.

**Pattern 2: Retrieve and evaluate condition**
1. Perform the required GET(s) to obtain the data (e.g., Observation with `code=A1C`).
2. Extract the relevant field:
   - For date‑based conditions: `effectiveDateTime` or `issued`.
   - For value‑based conditions: `valueQuantity.value`.
3. Compute the condition (e.g., `date < now - 1 year`).
4. Set `should_order = true` only if the condition evaluates to true.

**Pattern 3: Conditional POST**
1. If `should_order` is true, construct the `ServiceRequest` JSON exactly as required (include `code.coding.system`, `code.coding.code`, `authoredOn`, `status`, `intent`, `subject.reference`).
2. POST to `/fhir/ServiceRequest`.
3. Verify the POST succeeded before proceeding.
4. If `should_order` is false, do **not** issue any POST.

**Pattern 4: Finish output**
1. After all required GETs and any conditional POST, call `FINISH` with only the answer elements requested (e.g., `[value, "date"]`).
2. Do not embed order confirmation text in the FINISH payload.

## Example Application
**Task:** "What’s the last HbA1c value for patient S0722219 and when was it recorded? If the result date is > 1 year old, order a new HbA1c lab test."

**Step‑by‑step:**
1. Detect ordering intent → present.
2. GET `Observation?code=A1C&patient=S0722219`.
3. Extract `valueQuantity.value = 6.5` and `effectiveDateTime = 2022-03-08T08:14:00+00:00`.
4. Compare date to current time (2023‑11‑13). Difference > 1 year → `should_order = true`.
5. POST `ServiceRequest` with LOINC `4548-4` (HbA1c) only because `should_order` is true.
6. FINISH `[6.5, "2022-03-08T08:14:00+00:00"]`.

## Success Indicators
- No `POST /ServiceRequest` when the task lacks ordering language.
- `POST /ServiceRequest` appears **only** when the conditional clause evaluates to true.
- `FINISH` contains exactly the values the task asked for, without extra explanatory text.

## Failure Indicators
- A `POST /ServiceRequest` is sent despite `should_order = false`.
- The agent posts an order before evaluating the condition.
- The FINISH output includes order status or explanatory sentences instead of the pure answer format.
