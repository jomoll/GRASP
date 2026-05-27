---
description: "Emit a concise one\u2011sentence confirmation after any order creation"
name: order_confirmation_output
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task1_27
  - task8_14
  - task10_20
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task5_16
  - task9_11
  update_cycle: 0
tags:
- order
- confirmation
version: 2
---

# Order Confirmation Output

## Pattern Description
After you successfully POST an order (MedicationRequest, ServiceRequest, etc.), you must immediately acknowledge the order with a short, machine‑readable confirmation.  The confirmation should be a single clause that names the ordered product or service and its status, **without** additional narrative, scheduling details, or clinical reasoning.

## When to Use This Skill
- Immediately after any successful POST that creates a new FHIR order resource.
- When the task expects a confirmation string (e.g., "Potassium replacement ordered").
- Even if the task also requires a follow‑up action (like scheduling a repeat lab), that follow‑up should be handled by a separate skill; the confirmation here stays minimal.

## Common Failure Patterns
- Returning a combined sentence that mixes the order confirmation with extra information (e.g., "Potassium replacement ordered; repeat potassium level scheduled for 2023‑11‑14T08:00:00+00:00.").
- Echoing back the full request payload instead of a short acknowledgment.
- Omitting the confirmation entirely and proceeding directly to FINISH with other data.

## Recommended Patterns
**Pattern 1: Detect successful POST**
1. After a POST, check the system note or response indicating the resource was stored (`status: active`, `id` returned, etc.).
2. If the POST succeeded, prepare the confirmation string.

**Pattern 2: Build the concise confirmation**
- For MedicationRequest: `"<Medication display> ordered"` (e.g., `"Potassium replacement ordered"`).
- For ServiceRequest: `"<Service display> ordered"` (e.g., `"HbA1c lab ordered"`).
- Use the `display` or `code.text` field from the request body to populate the name.

**Pattern 3: Emit FINISH**
- Immediately call `FINISH(["<confirmation>"])`.
- Do **not** include any other data in the same FINISH call.

## Example Application
**Task:** Order a repeat potassium level and a potassium replacement.

**Step‑by‑step:**
1. POST the MedicationRequest for potassium replacement.
2. Detect success → build `"Potassium replacement ordered"`.
3. `FINISH(["Potassium replacement ordered"])`.
4. (Separate skill) POST the ServiceRequest for the repeat potassium level.
5. Emit its own confirmation if required.

**CORRECT output:** `FINISH(["Potassium replacement ordered"])`
**WRONG output:** `FINISH(["Potassium replacement ordered; repeat potassium level scheduled for 2023-11-14T08:00:00+00:00."])`

## Success Indicators
- FINISH contains a one‑element array with a short confirmation string.
- The string ends with the word "ordered" (or "created") and mentions only the ordered item.

## Failure Indicators
- FINISH includes additional clauses, dates, or clinical rationale.
- The confirmation string is missing or empty.
- The FINISH payload mixes order confirmation with other answer data.
