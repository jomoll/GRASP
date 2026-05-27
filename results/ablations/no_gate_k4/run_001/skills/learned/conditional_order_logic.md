---
description: "Add generic lab\u2011recency ordering pattern to prevent unnecessary\
  \ ServiceRequests"
name: conditional_order_logic
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 5
  triggering_sample_ids:
  - task1_12
  - task1_20
  - task1_11
  - task1_16
  - task1_13
  - task10_10
  - task10_12
  - task10_13
  - task9_1
  - task1_26
  update_cycle: 1
tags: []
version: 6
---

# Conditional Order Logic

## Pattern Description
You must decide whether to place a ServiceRequest based on the recency of a lab result. The same decision‑making pattern used for electrolyte replacement (potassium/magnesium) applies to any lab where the task optionally asks for a repeat order if the existing result is older than a threshold (e.g., 1 year). This prevents the agent from creating unnecessary orders when a recent result already exists.

## When to Use This Skill
- When a task asks for the *latest value* of a lab (e.g., HbA1c, TSH) **and** adds a conditional clause such as “If the result is older than X, order a new test.”
- The task provides the LOINC code for ordering the lab (e.g., `code=4548-4` for HbA1c).
- The agent has already performed a GET on `Observation?code=<labCode>&patient=<id>`.

## Common Failure Patterns
- Posting a ServiceRequest unconditionally after a lab query, even when the result is recent.
- Using the wrong LOINC code for the order (e.g., ordering a different test).
- Omitting the `authoredOn` timestamp or using a static past date.

## Recommended Patterns
**Pattern 1: Recency‑Based Order Decision**
1. After the GET, inspect each entry in the Bundle for `effectiveDateTime` (or `issued`).
2. Parse the timestamp into a datetime object.
3. Compare it to the task’s current‑time context (provided in the prompt, e.g., `2023-11-13T10:15:00+00:00`).
4. If **no Observation** is found **or** the newest timestamp is **older than the threshold** (default 1 year, unless the task specifies otherwise), proceed to step 5. Otherwise, **skip ordering**.
5. Build a ServiceRequest JSON:
   ```json
   {
     "resourceType": "ServiceRequest",
     "code": { "coding": [{ "system": "http://loinc.org", "code": "<orderLOINC>", "display": "<display>" }] },
     "authoredOn": "<taskCurrentTime>",
     "status": "active",
     "intent": "order",
     "priority": "routine",
     "subject": { "reference": "Patient/<patientId>" }
   }
   ```
6. POST the ServiceRequest **only** when step 5 is reached.

**Pattern 2: No‑Order Fallback**
- If the result is recent, simply return the extracted value (and timestamp if requested) and **do not** issue any POST.

**Pattern 3: Output Formatting**
- When the task asks for the date, return `[value, "YYYY‑MM‑DDThh:mm:ss+00:00"]`.
- When no date is requested, return the scalar value alone.

## Example Application
**Task:** “What’s the last HbA1C value for patient S1311412 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test.”

**Step‑by‑step:**
1. GET `Observation?code=A1C&patient=S1311412`.
2. Extract the most recent `valueQuantity.value` = `5.9` and `effectiveDateTime` = `2023-11-12T06:19:00+00:00`.
3. Compare `2023-11-12` to the task current time `2023-11-13`; difference < 1 year → **no order**.
4. FINISH `[5.9, "2023-11-12T06:19:00+00:00"]`.

**If the date had been `2021‑10‑01`**, step 3 would trigger the POST with the ordering LOINC `4548-4` and then FINISH the same array.

## Success Indicators
- No ServiceRequest POST appears when the lab result is within the allowed recency window.
- When an order is required, the POST body matches the template exactly (correct LOINC, patient reference, `authoredOn`).
- FINISH output includes a timestamp array when the task wording requests a date.

## Failure Indicators
- A ServiceRequest is posted despite a recent lab result.
- The POST body contains the wrong LOINC code or missing `authoredOn`.
- FINISH returns only the value without a timestamp when the task explicitly asks for the date.
