---
description: Verify Observation GET responses contain entries before extracting a
  value. This rule only activates after a GET request to an Observation endpoint and
  before any attempt to read `bundle['entry'][0]`. It does **not** prescribe a specific
  fallback value; downstream task logic must decide what to do when no observation
  is present.
name: observation_presence_check
provenance:
  action: ADD
  epoch: 0
  fixes: 12
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task8_26
  - task5_19
  - task9_5
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

## Observation Bundle Presence Check (Narrowed Trigger)

**When to fire**
1. The most recent agent action was a `GET` request whose URL contains `/Observation` (e.g., `GET http://.../fhir/Observation?...`).
2. The next planned step (by the agent) accesses `bundle['entry'][0]` or `bundle['entry'][0]['resource']` to read an observation field such as `valueQuantity` or `effectiveDateTime`.

**What to do**
```python
# Assume the GET response JSON is stored in variable `bundle`
if bundle.get('total', 0) == 0 or not bundle.get('entry'):
    # No observation present – set a sentinel for downstream logic
    observation_present = False
    observation_resource = None
else:
    observation_present = True
    observation_resource = bundle['entry'][0]['resource']
```
- **Do not** automatically call `FINISH` or return a hard‑coded fallback (e.g., `-1`).
- Let the task‑specific logic decide what to do when `observation_present` is `False` (e.g., return `-1`, order a new test, or emit a custom message).

**Typical downstream usage**
```python
if observation_present:
    value = observation_resource['valueQuantity']['value']
    date  = observation_resource['effectiveDateTime']
    # ... task‑specific processing ...
else:
    # Task‑specific fallback (could be ordering a new lab, returning -1, etc.)
    pass
```

**Why this change fixes regressions**
- **Task 8_3 (orthopedic referral)**: The rule no longer triggers because the previous request was not an Observation GET, so the duplicate `ServiceRequest` creation is avoided.
- **Task 10_12 (HbA1c check)**: The rule only sets `observation_present = False` when the bundle is empty; it does **not** force a `FINISH([-1])`. The agent can now follow the task instruction to order a new HbA1c test when no recent result exists.

**Success criteria**
- The agent checks `bundle.total` / `bundle.entry` before any `valueQuantity` access.
- No automatic `FINISH` is emitted by this rule.
- Task‑specific fallback behavior remains under the agent’s control.

**Failure indicators**
- Accessing `bundle['entry'][0]` without the guard above.
- Emitting a `FINISH` directly from this rule.
- Duplicate service requests for non‑Observation tasks.
