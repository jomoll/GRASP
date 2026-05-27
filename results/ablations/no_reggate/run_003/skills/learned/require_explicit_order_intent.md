---
description: Block ServiceRequest POSTs unless the task explicitly requests an order
  (including conditional orders).
name: require_explicit_order_intent
provenance:
  action: ADD
  epoch: 2
  fixes: 6
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - task8_14
  - task10_20
  - task10_27
  - task9_28
  - task8_29
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task8_13
  update_cycle: 0
tags: []
version: 1
---

# Require Explicit Order Intent

## Pattern Description
You must only create a `ServiceRequest` (POST) when the user instruction **clearly** asks for an order.  This includes direct orders (e.g., "order a HbA1c test") and conditional orders (e.g., "If the last HbA1c is >1 year old, order a new test").  If the instruction is solely a data‑retrieval request, any POST will be considered an unrequested order and must be suppressed.

## When to Use This Skill
- When the task description contains **no ordering keywords** (`order`, `request`, `place`, `referral`, `prescribe`, `order a new`, `order replacement`).
- When the task contains a **conditional ordering clause** (e.g., "If …, order …").
- Before issuing any `POST /ServiceRequest`.

## Common Failure Patterns
- `POST /ServiceRequest` executed for a pure query task (e.g., "What’s the last HbA1c value?").
- Duplicate `POST` when the task only asked for a single order but the agent sends multiple identical requests.
- Missing check of the conditional clause, leading to an order even when the condition is false.

## Recommended Patterns
**Pattern 1: Detect explicit ordering intent**
1. Scan the task description for ordering keywords.
2. If none are found, **abort** any `POST /ServiceRequest` and proceed to `FINISH` with the answer.
3. If keywords are present, continue to step 2.

**Pattern 2: Evaluate conditional ordering**
1. Identify the condition (e.g., date older than 1 year, lab value low).
2. Perform the required GET calls to evaluate the condition.
3. Only issue the `POST /ServiceRequest` **if the condition evaluates to true**.
4. If the condition is false, skip the POST and finish with the retrieved data.

**Pattern 3: Prevent duplicate orders**
1. After a successful `POST`, record the `ServiceRequest.id` in a temporary context.
2. Before any subsequent `POST` for the same patient and same order code, check this context.
3. If an identical request was already sent, skip the second POST.

## Example Application
**Task:** "What’s the last HbA1c value for patient S0722219 and when was it recorded? If the result is >1 year old, order a new HbA1c test."

**Step‑by‑step:**
1. Parse the description – ordering keyword present (`order`).
2. GET `Observation?code=A1C&patient=S0722219`.
3. Extract `effectiveDateTime` from the most recent entry.
4. Compare the date to `now - 1 year`.
5. If the date is older, POST `ServiceRequest` with LOINC 4548‑4; otherwise, do **not** POST.
6. FINISH with `[value, date]` (or `[-1]` if not found).

**Correct output:** `FINISH([6.5, "2022-03-08"])` (POST only if step 5 required).
**Wrong output:** `FINISH([6.5, "2022-03-08"])` **and** an unconditional POST – violates this skill.

## Success Indicators
- No `POST /ServiceRequest` appears in the trace for tasks that lack ordering language.
- When a conditional order is present, the POST occurs **only** after the condition is satisfied.
- Duplicate POSTs for the same order are absent.

## Failure Indicators
- Agent issues a `POST /ServiceRequest` while the task description contains no ordering keywords.
- Agent posts an order even though the evaluated condition is false.
- Multiple identical `POST /ServiceRequest` calls appear for a single task.
