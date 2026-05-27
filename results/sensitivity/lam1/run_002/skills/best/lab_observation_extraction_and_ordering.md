---
description: Add mandatory Observation GET query before extracting lab values and
  ordering repeat tests
name: lab_observation_extraction_and_ordering
provenance:
  action: MODIFY
  epoch: 4
  fixes: 8
  parent_version: 1
  probe_score: 2
  regressions: 3
  triggering_sample_ids:
  - task9_8
  - task4_7
  - task8_7
  - task8_21
  - task5_17
  - task8_23
  - task5_16
  - task9_3
  - task9_11
  - task5_7
  update_cycle: 0
tags:
- lab
- observation
- query
- extraction
- ordering
version: 2
---

# Lab Observation Extraction and Ordering

## Pattern Description
You must first retrieve the relevant Observation resources before trying to extract a value or decide whether to order a repeat test. The pattern works for any lab code (e.g., "MG" for magnesium, "K" for potassium, "A1C" for hemoglobin A1c). By separating the *search* step from the *extraction* step you avoid the common failure where the agent attempts to answer without ever issuing a GET request.

## When to Use This Skill
- When a task asks for the most recent value of a lab Observation (any code) within a time window.
- When the task requires you to order a repeat test if the existing result is older than a threshold.
- When the answer must be a plain numeric value (or `-1` if no recent result exists).

## Common Failure Patterns
- Skipping the GET Observation request and trying to answer directly.
- Using the wrong query parameters (`code` vs `category`, missing `patient` reference).
- Forgetting to apply the date range (`ge`/`le`) that the task specifies.
- Returning the whole Observation bundle or a string description instead of the numeric value.

## Recommended Patterns
**Pattern 1: Mandatory Observation query**
1. Build the GET URL:
   ```
   GET {base}/Observation?code={LAB_CODE}&patient=Patient/{MRN}&date=ge{START_ISO}&date=le{END_ISO}
   ```
   - `{LAB_CODE}` is the code supplied in the task (e.g., `MG`).
   - `{START_ISO}` and `{END_ISO}` define the required window (often "now-24h" to "now").
2. Execute the GET request and capture the response bundle.
3. If `total == 0`, treat the result as *not available* and set the answer to `-1` (or follow the task‑specific fallback).
4. Otherwise, sort the entries by `effectiveDateTime` (or `issued`) descending and pick the first Observation.
5. Extract the numeric value from `valueQuantity.value` (or `valueQuantity` if the unit must be converted).

**Pattern 2: Optional ordering fallback**
- After extraction, compare the Observation date to the task‑provided threshold.
- If the date is older than the threshold, construct a ServiceRequest POST using the ordering LOINC/SNOMED code supplied in the task.
- Include `authoredOn` = current time, `status` = "active", `intent` = "order", and reference the patient.

**Pattern 3: Output formatting**
- Return only the numeric value (or `-1`) in a JSON array: `FINISH([value])`.
- If an order was placed, return the value and the original date: `FINISH([value, "YYYY‑MM‑DDTHH:MM:SS+00:00"])`.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0636132 within last 24 hours?"

**Step‑by‑step:**
1. Compute window: `START = 2023-11-12T10:15:00Z`, `END = 2023-11-13T10:15:00Z`.
2. GET request:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S0636132&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z
   ```
3. Response bundle has `total = 2`; sort entries, pick the newest Observation.
4. Extract `valueQuantity.value` → `2.0` (already in mg/dL).
5. No ordering needed because a recent value exists.
6. FINISH output:
   ```
   FINISH([2.0])
   ```

## Success Indicators
- A GET Observation request appears in the action log before any FINISH.
- The GET URL contains `code`, `patient`, and both `date=ge` and `date=le` parameters.
- The FINISH output is a numeric array (or `[value, date]` when ordering).

## Failure Indicators
- No GET request for Observation is logged despite the task asking for a lab value.
- The GET URL is missing the `patient` reference or the `code` parameter.
- FINISH returns a string, an array with extra text, or the whole Observation bundle.
- An order is created when the task only required a value and a recent result exists.
