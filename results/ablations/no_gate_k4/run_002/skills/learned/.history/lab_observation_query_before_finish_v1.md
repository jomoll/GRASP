---
description: "Require a FHIR Observation query and proper extraction before answering\
  \ any lab\u2011value request"
name: lab_observation_query_before_finish
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task5_19
  - task9_5
  - task8_23
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task8_29
  update_cycle: 1
tags: []
version: 1
---

# Lab Observation Retrieval Before FINISH

## Pattern Description
You must always query the FHIR server for the requested laboratory observation before producing a final answer. This pattern applies to any task that asks for the most recent value of a lab test (e.g., magnesium, potassium, HbA1c) or that conditions an order on that value. By forcing a GET Observation first, you guarantee that the answer is based on real data rather than a placeholder or guess.

## When to Use This Skill
- When the task asks for *most recent*, *last*, or *within the last N hours* value of a lab test (e.g., "most recent magnesium level", "last HbA1c value").
- When the task requires a conditional order that depends on a lab result (e.g., "If potassium is low, order replacement").
- When the task explicitly mentions a LOINC or custom code (e.g., code "MG" for magnesium).

## Common Failure Patterns
- Agent provides reasoning but never issues a `GET http://.../Observation` request.
- `FINISH` is called with a placeholder like `-1` or a free‑text sentence instead of a numeric value.
- The agent extracts the unit together with the number (e.g., `"3.5 mmol/L"`) instead of a pure number.
- No date filter is applied even though the task limits the time window.

## Recommended Patterns
**Pattern 1: Core query and extraction**
1. **Build the GET URL**
   - Base: `http://localhost:8080/fhir/Observation`
   - Required parameters: `code=<CODE>`, `patient=<MRN>`
   - If the task limits time, add `date=ge<ISO>` and `date=le<ISO>` where the lower bound is *now – window*.
   - Example: `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1733937&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`
2. **Parse the Bundle response**
   - If `total == 0`, treat as *no recent measurement*.
   - Otherwise, locate the entry with the greatest `effectiveDateTime` (or `issued`).
3. **Extract the numeric value**
   - Prefer `valueQuantity.value` (number) and `valueQuantity.unit`.
   - If only `valueString` is present, parse the leading number.
4. **Convert to required unit** (use `append_units_to_quantity` if needed).
5. **Finish**
   - If a value was found: `FINISH([<number>])`
   - If none: `FINISH([-1])` (or the task‑specific message).

**Pattern 2: Conditional ordering based on the extracted value**
1. After extraction, compare the numeric result to the clinical threshold defined in the task.
2. If the condition is met, construct the appropriate `POST` (e.g., `MedicationRequest` for IV magnesium) **before** calling `FINISH`.
3. If the condition is not met, skip the order and call `FINISH` with the appropriate “no action” message.

**Pattern 3: Formatting the final output**
- Always return a JSON array with a single numeric element (or `-1`).
- Do **not** embed explanatory text inside the array.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1733937 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1733937&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00`
2. Receive Bundle. Suppose it contains one entry with:
   ```json
   "valueQuantity": {"value": 1.8, "unit": "mg/dL"},
   "effectiveDateTime": "2023-11-13T08:00:00+00:00"
   ```
3. Extract `1.8` (already in mg/dL, no conversion needed).
4. `FINISH([1.8])`

**CORRECT output:** `FINISH([1.8])`
**WRONG output:** `FINISH(["Magnesium is 1.8 mg/dL"] )` or `FINISH([-1])` when a value exists.

## Success Indicators
- A `GET` request to `/Observation` appears in the action log before any `FINISH`.
- The `FINISH` payload is a JSON array containing a single number (or `-1`).
- No free‑text explanations are embedded in the array.

## Failure Indicators
- `FINISH` is called without a preceding `GET /Observation`.
- The array contains a string or explanatory sentence.
- The agent returns `-1` while the GET response actually includes a valid observation.
- The agent omits required date filters when the task specifies a time window.
