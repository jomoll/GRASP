---
description: Force lab Observation answers to be returned as separate structured fields
  (value, unit, date, order flag).
name: structured_lab_observation_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 8
  regressions: 0
  triggering_sample_ids:
  - task3_14
  - task2_26
  - task10_20
  - task9_9
  - task4_21
  - task2_22
  - task3_3
  - task4_28
  - task4_7
  - task10_8
  update_cycle: 0
tags:
- structured_output
- lab_observation
- answer_format
version: 1
---

# Structured Lab Observation Answer Format

## Pattern Description
You must always return the result of a lab Observation (e.g., HbA1c, potassium, magnesium) as a **structured JSON object** rather than a free‑text string or a list of strings.  The pattern separates the numeric result, its unit, the timestamp of the measurement, and any downstream decision (e.g., whether a new order was placed).  This makes downstream processing reliable and avoids the `answer_format_wrong_type` failure mode.

## When to Use This Skill
- When a task asks for "the last *X* value and when it was recorded" for any Observation code.
- When the task adds a conditional action such as "if the result is older than 1 year, order a new test".
- When the task asks for a decision based on the numeric value (e.g., low potassium → order replacement).

## Common Failure Patterns
- `FINISH(["The most recent HbA1c is 6.5% recorded on 2022‑03‑08."])` – a single narrative string inside a list.
- Returning two separate strings in a list (e.g., `FINISH(["5.8% on 2022‑09‑09","New test ordered"])`).
- Omitting the unit or date field, or mixing them into the value string.
- Using a plain integer list for age (`FINISH(["66"])`) instead of a raw number.

## Recommended Patterns
**Pattern 1: Core extraction and formatting**
1. Issue the GET request for the Observation with the appropriate `code` and `patient` parameters.
2. From the first entry in the returned Bundle, extract:
   - `valueQuantity.value` → numeric result (or `valueString` if the Observation uses a string).
   - `valueQuantity.unit` (if present) → unit of measure.
   - `effectiveDateTime` → ISO‑8601 timestamp of the measurement.
3. Build a JSON object:
   ```json
   {
     "value": 6.5,
     "unit": "%",
     "date": "2022-03-08T00:00:00+00:00",
     "order_placed": false
   }
   ```
   - If the Observation uses a string value, keep it as a string and still provide a separate `unit` field if known.
4. Compare the extracted `date` to the current context time (provided in the task description). If the date is older than the threshold, perform the required POST (e.g., ServiceRequest) **before** constructing the final object and set `"order_placed": true`.
5. Call `FINISH([<JSON object>])` – the object must be the sole element of the list.

**Pattern 2: Fallback when no recent Observation exists**
- If the GET returns `total: 0` or the Bundle has no entries, construct a minimal object indicating the absence:
  ```json
  { "value": null, "unit": null, "date": null, "order_placed": false }
  ```
- Optionally add a human‑readable note in a separate field `"note"` if the task explicitly asks for a message.

**Pattern 3: Formatting for age queries**
- For patient age requests, extract `birthDate` from the Patient resource, compute the integer age (floor), and **return the raw number** (not a string or list). Example:
  ```json
  FINISH([45])
  ```

## Example Application
**Task:** "What’s the last HbA1c value for patient S3114648 and when was it recorded? If the result is older than 1 year, order a new HbA1c test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S3114648`
2. Extract `valueQuantity.value = 6.1`, `valueQuantity.unit = "%"`, `effectiveDateTime = "2023-10-13T22:22:00+00:00"`.
3. Compare the date to the current time (`2023‑11‑13`). It is < 1 year, so **no order**.
4. Build the object:
   ```json
   { "value": 6.1, "unit": "%", "date": "2023-10-13T22:22:00+00:00", "order_placed": false }
   ```
5. `FINISH([{"value":6.1,"unit":"%","date":"2023-10-13T22:22:00+00:00","order_placed":false}])`

**If the date had been older than 1 year:**
- POST the ServiceRequest for LOINC 4548‑4.
- Set `"order_placed": true` in the final object.

## Success Indicators
- The FINISH call contains a single JSON object (or a raw integer for age) inside the list.
- The object includes the keys `value`, `unit`, `date`, and `order_placed` (or just the integer for age).
- No free‑text sentences appear inside the FINISH payload.

## Failure Indicators
- FINISH payload is a list of strings or contains narrative text.
- Missing any of the required keys (`value`, `unit`, `date`).
- Age is returned as a string or wrapped in a list instead of a raw number.
- The agent posts an order but does not update `order_placed` in the output.
