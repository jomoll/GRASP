---
description: After creating or discontinuing orders, verify the count of active orders
  matches the task requirement.
name: active_order_count_verification_post_update
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task8_29
  - task8_9
  - task2_26
  - task2_6
  - task3_17
  - task3_16
  - task3_12
  - task4_27
  - task3_14
  - task4_21
  update_cycle: 1
tags:
- order-verification
- medicationrequest
- cardinality
- post-action-check
version: 1
---

# Active Order Count Verification Post-Update

## Pattern Description

When a task requires that a patient have exactly one active order of a specific type (e.g., DVT prophylaxis), it is not sufficient to simply create a new order if none are found, or discontinue duplicates if multiple are found. You must always verify the count of active orders after any create or discontinue action to ensure the final state matches the task requirement. This pattern prevents errors where the agent assumes the action succeeded without confirming the actual result in the FHIR server.

This skill is essential for tasks that require strict cardinality of orders (e.g., "exactly one active DVT prophylaxis order"). It ensures that the agent's actions result in the intended state, regardless of possible race conditions, failed POSTs, or unexpected resource states.

## When to Use This Skill

- When a task requires that a patient have exactly one active order of a specific type (e.g., DVT prophylaxis, anticoagulant, etc.).
- After creating a new order because none were found.
- After discontinuing duplicate orders to leave only the newest active order.
- Before calling FINISH or reporting task completion for order cardinality tasks.

## Common Failure Patterns

- Creating a new order but not verifying that only one active order exists afterward.
- Discontinuing duplicates but failing to confirm that only one active order remains.
- Assuming POST or PATCH actions succeeded without re-querying the server.
- Reporting "exactly one active order" in the answer without checking the actual state.

## Recommended Patterns

Pattern 1: Post-Action Verification
1. After any create (POST) or discontinue (PATCH/PUT) action on orders, issue a fresh GET request for active orders of the relevant type (e.g., `GET /MedicationRequest?patient=...&status=active`).
2. Filter the results to include only orders matching the required criteria (e.g., medication name, route, intent).
3. Count the number of active orders.
4. If the count is not exactly one, repeat the necessary actions (e.g., discontinue extras, create missing order) and re-verify.
5. Only report task completion (FINISH) when exactly one active order is present.

Pattern 2: Defensive Reporting
- In your final answer, state the actual number and details of active orders as confirmed by the last GET, not just what you intended to create or discontinue.

Pattern 3: Handling Race Conditions or Server Errors
- If the POST or PATCH fails, or the GET after action does not reflect the expected state, retry or report the discrepancy rather than assuming success.

## Example Application

**Task:** "Verify that patient S0869531 has exactly one active DVT prophylaxis order. If there are zero orders, create one. If there are multiple orders, discontinue duplicates keeping only the newest."

**Step-by-step:**

1. GET `/MedicationRequest?patient=Patient/S0869531&status=active` (filter for DVT prophylaxis orders).
2. If count == 0:
    - POST new DVT prophylaxis order.
    - GET `/MedicationRequest?patient=Patient/S0869531&status=active` again.
    - Confirm count == 1.
3. If count > 1:
    - Discontinue all but the newest order (PATCH/PUT to set `status: stopped` on extras).
    - GET `/MedicationRequest?patient=Patient/S0869531&status=active` again.
    - Confirm count == 1.
4. Only FINISH when exactly one active DVT prophylaxis order is present.

CORRECT output: `FINISH(["Exactly one active DVT prophylaxis order is now present for patient S0869531."])`
WRONG output:   `FINISH(["Order created. There are no other active DVT prophylaxis orders."])` (if not verified)

## Success Indicators

- A GET request for active orders is issued after any create or discontinue action.
- The final answer is based on the actual count of active orders from the last GET, not just the intended action.
- The agent repeats actions if the post-action state does not match the requirement.

## Failure Indicators

- The agent creates or discontinues orders but does not re-query to verify the result.
- The agent reports "exactly one active order" without confirming via GET after the last action.
- The agent calls FINISH immediately after POST or PATCH without post-action verification.
