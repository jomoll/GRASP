---
description: "Add pre\u2011check for missing Observation GET and enforce string\u2011\
  type no\u2011result output"
name: lab_observation_query_before_finish
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 3
  triggering_sample_ids:
  - task9_6
  - task9_9
  - task4_27
  - task5_19
  - task5_3
  - task4_20
  - task2_30
  - task4_4
  - task10_10
  - task4_15
  update_cycle: 1
tags: []
version: 4
---

# Lab Observation Query Before Finish (updated)

## Pattern Description
When a task asks for the most recent lab value, you must first query the Observation endpoint.  If the query returns no entries, you must return a **scalar string** `"-1"` (or the task‑specific no‑result message) inside a JSON array, and you must never skip the GET request.

## When to Use This Skill
- Any instruction that requests the latest value of a lab, electrolyte, or other Observation (e.g., *"most recent magnesium level"*, *"last serum potassium"*).
- When the task also includes a conditional action based on that value.

## Common Failure Patterns
- Agent answers directly with `FINISH([-1])` or a custom message without first issuing `GET /Observation`.
- Agent returns a numeric `-1` instead of the required string `"-1"`.
- Agent uses the wrong query parameters (missing `code`, `patient`, or date range).

## Recommended Patterns
**Pattern 1: Mandatory GET before any answer**
1. Parse the task to extract:
   - `code` (LOINC or custom identifier)
   - `patient` MRN
   - Optional date range (`ge…`/`le…`).
2. Issue the GET request exactly:
   ```
   GET {base}/Observation?code={CODE}&patient={MRN}&date=ge{START}&date=le{END}&_sort=-date&_count=1
   ```
3. Wait for the response before proceeding.

**Pattern 2: Handle empty bundles**
- If `Bundle.total == 0`:
  - Return the task‑specified placeholder **as a string** inside an array, e.g., `FINISH(["-1"])` or `FINISH(["no replacement ordered"])`.
- Do **not** fabricate a numeric placeholder.

**Pattern 3: Extract and format the value**
- When a result exists, pull `valueQuantity.value` and optionally `valueQuantity.unit`.
- If the task requires unit conversion, apply it before constructing the final answer.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1521703 within last 24 hours?"

**Steps:**
1. `GET {base}/Observation?code=MG&patient=S1521703&date=ge2023-11-12T10:15:00&date=le2023-11-13T10:15:00&_sort=-date&_count=1`
2. If the bundle is empty, `FINISH(["-1"])`.
3. If a result exists, extract `valueQuantity.value` (e.g., `1.8`) and unit (`mg/dL`), then `FINISH(["1.8 mg/dL"])`.

## Success Indicators
- A correctly formed Observation GET appears before any `FINISH`.
- Empty results produce a **string** placeholder inside a JSON array.
- Non‑empty results are extracted and returned in the exact format the task demands.

## Failure Indicators
- `FINISH` without a preceding Observation GET.
- Numeric `-1` or other placeholder returned instead of a string.
- Missing or incorrect query parameters (e.g., omitted `code` or `patient`).
