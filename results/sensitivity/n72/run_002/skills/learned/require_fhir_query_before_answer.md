---
description: Enforce that a GET request for the specific resource mentioned in the
  task precedes any FINISH. This rule now only activates when the agent is about to
  emit a FINISH action; it does not interfere with intermediate reasoning steps or
  when the agent is still formulating the required GET request.
name: require_fhir_query_before_answer
provenance:
  action: MODIFY
  epoch: 2
  fixes: 11
  parent_version: 1
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - task4_23
  - task9_22
  - task9_28
  - task10_16
  - task9_5
  - task3_30
  - task9_11
  - task9_20
  - task9_8
  - task9_6
  update_cycle: 0
tags: []
version: 2
---

## Updated Skill: Require FHIR Query Before Answer

### Purpose
Prevent the agent from finishing a task without first retrieving the exact FHIR resource needed to answer the user’s request.

### When to Apply
- **Trigger:** The agent’s next output is a `FINISH` action (i.e., the assistant is about to provide the final answer).
- **Do NOT apply** during intermediate reasoning, planning, or when the assistant is still generating a `GET` request.

### Enforcement Logic
1. **Detect FINISH Intent**
   - Scan the current assistant message for a `FINISH` action. If none is present, the skill does nothing.
2. **Identify Required Resource**
   - Parse the task description for patient identifiers (`MRN`, `identifier`, `patient=`) and resource‑specific qualifiers (`code=`, `type=`, etc.).
3. **Validate Prior GET**
   - Verify that the execution trace already contains a `GET` request whose URL includes:
     - The correct FHIR resource type (`Patient`, `Observation`, `Condition`, …).
     - All required query parameters (e.g., `identifier=`, `code=`, `patient=`).
   - The `GET` must have been issued **before** the current `FINISH` action.
4. **If Validation Fails**
   - Abort the planned `FINISH`.
   - Emit the missing or corrected `GET` request as the next action.
   - After receiving the response, the agent may proceed to `FINISH`.

### Common Failure Patterns Fixed
- Emitting `FINISH` without any preceding `GET`.
- Emitting `FINISH` after a `GET` that targets the wrong resource or lacks required parameters.
- The skill mistakenly blocking legitimate reasoning steps that do not yet include `FINISH` (the regression case).

### Example (Age Query)
**Task:** "What's the age of the patient with MRN of S6537563?"
1. Agent plans: `GET /Patient?identifier=S6537563` → (no `FINISH` yet, skill does nothing).
2. After receiving the bundle, agent computes age and then outputs:
   `FINISH([45])` – skill checks that a suitable `GET` was already made; passes.

### Success Indicators
- Every `FINISH` in the trace is preceded by a validated `GET` for the needed resource.
- The agent can freely reason and issue `GET` actions before the final answer without being blocked.

### Failure Indicators
- `FINISH` appears with no prior appropriate `GET`.
- The preceding `GET` targets the wrong resource type or misses required query parameters.

### Guard Clause (Key Change)
> **Only enforce** when the assistant’s current output includes a `FINISH` action. If the output is reasoning text, a `GET`, or any other non‑FINISH action, the skill does not intervene.
