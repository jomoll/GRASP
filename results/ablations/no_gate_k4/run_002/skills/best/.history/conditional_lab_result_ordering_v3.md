---
description: "Add low\u2011value and stale\u2011result checks so the agent orders\
  \ replacements or repeat labs when required"
name: conditional_lab_result_ordering
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task10_20
  - task10_27
  - task9_28
  - task8_29
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

# Conditional Lab Result Ordering

## Pattern Description
You must decide whether to place an order based on the most recent lab Observation.  The core pattern extracts the numeric value (and its unit) from the Observation, compares it against a clinically‑relevant threshold, and, if the value is out of range **or** the result is older than an allowed interval, creates a ServiceRequest.  This pattern is reusable for any lab where a "low" trigger or a "stale" trigger is defined (e.g., potassium, magnesium, HbA1c).

## When to Use This Skill
- When a task asks to *check a lab value and order a replacement if the value is low* (e.g., potassium < 3.5 mmol/L, magnesium < 1.5 mg/dL).
- When a task asks to *order a repeat test if the most recent result is older than a specified period* (e.g., HbA1c older than 1 year).
- When the Observation bundle may contain multiple entries; you must pick the most recent entry by `effectiveDateTime`.

## Common Failure Patterns
- The agent extracts the value but never compares it to the low‑value threshold, resulting in `FINISH(["no replacement ordered"])`.
- The agent ignores the `effectiveDateTime` and therefore never detects a stale result.
- The agent returns a scalar string instead of a JSON list, violating the `verify_before_finish` contract.
- The agent creates an order but uses the wrong NDC or LOINC code because the mapping is missing.

## Recommended Patterns
**Pattern 1: Extract the latest numeric value**
1. From the Observation Bundle, locate the entry with the greatest `effectiveDateTime`.
2. Read `valueQuantity.value` (numeric) and `valueQuantity.unit`.
3. Store as `lab_value` and `lab_unit`.

**Pattern 2: Apply low‑value trigger**
- Define a threshold map, e.g. `{ "K": { "low": 3.5, "unit": "mmol/L" }, "MG": { "low": 1.5, "unit": "mg/dL" } }`.
- If `lab_value < threshold.low` **and** `lab_unit` matches the expected unit, proceed to order replacement.

**Pattern 3: Apply stale‑result trigger**
1. Parse `effectiveDateTime` into a datetime object.
2. Compute `age = now - effectiveDateTime`.
3. If `age > allowed_interval` (e.g., 365 days for HbA1c), create a new ServiceRequest.

**Pattern 4: Build the ServiceRequest**
- Use the appropriate coding system:
  - Replacement medication: `system: http://hl7.org/fhir/sid/ndc`, `code: <NDC>`.
  - Lab order: `system: http://loinc.org`, `code: <LOINC>`.
- Populate required fields (`authoredOn`, `status`, `intent`, `priority`, `subject`).
- POST to `/fhir/ServiceRequest`.

**Pattern 5: FINISH output**
- If an order was placed, `FINISH(["order placed"])`.
- If no order is needed, `FINISH(["no replacement ordered"])`.
- Always wrap the string in a JSON list.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium. Also schedule a repeat potassium draw tomorrow at 8 am."

**Step‑by‑step:**
1. `GET /fhir/Observation?code=K&patient=S3228213`.
2. From the returned Bundle, pick the entry with the latest `effectiveDateTime`.
3. Extract `valueQuantity.value = 3.2` and `valueQuantity.unit = "mmol/L"`.
4. Compare to threshold 3.5 mmol/L → value is low.
5. Build a ServiceRequest for replacement potassium using the NDC supplied in the task context.
6. POST the ServiceRequest.
7. Build a second ServiceRequest for a repeat potassium draw (code = same LOINC, `scheduledDateTime = now + 1 day at 08:00`).
8. POST the second ServiceRequest.
9. `FINISH(["order placed"])`.

**Correct output:** `FINISH(["order placed"])`
**Wrong output:** `FINISH(["no replacement ordered"])` (low value not detected) or `FINISH("order placed")` (not a list).

## Success Indicators
- The agent posts a ServiceRequest whenever the lab value is below the defined low threshold.
- The agent posts a ServiceRequest when the result date exceeds the allowed interval.
- The final `FINISH` call always contains a JSON list with a single string.

## Failure Indicators
- No ServiceRequest is posted despite a low value or stale result.
- The agent returns a scalar string or includes extra explanatory text in the FINISH payload.
- The wrong coding system or code is used in the ServiceRequest.

---
*This modification expands the original conditional ordering skill to cover low‑value detection, stale‑result detection, and strict FINISH formatting, eliminating the dominant `conditional_order_missing` failures observed in the current batch.*
