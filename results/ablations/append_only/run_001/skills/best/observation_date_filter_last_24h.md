---
description: "Add a 24\u2011hour date filter to Observation searches when the task\
  \ requires recent results."
name: observation_date_filter_last_24h
provenance:
  action: ADD
  epoch: 3
  fixes: 4
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task10_13
  - task10_17
  update_cycle: 0
tags:
- date_filter
- observation
- time_window
version: 1
---

# Observation 24‑Hour Date Filter Strategy

## Pattern Description
You must ensure that any Observation search that is meant to retrieve a value "within the last 24 hours" (or similar phrasing) is constrained to that time window.  The FHIR search API supports a `date` parameter with comparison prefixes.  By adding `date=gt{now-24h}` (or `date=ge{now-24h}`) you guarantee that only observations recorded after the cutoff are considered, preventing stale values from being used.

## When to Use This Skill
- When the task wording contains **"within last 24 hours"**, **"last 24 hours"**, **"most recent … within last 24 hours"**, or any equivalent time‑window phrase.
- When the task asks for the *most recent* value of a lab or vital sign and the answer must be based on a recent measurement.
- When the task includes a conditional action (e.g., order replacement if low) that depends on the recency of the result.

## Common Failure Patterns
- GET request only includes `code` and `patient` (e.g., `GET /Observation?code=MG&patient=S123`).
- The returned Observation is older than 24 h, yet the agent treats it as current.
- The agent returns a value with an outdated timestamp without indicating the failure.

## Recommended Patterns
**Pattern 1: Core date‑filter strategy**
1. Parse the task context to obtain the current timestamp (`now`).
2. Compute the cutoff timestamp: `cutoff = now - 24h` (ISO‑8601 format, e.g., `2023-11-12T10:15:00+00:00`).
3. Build the GET URL:
   ```
   GET {base}/Observation?code={CODE}&patient={MRN}&date=gt{cutoff}&_sort=-date
   ```
   - `date=gt{cutoff}` limits results to observations after the cutoff.
   - `_sort=-date` ensures the bundle is ordered newest‑first.
4. Inspect the returned bundle. If `total > 0`, extract the first entry’s value (e.g., `valueQuantity.value` or `valueString`).
5. Pass the extracted scalar to the existing `format_lab_result_scalar_string` skill for final FINISH formatting.

**Pattern 2: No recent result fallback**
- If the bundle is empty (`total == 0`), do **not** treat the result as low.  Return the task‑specific "no result" message (e.g., `-1` for numeric queries or a phrased string like "No magnesium result in last 24 hours; no replacement ordered.").

**Pattern 3: Output consistency**
- Always output a plain scalar (number or string) without extra commentary unless the task explicitly asks for a free‑text note.
- Use the `format_lab_result_scalar_string` skill to enforce the scalar‑string FINISH format.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S1876702 within last 24 hours?"

**Step‑by‑step:**
1. `now = 2023-11-13T10:15:00+00:00` (provided in task context).
2. `cutoff = 2023-11-12T10:15:00+00:00`.
3. Issue GET:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S1876702&date=gt2023-11-12T10:15:00+00:00&_sort=-date
   ```
4. If the bundle contains an entry, extract `valueQuantity.value` (e.g., `1.6`).
5. Call `format_lab_result_scalar_string` to produce:
   ```
   FINISH([1.6])
   ```
6. If the bundle is empty, output the no‑result string defined by the task.

## Success Indicators
- The GET URL includes a `date=gt…` (or `date=ge…`) parameter.
- The bundle is sorted with newest first (`_sort=-date`).
- The FINISH output is a plain scalar or the prescribed no‑result message.

## Failure Indicators
- The GET request lacks any `date` filter despite the task mentioning a 24‑hour window.
- The agent returns a value whose `effectiveDateTime` is older than the cutoff.
- The FINISH output contains extra explanatory text when a scalar is required.
