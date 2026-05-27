---
description: Prevent embedding order flags in FINISH output and require explicit ServiceRequest
  POST for conditional orders
name: enforce_output_type
provenance:
  action: MODIFY
  epoch: 1
  fixes: 4
  parent_version: 1
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task9_22
  - task8_21
  - task9_1
  - task9_5
  - task10_27
  - task8_7
  - task8_9
  - task9_9
  - task5_3
  - task9_8
  update_cycle: 1
tags:
- output
- conditional-order
- lab-observation
version: 2
---

# Enforce Output Type for Conditional Order Tasks

## Pattern Description
You must keep the final `FINISH` payload strictly to the data the user asked for.  When a task requests a lab value **and** adds a conditional ordering rule (e.g., *"If the result is older than 1 year, order a new test"*), the ordering decision must be performed via an explicit `POST` of a `ServiceRequest`.  The `FINISH` result should contain **only** the requested value/date (or `-1`/`null` when no result exists).  Any auxiliary flag such as `order_needed`, `needsOrder`, or free‑text decision must be stripped out.

## When to Use This Skill
- A task asks for the most recent lab Observation **and** adds a conditional ordering clause.
- The agent has already retrieved the Observation via `GET`.
- The agent is about to produce the final answer with `FINISH`.
- Example triggers:
  - "What’s the last HbA1c value and when was it recorded? If the result is > 1 year old, order a new HbA1c."
  - "Check the potassium level; if low, order replacement potassium."

## Common Failure Patterns
- `FINISH([{"value":5.4,"unit":"%","date":"2023-11-02","order_needed":false}])` – embeds an `order_needed` field that was never requested.
- Omitting the required `POST` when the condition is met, leaving the ordering decision only in the output payload.
- Returning free‑text confirmation (e.g., "Order placed") instead of the pure numeric/value array when the task explicitly asks for the value.

## Recommended Patterns
**Pattern 1: Core extraction and conditional order decision**
1. After the `GET` call, locate the most recent Observation:
   - Use `entry[0].resource.valueQuantity.value` (or `valueString` for non‑numeric) for the numeric value.
   - Use `effectiveDateTime` (or `issued`) for the timestamp.
2. Compare the timestamp to the current time (provided in the task context) to decide if the result is stale.
3. **If the condition requires ordering**:
   - Build a `ServiceRequest` resource with the appropriate LOINC/SNOMED code.
   - `POST` it to `/fhir/ServiceRequest` **before** calling `FINISH`.
4. **FINISH** only the requested data structure:
   - `FINISH([value, "date"])` for numeric/date pairs, or `FINISH([-1])` when no recent result exists.
   - **Never** include auxiliary keys like `order_needed`.

**Pattern 2: Fallback when no Observation is found**
- If the `GET` bundle `total` is `0`, skip extraction, still evaluate the ordering rule (e.g., order because no result exists), perform the `POST` if needed, and `FINISH([-1])`.

**Pattern 3: Formatting rule**
- The output array must contain plain JSON primitives (numbers, strings, or `-1`).
- Do not wrap the array in an extra object or add explanatory text.

## Example Application
**Task:** "What’s the last HbA1c value for patient S0658561 and when was it recorded? If the result is older than 1 year, order a new HbA1c."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0658561`
2. Extract `valueQuantity.value = 5.4`, `effectiveDateTime = "2022-10-30T00:00:00+00:00"`.
3. Compare to current time (`2023‑11‑13`). The result is > 1 year old → **order needed**.
4. `POST http://localhost:8080/fhir/ServiceRequest` with LOINC `4548-4` for HbA1c.
5. `FINISH([5.4, "2022-10-30"])` (no `order_needed` field).

## Success Indicators
- The agent issues a `POST` **only** when the ordering condition is satisfied.
- The final `FINISH` payload contains only the numeric value and date (or `-1`).
- No extra keys (`order_needed`, `needsOrder`, etc.) appear in the output.

## Failure Indicators
- `FINISH` includes any ordering flag or free‑text decision.
- The required `POST` is missing when the condition is true.
- The output array contains objects or strings that were not explicitly requested.

---
*This modification extends the existing `enforce_output_type` skill to cover conditional ordering scenarios, ensuring clean separation between data retrieval, ordering actions, and final answer formatting.*
