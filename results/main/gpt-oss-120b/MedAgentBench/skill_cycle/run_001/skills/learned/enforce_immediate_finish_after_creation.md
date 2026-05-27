---
description: Require FINISH with created resource ID right after a POST, without intervening
  GETs
name: enforce_immediate_finish_after_creation
provenance:
  action: ADD
  epoch: 9
  fixes: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task4_28
  - task8_21
  - task8_13
  update_cycle: 0
tags:
- creation
- finish
- resource_id
version: 1
---

# Enforce Immediate FINISH After Resource Creation

## Pattern Description
You must capture the identifier of any FHIR resource you create via a `POST` request and return it directly with `FINISH` before performing any other API calls. The POST response contains the full resource JSON, including the `id` field. Use that `id` as the sole answer. Do **not** issue a `GET` for the same resource before calling `FINISH`, because that defeats the purpose of the creation‑confirmation skill and leads to generic string answers.

## When to Use This Skill
- After a `POST` that creates a new resource (e.g., `ServiceRequest`, `Observation`, `MedicationRequest`).
- When the task description asks you to *order*, *create*, *record*, or otherwise *add* a resource and expects a confirmation.
- Whenever you see a `POST` followed by any other API call before `FINISH`.

## Common Failure Patterns
- `POST` → `GET` → `FINISH` with a free‑text message like `"ServiceRequest created"`.
- `FINISH` returns a placeholder such as `[-1]` or a descriptive sentence instead of the resource ID.
- Missing extraction of `id` from the POST response body.

## Recommended Patterns
**Pattern 1: Capture and return the ID immediately**
1. Issue the `POST` request.
2. Parse the JSON response; extract `response.id` (e.g., `response.id = "372777"`).
3. Call `FINISH(["<id>"])` **without any intervening API calls**.

```json
POST http://localhost:8080/fhir/ServiceRequest { ... }
# Assume response body contains "id": "abc123"
FINISH(["abc123"])
```

**Pattern 2: Guard against accidental GETs**
- If your logic would normally verify the creation, skip the verification step; the POST response is authoritative.
- If you must verify later, do it **after** you have already called `FINISH` (outside the current task flow).

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6547257. Include the free‑text note …"

**Step‑by‑step:**
1. `POST http://localhost:8080/fhir/ServiceRequest` with the referral payload.
2. Receive response: `{ "resourceType": "ServiceRequest", "id": "sr-00123", ... }`.
3. Immediately execute `FINISH(["sr-00123"])`.

**CORRECT output:** `FINISH(["sr-00123"])`
**WRONG output:** `FINISH(["Orthopedic surgery referral for patient S6547257 has been created."])` or any `GET` before `FINISH`.

## Success Indicators
- The final `FINISH` call contains a single string element that matches the `id` from the POST response.
- No `GET` request appears between the `POST` and the `FINISH`.

## Failure Indicators
- `FINISH` outputs a sentence, placeholder `-1`, or any value that is not the raw resource ID.
- A `GET` request targeting the newly created resource occurs before `FINISH`.
