---
description: Prevent creating ServiceRequests unless the task explicitly requests
  an order
name: service_request_creation_guard
provenance:
  action: ADD
  epoch: 4
  fixes: 9
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task3_10
  - task10_15
  - task10_13
  - task9_3
  - task10_18
  - task9_5
  update_cycle: 1
tags: []
version: 1
---

# Service Request Creation Guard

## Pattern Description
You must ensure that a ServiceRequest is only created when the user instruction explicitly asks for an order. This guard runs before any POST to `/fhir/ServiceRequest`. It looks for ordering keywords (e.g., "order", "create", "place", "request", "schedule") in the original task text. If none are found, the skill aborts the POST and proceeds directly to the FINISH step. When the instruction contains a conditional clause (e.g., "If the result is older than 1 year, order a new test"), the presence of the word "order" satisfies the guard, and the normal conditional logic may proceed.

## When to Use This Skill
- When the agent is about to POST a `ServiceRequest` resource.
- The current task description does **not** contain any ordering keyword.
- The task includes only a data‑retrieval request (e.g., "What’s the last HbA1c value?" without ordering language).
- The task includes a conditional ordering clause that contains an ordering keyword; in that case the POST is allowed.

## Common Failure Patterns
- `POST http://.../ServiceRequest` executed even though the instruction only asked for a value.
- Unnecessary duplicate orders created for the same patient because the guard was missing.
- ServiceRequest created when the task wording uses synonyms not covered by the guard (e.g., "schedule"), leading to false negatives.

## Recommended Patterns
**Pattern 1: Guard check before POST**
1. Extract the original task description string.
2. Define the ordering keyword set: `{"order", "create", "place", "request", "schedule", "order a", "order new"}`.
3. If **any** keyword appears in the task description (case‑insensitive), allow the POST.
4. Otherwise, **skip** the POST and go straight to FINISH.

**Correct example**
```text
Task: "If the lab value result date is greater than 1 year old, order a new HbA1c lab test."
→ Keyword "order" found → POST allowed.
```

**Wrong example**
```text
Task: "What’s the last HbA1c value in the chart?"
→ No ordering keyword → POST must be skipped.
```

**Pattern 2: Fallback when keyword missed**
If the guard incorrectly blocks a needed order (e.g., the user used an uncommon synonym), add the synonym to the keyword set and re‑run.

## Example Application
**Task:** "What’s the last HbA1c value for patient S123456 and when was it recorded?"

**Step‑by‑step:**
1. Agent prepares to POST a `ServiceRequest`.
2. Guard extracts task text.
3. No ordering keyword found → guard aborts POST.
4. Agent proceeds to FINISH with the retrieved value only.

**Correct output:** `FINISH([5.2, "2022-08-15T10:00:00+00:00"])`
**Wrong output:** `POST ... ServiceRequest` followed by `FINISH([...])`

## Success Indicators
- No `POST /ServiceRequest` appears in logs for tasks that lack ordering language.
- When ordering language is present, the POST proceeds as before.
- Reduced count of `unnecessary_service_request_created` failures.

## Failure Indicators
- A `POST /ServiceRequest` is logged for a pure‑retrieval task.
- The agent skips an order when the task uses an unrecognized synonym for ordering.
- The guard incorrectly blocks duplicate‑prevention logic, leading to duplicate orders.
