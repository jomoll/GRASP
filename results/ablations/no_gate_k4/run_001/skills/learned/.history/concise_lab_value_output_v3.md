---
description: Force scalar lab result with unit as the sole FINISH payload
name: concise_lab_value_output
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 2
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
tags: []
version: 3
---

# Concise Lab Value Output

## Pattern Description
You must always return a single scalar lab value together with its unit as the *only* element of the FINISH call. The agent should never wrap the value in an array, nor return a free‑text narrative. This pattern applies to any Observation lookup where the task asks for “the last X value” and expects a machine‑readable answer.

## When to Use This Skill
- After a GET /Observation that returns a Bundle with at least one entry and the task asks for the most recent value.
- When the task wording is “What’s the last <lab> value” or “Check the most recent <lab> level”.
- The response must be a scalar (number) **or** a string that already includes the unit (e.g., `"5.2%"`). No additional text or JSON objects are allowed.

## Common Failure Patterns
- `FINISH(["4.7 mmol/L"])` – value inside an array and as a string.
- `FINISH([5.2, "2022-08-09T15:33:00+00:00"])` – returning a tuple of value and timestamp.
- `FINISH([{"value":4.7,"unit":"mmol/L"}])` – returning a JSON object instead of a plain scalar.

## Recommended Patterns
**Pattern 1: Extract and format the scalar**
1. Locate the first entry in the Bundle (`entry[0].resource`).
2. Prefer `valueQuantity.value` and `valueQuantity.unit`. If the unit is missing, fall back to `valueString`.
3. Build the output string **only if the unit is part of the value**; otherwise concatenate as `"{value} {unit}"`.
4. Call `FINISH([output])` where `output` is a single string (e.g., `"4.7 mmol/L"`).

**CORRECT**: `FINISH(["4.7 mmol/L"])`
**WRONG**: `FINISH(["4.7", "mmol/L"])` or `FINISH(["4.7 mmol/L", "2023-11-13T10:15:00+00:00"])`

**Pattern 2: Fallback when no Observation**
- If the Bundle `total` is 0, invoke the `missing_observation_placeholder` skill instead of returning an empty array.

**Pattern 3: Validation before FINISH**
- Verify that the FINISH argument is a list of length 1 and that the element is a string matching `/^[0-9.]+\s*\w+$/`.
- If validation fails, raise a warning and re‑extract using the fallback rule.

## Example Application
**Task:** "What’s the last potassium level for patient S123456?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S123456`
2. Parse the Bundle, take `entry[0].resource.valueQuantity.value` = `4.7` and `unit` = `mmol/L`.
3. Build `output = "4.7 mmol/L"`.
4. `FINISH([output])`

**CORRECT output:** `FINISH(["4.7 mmol/L"])`
**WRONG output:** `FINISH(["4.7 mmol/L", "2023-11-13T10:15:00+00:00"])`

## Success Indicators
- FINISH payload is a list of length 1.
- The sole element is a string that contains a numeric value followed by a space and a unit.
- No timestamp or extra narrative appears in the FINISH call.

## Failure Indicators
- FINISH contains an array with more than one element.
- The element is a JSON object or a plain number without unit.
- A timestamp is included alongside the value.
- The agent returns raw JSON from the placeholder skill instead of the scalar.
