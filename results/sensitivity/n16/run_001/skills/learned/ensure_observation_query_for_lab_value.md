---
description: Require an Observation GET for any task that asks for a recent lab value
  before producing the answer.
name: ensure_observation_query_for_lab_value
provenance:
  action: ADD
  epoch: 1
  fixes: 4
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task4_10
  - task10_24
  - task9_14
  - task9_20
  - task10_18
  - task10_17
  - task2_15
  update_cycle: 0
tags:
- lab
- observation
- query
version: 1
---

# ensure_observation_query_for_lab_value

## Pattern Description
You must always retrieve the relevant Observation resource before answering any question that requests a recent laboratory measurement (e.g., magnesium, potassium, HbA1c, creatinine). The task usually specifies a code, a time window, and expects a scalar numeric answer (or -1 if no recent result). By forcing a search first, you avoid returning default or empty answers and ensure the value you report is based on actual chart data.

## When to Use This Skill
- When the instruction contains phrases like "most recent *X* level", "last *X* value", "check patient *Y*'s *X* within last *N* hours/days", or "what’s the *X* result".
- When a LOINC or custom code (e.g., `MG`, `K`, `A1C`) is mentioned.
- When the expected answer is a single number (or -1) rather than a free‑text sentence.

## Common Failure Patterns
- The agent calls `FINISH` directly without any `GET /Observation` request.
- The agent queries Observation but omits the required `code` or `patient` parameters.
- The agent queries Observation but forgets to apply a date filter (`ge`/`le`) for the required time window.
- The agent extracts the value from the wrong field (e.g., `valueString` instead of `valueQuantity.value`).

## Recommended Patterns
**Pattern 1: Core retrieval strategy**
1. If the task supplies an MRN only, first `GET /Patient?identifier={MRN}` to obtain the FHIR patient reference ID.
2. Construct an Observation search URL:
   ```
   GET {base}/Observation?code={CODE}&patient={PatientID}&date=ge{START_TIME}Z
   ```
   - `{CODE}` is the lab code from the task (e.g., `MG`).
   - `{START_TIME}` is the ISO‑8601 timestamp representing the start of the required window (e.g., now‑24h).
   - Optionally add `date=le{END_TIME}` if an upper bound is needed.
3. Parse the returned Bundle. If `total == 0`, treat as “no recent result”.
4. Otherwise, locate the entry with the most recent `effectiveDateTime` and read `valueQuantity.value` (numeric) and `valueQuantity.unit`.
5. Convert units if necessary (e.g., mmol/L → mg/dL) and round as the task requires.

**Pattern 2: Fallback when no result**
- If the Observation search returns no entries, output `-1` (or the task‑specified placeholder) and **do not** create any ServiceRequest or MedicationRequest.

**Pattern 3: Formatting the final answer**
- Return a plain scalar wrapped in `FINISH([...])`:
  - Correct: `FINISH([1.8])`
  - Wrong: `FINISH(["1.8 mg/dL"])` or `FINISH(["Result is 1.8"] )`

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3213957 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S3213957`
2. Extract the patient reference, e.g., `Patient/S3213957`.
3. Compute start time: `2023-11-12T10:15:00Z` (now minus 24 h).
4. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S3213957&date=ge2023-11-12T10:15:00Z`
5. If the bundle contains entries, pick the one with the latest `effectiveDateTime` and read `valueQuantity.value` → `1.8`.
6. `FINISH([1.8])`

**If the bundle is empty:**
- `FINISH([-1])`

## Success Indicators
- An Observation GET appears in the action log before any `FINISH`.
- The GET URL includes both `code=` and `patient=` (and a `date=` filter when a time window is specified).
- The final `FINISH` payload is a single‑element list containing a number (or -1).

## Failure Indicators
- `FINISH` is called without a preceding Observation GET.
- Observation GET is missing `code` or `patient` parameters.
- Date filter is absent when the task mentions a time window.
- The answer is returned as a string, sentence, or list of strings instead of a numeric scalar.
