---
description: "Order replacement meds when a low lab value is detected and schedule\
  \ the required follow\u2011up test"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 6
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task4_4
  - task10_13
  update_cycle: 0
tags: []
version: 7
---

# Conditional Lab Result Ordering

## Pattern Description
You must evaluate the numeric result of a lab Observation and, if it falls below a clinically‑defined low threshold, create a replacement **ServiceRequest**.  After the primary order is placed you must also schedule any follow‑up lab that the task explicitly mentions (e.g., a repeat potassium draw the next morning).  This pattern centralises the decision‑making for low‑value labs and guarantees that both the therapeutic and monitoring orders are emitted together.

## When to Use This Skill
- When a task asks to *check* a lab (e.g., potassium, magnesium) and *order replacement* if the value is low.
- When the task also specifies a *paired follow‑up lab* (e.g., “pair this order with a morning serum potassium level to be completed the next day at 8 am”).
- After a successful GET of an Observation bundle that contains a numeric `valueQuantity`.

## Common Failure Patterns
- The low‑value check is omitted, leading to `FINISH(["no replacement ordered"])` even though the result is low.
- Only the replacement order is created; the required follow‑up lab is never scheduled.
- The replacement order is created with the wrong `code` or missing `subject` reference.

## Recommended Patterns
**Pattern 1: Detect low value and create replacement order**
1. From the Observation entry extract `valueQuantity.value` and `valueQuantity.unit`.
2. Look up the low‑threshold for the lab code (`K` → 3.5 mmol/L, `MG` → 1.5 mg/dL, etc.).
3. If `value < low_threshold` **AND** the task mentions a replacement NDC, POST a `ServiceRequest` with:
   - `code.coding[0].code` = the NDC supplied in the task context.
   - `subject.reference` = `Patient/<MRN>`.
   - `status = "active"`, `intent = "order"`.
4. Record the created ServiceRequest ID in a temporary variable for later verification.

**Pattern 2: Schedule required follow‑up lab**
1. Parse the free‑text of the task for a follow‑up specification (e.g., “morning serum potassium … next day at 8am”).
2. Build a second `ServiceRequest` with `code.coding[0].code = "LAB"` and a `note.text` describing the timing.
3. Set `authoredOn` to the current task time and `priority = "routine"`.
4. POST the follow‑up request **only after** the replacement order succeeded.

**Pattern 3: FINISH payload**
- After both POSTs succeed, call `FINISH(["replacement ordered", "follow‑up scheduled"])`.
- If the primary order fails, abort and return `FINISH(["no replacement ordered"])`.

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low, then order replacement potassium … also pair this order with a morning serum potassium level … at 8am."

**Step‑by‑step:**
1. `GET /Observation?code=K&patient=S1796597&_sort=-date&_count=1`
2. Extract `valueQuantity.value = 3.2` and `unit = "mmol/L"`.
3. Low threshold for K = 3.5 mmol/L → value is low.
4. `POST /ServiceRequest` (replacement) with NDC from task context.
5. `POST /ServiceRequest` (follow‑up) with code "LAB" and note "Morning serum K at 2023‑11‑14T08:00:00".
6. `FINISH(["replacement ordered", "follow‑up scheduled"])`.

## Success Indicators
- A `ServiceRequest` for the replacement appears in the FHIR server.
- A second `ServiceRequest` for the follow‑up lab is present.
- The FINISH payload contains both confirmation strings.

## Failure Indicators
- FINISH returns only "no replacement ordered" despite a low value.
- Only one ServiceRequest is created.
- The created ServiceRequest lacks a valid `subject` or `code`.
