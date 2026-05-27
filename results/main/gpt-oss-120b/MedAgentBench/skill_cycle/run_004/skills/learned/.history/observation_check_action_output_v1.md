---
description: Ensures tasks that check a lab observation and conditionally order medication
  return an empty array, not raw observation data.
name: observation_check_action_output
provenance:
  action: ADD
  epoch: 1
  fixes: 13
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task10_16
  - task10_15
  - task10_18
  - task10_24
  - task10_17
  - task10_20
  - task9_6
  - task9_9
  - task9_5
  - task9_22
  update_cycle: 0
tags: []
version: 1
---

# Observation Check Action Output Formatting

## Pattern Description
You must treat any task that asks you to *check a recent laboratory observation* (e.g., potassium, magnesium, HbA1c) **and** conditionally create a `ServiceRequest` as a *pure action* task. The purpose of the task is to perform the order, not to report the observation itself. Therefore the final `FINISH` payload must be an empty JSON array (`[]`). The raw observation data should never be echoed back to the user.

## When to Use This Skill
- The instruction contains phrasing like "Check patient X's most recent **[lab]** level. If low, then order **[medication]** ...".
- The instruction also asks to schedule a follow‑up observation (e.g., "pair this order with a morning serum potassium level to be completed the next day at 8am").
- Any task that combines **observation retrieval + conditional order**.

## Common Failure Patterns
- `FINISH([{"value":4.3,"date":"2023-11-12T14:09:00+00:00"}])` – raw observation object returned.
- `FINISH([4.3])` – numeric value returned instead of an empty array.
- `FINISH(["No potassium replacement needed; latest level 3.9 mmol/L is above the goal of 3.5 mmol/L."])` – free‑text string returned.
- Returning the observation **and** the order result together.

## Recommended Patterns
**Pattern 1: Core workflow**
1. **GET** the observation: `GET {api_base}/Observation?code={LOINC_or_custom}&patient={MRN}`.
2. Parse the first entry in `Bundle.entry` → `resource.valueQuantity.value` (numeric) and `resource.effectiveDateTime`.
3. Compare the numeric value to the task‑specific threshold (e.g., potassium < 3.5 mmol/L).
4. **If low**:
   - Build a `ServiceRequest` for the replacement medication (use provided NDC or code).
   - Build a second `ServiceRequest` (or `ProcedureRequest`) for the follow‑up observation at the required time.
   - `POST` each request.
5. **Regardless of the branch**, call `FINISH([])` – an empty JSON array.

**Pattern 2: Fallback / verification**
- If the GET returns no entries, treat the level as *not available* and still `FINISH([])` (no order).
- If the numeric field is missing or not a number, log a warning internally and `FINISH([])`.

**Pattern 3: Output rule**
- **Never** include any part of the retrieved Observation in the final `FINISH` payload.
- The only valid payload for these tasks is `[]` (empty array).

## Example Application
**Task:** "Check patient S6550473's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S6550473`
2. Extract `valueQuantity.value` → e.g., `4.3`.
3. Compare to threshold `3.5` → not low.
4. No `POST` needed.
5. `FINISH([])`

**Correct output:** `FINISH([])`
**Incorrect output:** `FINISH([{"value":4.3,"date":"2023-11-12T14:09:00+00:00"}])`

## Success Indicators
- The agent performs the GET, makes any required POST(s), and ends with `FINISH([])`.
- No observation data appears in the FINISH payload.
- All required ServiceRequests (medication and follow‑up) are posted when the condition is met.

## Failure Indicators
- FINISH payload contains any object, number, or string derived from the observation.
- The agent omits required POST(s) when the observation is low.
- The agent returns a non‑empty array when the task only demanded an action.
