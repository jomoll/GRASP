---
description: Ensure duplicate active orders are discontinued via FHIR PATCH or DELETE,
  not just described in output
name: active_order_discontinuation_execution
provenance:
  action: ADD
  epoch: 2
  fixes: 6
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task3_16
  - task6_26
  - task1_10
  - task3_27
  - task8_5
  - task10_8
  - task3_10
  - task3_30
  - task2_6
  - task3_19
  update_cycle: 0
tags:
- order management
- FHIR
- PATCH
- DELETE
- medication
- service request
- discontinuation
version: 1
---

# Active Order Discontinuation Execution

## Pattern Description

When a clinical protocol requires that only one active order of a given type (e.g., DVT prophylaxis) remain, you must not only identify duplicates but also actively discontinue all but the most recent order. It is insufficient to merely describe which orders should be discontinued in the output; you must execute the discontinuation using the appropriate FHIR operation (PATCH or DELETE) on the duplicate orders.

This skill ensures that the agent transitions from passive reporting (summarizing what should be done) to active execution (actually performing the discontinuation), which is critical for maintaining accurate and up-to-date medication and service order records.

## When to Use This Skill

- When a task requires that exactly one active order of a specific type (e.g., DVT prophylaxis) remain for a patient.
- When multiple active orders of the same type are found for a patient and the protocol instructs to keep only the newest.
- When the agent is about to FINISH with a summary of which orders should be discontinued, but has not yet executed any FHIR PATCH or DELETE requests.

## Common Failure Patterns

- FINISH output describes which orders should be discontinued, but no PATCH or DELETE request is issued to the FHIR server.
- Only the most recent order is identified, but older active orders remain in the system.
- PATCH or DELETE is attempted on the wrong resource type or with an incorrect resource id.
- PATCH request omits the required status update (e.g., does not set `status` to `stopped` or `cancelled`).

## Recommended Patterns

**Pattern 1: Identify Duplicates**
- After retrieving all active orders (e.g., via GET /MedicationRequest?patient=...&status=active), filter for orders matching the relevant medication or protocol.
- Sort by `authoredOn` to identify the most recent order.

**Pattern 2: Discontinue Duplicates**
- For each duplicate (all but the most recent), issue a PATCH request to the resource endpoint (e.g., PATCH /MedicationRequest/{id}) with a body that sets `status` to `stopped` or `cancelled`.
- Alternatively, if PATCH is not supported, use DELETE /MedicationRequest/{id} to remove the order.
- Wait for confirmation of successful execution before proceeding.

CORRECT:
PATCH /MedicationRequest/765640
{
  "status": "stopped"
}

or
DELETE /MedicationRequest/765640

WRONG:
FINISH(["Discontinue MedicationRequest/765640 (authoredOn: 2023-07-29)"])

**Pattern 3: Final Output**
- Only after all discontinuation actions have been executed, call FINISH with a summary of the actions taken and the final state (e.g., "Exactly one active DVT prophylaxis order remains").

## Example Application

**Task:** "Verify that patient S2704870 has exactly one active DVT prophylaxis order. If there are zero orders, create one. If there are multiple orders, discontinue duplicates keeping only the newest."

**Step-by-step:**

1. GET /MedicationRequest?patient=S2704870&status=active
2. Identify all active DVT prophylaxis orders. Suppose you find:
   - MedicationRequest/765646 (authoredOn: 2023-11-12)
   - MedicationRequest/765640 (authoredOn: 2023-07-29)
3. Keep MedicationRequest/765646. For MedicationRequest/765640, issue:
   PATCH /MedicationRequest/765640 { "status": "stopped" }
   (or DELETE /MedicationRequest/765640)
4. Wait for confirmation of successful PATCH/DELETE.
5. FINISH(["Discontinued MedicationRequest/765640. Exactly one active DVT prophylaxis order remains (MedicationRequest/765646)."])

CORRECT output: PATCH or DELETE requests are issued for all duplicates before FINISH.
WRONG output: Only a FINISH statement describing what should be done, with no PATCH/DELETE action.

## Success Indicators

- PATCH or DELETE requests are issued for all duplicate active orders before FINISH.
- FINISH output summarizes the actions taken and confirms only one active order remains.
- The FHIR server reflects the updated status or removal of discontinued orders.

## Failure Indicators

- FINISH output describes discontinuation but no PATCH or DELETE requests are made.
- Duplicate active orders remain in the system after task completion.
- PATCH/DELETE is attempted on the wrong resource or with missing/incorrect status field.
