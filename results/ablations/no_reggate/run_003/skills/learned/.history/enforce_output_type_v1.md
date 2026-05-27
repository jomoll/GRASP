---
description: "Guarantee that FINISH returns raw numbers or structured JSON only for\
  \ tasks that explicitly request a value, date, or other structured data. For tasks\
  \ whose primary goal is to place an order, create a referral, or otherwise acknowledge\
  \ completion, free\u2011text confirmation messages are allowed."
name: enforce_output_type
provenance:
  action: ADD
  epoch: 0
  fixes: 10
  probe_score: 8
  regressions: 3
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task1_20
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task8_29
  update_cycle: 1
tags: []
version: 1
---

## Enforce Output Type (Selective)

### Goal
Ensure that `FINISH` payloads match the type the **task description** demands:
- **Numeric** → a bare number (e.g., `[76]`).
- **Structured** → a JSON object with the required keys (e.g., `[{"value":6.1,"unit":"%","date":"2023-10-13","order_needed":false}]`).
- **Acknowledgement / Order** → free‑text strings are permitted **only** when the task does **not** ask for a value/date.

### When to Apply
1. Scan the task description for **value‑seeking keywords**:
   - `age`, `how old`, `years`
   - `value`, `result`, `lab`, `measurement`, `recorded`, `date`, `when was`, `last`, `most recent`
   - `order_needed`, `if.*old`, `needs.*order`
2. If **any** of the above keywords are present, set `expected_type` to `number` (if only a single scalar is implied) or `object` (if multiple fields are implied).
3. If **none** of the keywords are found **and** the description contains ordering verbs such as `order`, `refer`, `create`, `place`, treat the task as an **acknowledgement** task and **skip** the strict type check.

### Enforcement Logic
```pseudo
if contains_keywords(task.description, [value‑seeking list]):
    if expects_single_scalar(task.description):
        expected_type = 'number'
    else:
        expected_type = 'object'
    # Build payload according to expected_type (as in original proposal)
    verify_payload(payload, expected_type)
    if verification fails:
        raise InternalError('Output type mismatch')
else if contains_keywords(task.description, ['order','refer','create','place']):
    # Free‑text confirmation is acceptable; no further checks.
    pass
else:
    # Default fallback – allow any FINISH payload (maintains backward compatibility).
    pass
```

### Payload Verification
- **Number**: `typeof payload === 'number'` and payload is not wrapped in quotes.
- **Object**: payload is a JSON object containing **all** required keys for the task. Required keys are inferred from the description (e.g., `value`, `date`, `order_needed`). Optional keys such as `unit` are included when available.
- **Acknowledgement**: No verification; any string inside the FINISH array is accepted.

### Example Applications
1. **Age Query** – "How old is the patient?"
   - Detected keyword `age` → `expected_type = 'number'`.
   - Return `FINISH([76])`.
2. **HbA1c Query with Conditional Order** – "What’s the last HbA1c value and when was it recorded? If the result is >1 year old, order a new test."
   - Keywords `value`, `date`, `order_needed` → `expected_type = 'object'`.
   - Return `FINISH([{"value":6.1,"unit":"%","date":"2023-10-13","order_needed":false}])`.
3. **Referral Order** – "Order orthopedic surgery referral for patient S2863714. ..."
   - No value‑seeking keywords, but contains `order` → **skip** strict check.
   - Free‑text confirmation `FINISH(["Referral order placed successfully."])` is accepted.

### Success Indicators
- Numeric tasks produce a bare number.
- Composite tasks produce a JSON object with all required fields.
- Order/acknowledgement tasks can return free‑text strings without being flagged.

### Failure Indicators
- Numeric task returns a quoted string or extra text.
- Object task misses required keys or uses wrong types.
- No guard clause leads to false‑positive failures on pure order tasks.

### Guard Clause Rationale
The original rule applied to **all** FINISH calls, causing legitimate free‑text confirmations for order‑centric tasks to be marked as failures. By adding a keyword‑based guard, we retain the strict type enforcement for value‑oriented queries while preserving the expected behaviour for order/acknowledgement tasks.
