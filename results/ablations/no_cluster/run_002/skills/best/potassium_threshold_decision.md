---
description: "Decide potassium replacement and schedule follow\u2011up only when level\
  \ is low"
name: potassium_threshold_decision
provenance:
  action: MODIFY
  epoch: 4
  fixes: 9
  parent_version: 1
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - task8_23
  - task9_27
  - task8_5
  - task8_14
  - task10_24
  - task9_14
  - task10_21
  - task10_20
  - task9_20
  - task10_16
  update_cycle: 0
tags:
- potassium
- lab
- decision
version: 2
---

# Potassium Threshold Decision

## Pattern Description
You must evaluate the most recent serum potassium Observation and decide whether therapeutic replacement and a follow‑up test are required. The decision is based on a numeric threshold (e.g., < 3.5 mmol/L). If the value meets or exceeds the threshold, no medication order should be generated; instead, acknowledge that the level is acceptable. When the value is below the threshold, create a replacement ServiceRequest (using the NDC code supplied in the task context) and a separate ServiceRequest for a repeat serum potassium draw the next morning at 08:00.

## When to Use This Skill
- When a task asks to "check patient X's most recent potassium level" and includes conditional actions such as "if low, order replacement and schedule a follow‑up test".
- When the task expects a numeric result **and** a possible ServiceRequest creation based on that result.
- When the task provides the NDC code for potassium replacement and the desired time for the follow‑up draw.

## Common Failure Patterns
- Ordering replacement regardless of the potassium value (e.g., value = 3.9 mmol/L, still creates a ServiceRequest).
- Returning only the numeric value without indicating that no action is needed for normal levels.
- Using the wrong field for the value (e.g., `valueQuantity.value` vs `valueQuantity.unit`).
- Omitting the follow‑up ServiceRequest when replacement is ordered.

## Recommended Patterns
**Pattern 1: Extract and evaluate the potassium value**
1. GET `Observation?code=K&patient={MRN}`.
2. From the first entry in the Bundle, read `entry[0].resource.valueQuantity.value` as a number.
3. Compare the number to the low‑potassium threshold (default < 3.5 mmol/L).

**Pattern 2: No‑action response for normal or missing values**
- If the Observation bundle is empty **or** the extracted value ≥ 3.5, FINISH with an empty array `FINISH([])` (or optionally a short acknowledgment like `FINISH(["Potassium normal"])`).
- Do **not** create any ServiceRequest.

**Pattern 3: Replacement and follow‑up when low**
- If the value < 3.5:
  1. POST a `ServiceRequest` for potassium replacement using the NDC code supplied in the task context (e.g., `code":"40032-917-01"`).
  2. POST a second `ServiceRequest` for a repeat serum potassium draw with `occurrenceDateTime` set to the next calendar day at `08:00` (use the task’s current time to compute the date).
  3. FINISH with the numeric value, e.g., `FINISH([3.2])`.

## Example Application
**Task:** "Check patient S6309742's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=K&patient=S6309742`.
2. Extract `valueQuantity.value` → `3.2`.
3. Since `3.2 < 3.5`:
   - POST replacement ServiceRequest (NDC `40032-917-01`).
   - POST follow‑up ServiceRequest with `occurrenceDateTime` = `2023-11-14T08:00:00+00:00`.
4. FINISH(`[3.2]`).

**Correct output:** `FINISH([3.2])`
**Incorrect output (current failure):** `FINISH([3.9])` with no orders, or ordering when value is normal.

## Success Indicators
- The agent returns a numeric potassium value **and** creates zero ServiceRequests when the value ≥ 3.5 or when no recent Observation exists.
- When the value < 3.5, exactly two ServiceRequests are posted: one with the NDC code for replacement, one with the correct `occurrenceDateTime` for the next‑day draw.
- FINISH output contains the numeric value (or an empty array for no‑action).

## Failure Indicators
- Any ServiceRequest is posted when the potassium value is ≥ 3.5 or when the Observation bundle is empty.
- The agent returns only the numeric value without creating the required follow‑up ServiceRequest when the value is low.
- The extracted value is taken from the wrong field (e.g., `valueString` instead of `valueQuantity.value`).
- The follow‑up `occurrenceDateTime` is missing or set to the wrong date/time.
