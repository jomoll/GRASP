---
description: Only place treatment or follow-up orders after explicitly verifying the
  latest lab meets the task condition.
name: conditional_lab_based_order_gating
provenance:
  action: ADD
  epoch: 3
  fixes: 7
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_16
  - task8_9
  - task9_3
  - task9_14
  - task10_10
  update_cycle: 1
tags:
- observation
- conditional-ordering
- medicationrequest
- servicerequest
- lab-thresholds
version: 1
---

# Conditional Lab-Based Order Gating

## Pattern Description

When a task says to check a lab and order treatment only if the result is abnormal, you must treat the lab review as a hard gate before any POST. First retrieve the relevant Observation, identify the most recent result, extract the numeric value, and compare it to the threshold or condition stated in the task. If the condition is not met, do not place any order.

This pattern is especially important in replacement protocols such as potassium or magnesium repletion, where the task is conditional: "if low, then order...". The required behavior change is to prevent premature `POST /MedicationRequest` or `POST /ServiceRequest` actions before the lab abnormality has been explicitly confirmed.

## When to Use This Skill

- When the instruction contains conditional phrasing like `if low`, `if elevated`, `if abnormal`, `if older than 1 year`, or `if no result exists`
- When reviewing an `Observation` before deciding whether to create a `MedicationRequest` or `ServiceRequest`
- When a replacement order and a paired follow-up lab should only be placed if the triggering lab is abnormal
- When a GET `/Observation?...` returns one or more entries and the task depends on the *most recent* result

## Common Failure Patterns

- Posting `MedicationRequest` immediately after `GET /Observation` without extracting `valueQuantity.value`
- Ordering both treatment and follow-up lab even though the latest result is normal
- Using any matching Observation instead of the most recent one by `effectiveDateTime`/`issued`
- Treating a non-empty Observation Bundle as sufficient evidence to order, without checking whether the value is below/above threshold
- Returning `FINISH(["done"])` after posting conditional orders when the condition was never verified
- Creating a paired `ServiceRequest` even though the primary replacement `MedicationRequest` should not have been placed

## Recommended Patterns

## Pattern 1: verify the triggering condition before any POST

1. Resolve the patient identifier and query the target lab Observation.
2. Identify the latest Observation entry.
3. Extract the numeric lab value from `resource.valueQuantity.value`.
4. Compare it against the task threshold or explicit condition.
5. Only if the condition is satisfied may you create downstream orders.

CORRECT: latest potassium `3.1` and task says `if low` with low threshold met -> place replacement order
WRONG: Observation exists -> place replacement order without reading `valueQuantity.value`

## Pattern 2: if condition is not met, stop with no orders

If the latest result is normal, high when task wants low, or otherwise does not satisfy the conditional trigger, do not POST anything. Finish with the task's no-action output, typically `FINISH([])` unless the task requests a different schema.

If no qualifying Observation exists and the task says not to order in that case, also do not POST anything.

## Pattern 3: pair follow-up orders only after the primary gate passes

When the task says to pair a treatment order with a follow-up lab, the follow-up `ServiceRequest` is also conditional on the abnormal lab. Do not place the paired lab alone unless the task explicitly asks for that. After the gate passes, construct both POST bodies using the resolved patient reference and required timing fields such as `occurrenceDateTime`.

## Example Application

**Task:** "Check patient S6547257's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step-by-step:**

1. Issue GET with exact parameters: `GET /Patient?identifier=S6547257`
2. Query the lab: `GET /Observation?patient=S6547257&code=K`
3. From the most recent entry, extract `entry[0].resource.valueQuantity.value` (or the latest by `effectiveDateTime` if entries are not already most-recent-first).
4. Compare the potassium value to the task's low threshold.
5. If the value is not low, do not POST `MedicationRequest` or `ServiceRequest`.
6. Finish with the no-order output.

CORRECT output: `FINISH([])`
WRONG output: `POST /MedicationRequest` then `POST /ServiceRequest` then `FINISH(["done"])` when potassium is normal

## Success Indicators

- You always inspect `valueQuantity.value` before placing a conditional order
- No `POST /MedicationRequest` or `POST /ServiceRequest` occurs until the lab condition is explicitly satisfied
- Normal latest labs lead to no-action completion such as `FINISH([])`
- Paired follow-up lab orders appear only when the triggering abnormal result justified treatment

## Failure Indicators

- A treatment order is posted even though the latest lab was normal or unverified
- The agent cites that a lab was checked, but there is no explicit numeric comparison step
- A follow-up `ServiceRequest` is created despite no qualifying abnormal trigger
- The agent uses presence of an Observation Bundle, rather than the latest result value, as the decision rule
