---
description: Require a GET Observation request before finishing any task that asks
  for a lab or vital value
name: enforce_fhir_get_before_finish
provenance:
  action: ADD
  epoch: 3
  fixes: 8
  probe_score: 7
  regressions: 5
  triggering_sample_ids:
  - task9_1
  - task9_5
  - task10_21
  - task8_7
  - task4_4
  - task10_13
  - task4_7
  - task8_29
  - task10_12
  - task8_26
  update_cycle: 0
tags: []
version: 1
---

# Enforce FHIR GET Action Before FINISH for Observation Retrieval

## Pattern Description
You must never answer a question that requires a lab, vital sign, or other patient data without first retrieving that data from the FHIR server. When the instruction asks for the "most recent" value, a "check" of a lab level, or any specific measurement, the correct behavior is to issue a `GET` request for the appropriate `Observation` resource, wait for the response, extract the needed field, and only then produce the final `FINISH` output. Skipping the GET leads to reasoning‑only replies and is a common failure mode.

## When to Use This Skill
- When the task text contains phrases like:
  - "most recent *level" or "most recent *value"
  - "Check patient *'s * level"
  - "What’s the last * (hemoglobin A1C, potassium, magnesium, etc.)"
  - "If * is low, then order ..."
- The task expects a numeric result or a decision based on that result.
- No prior `GET` request for the required `Observation` has been issued in the current turn.

## Common Failure Patterns
- Agent provides reasoning or directly calls `FINISH` without any preceding `GET` request.
- Agent issues a `GET` to the wrong resource (e.g., `ServiceRequest` instead of `Observation`).
- Agent uses incorrect query parameters (missing `code`, wrong patient identifier, missing date filter).
- Agent extracts the value from the wrong field (e.g., `valueString` instead of `valueQuantity.value`).

## Recommended Patterns
**Pattern 1: Identify required Observation and issue GET**
1. Parse the instruction to extract:
   - Lab/vital code (e.g., `MG` for magnesium, `K` for potassium, `A1C` for HbA1c).
   - Patient MRN (e.g., `S6474456`).
   - Optional time window (e.g., "within last 24 hours").
2. Construct the GET URL:
   - Base: `http://localhost:8080/fhir/Observation`
   - Query parameters:
     - `code={CODE}`
     - `patient={MRN}`
     - If a time window is specified, add `date=ge{ISO_TIMESTAMP}` where the timestamp is `current_time - window`.
   - Example: `GET http://localhost:8080/fhir/Observation?code=MG&patient=S6474456&date=ge2023-11-12T10:15:00`
3. Issue the GET request **before** any `FINISH`.

**Pattern 2: Extract the correct value**
- From the returned Bundle, locate the first (or most recent) `entry.resource` where `resourceType == "Observation"`.
- Use `valueQuantity.value` for numeric labs; if the unit is not mg/dL, convert accordingly.
- If no entries match the time window, treat the result as `-1` (or follow task‑specific fallback).

**Pattern 3: Produce the final output**
- After extraction, format the answer exactly as required (e.g., `FINISH([1.8])` or `FINISH([5.2, "2022-08-09T15:33:00+00:00"])`).
- Do **not** include any explanatory text in the `FINISH` payload.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S6474456 within last 24 hours?"

**Step‑by‑step:**
1. Identify code `MG`, patient `S6474456`, window 24 h.
2. Issue:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S6474456&date=ge2023-11-12T10:15:00
   ```
3. Receive Bundle, locate the newest Observation, extract `valueQuantity.value` (e.g., `1.8`).
4. Convert to mg/dL if needed (magnesium is already in mg/dL in this dataset).
5. Return:
   ```
   FINISH([1.8])
   ```

## Success Indicators
- A `GET` request for `Observation` appears in the action log before any `FINISH`.
- The GET URL includes both `code` and `patient` parameters (and `date` when a time window is mentioned).
- The final `FINISH` payload contains only the numeric value(s) required by the task.

## Failure Indicators
- `FINISH` is called without a preceding `GET` for the needed resource.
- The GET request targets the wrong endpoint or omits required query parameters.
- The extracted value comes from an incorrect field or includes units/text.
- The agent returns placeholder text or explanatory sentences inside `FINISH`.
