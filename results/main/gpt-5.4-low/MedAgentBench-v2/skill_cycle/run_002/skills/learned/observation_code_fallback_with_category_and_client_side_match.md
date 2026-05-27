---
description: When direct Observation code search is empty, fall back to broader category
  search and match codings client-side.
name: observation_code_fallback_with_category_and_client_side_match
provenance:
  action: ADD
  epoch: 3
  fixes: 2
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task1_13
  - task2_14
  - task10_20
  - task10_10
  - task10_16
  - task3_27
  - task10_21
  - task3_3
  - task8_29
  - task10_12
  update_cycle: 0
tags:
- fhir
- observation
- fallback
- vital-signs
- heart-rate
version: 1
---

# Observation Code Fallback With Category And Client-Side Match

## Pattern Description

When a task asks for a specific observation but a direct `Observation?code=...` search returns no entries, you must not immediately conclude the observation is absent. In many datasets, the task text may give a shorthand token or local alias, while the stored Observation uses a different coding system, code, or display string. The reusable strategy is to fall back to a broader Observation search, then inspect each returned resource's `code.coding` and `code.text` client-side to identify the target observation.

This matters most for vital signs and other commonly coded observations where the stored code may be standard LOINC or a display label rather than the task's literal token. The behavior change is: after an empty direct code search, broaden retrieval first, then filter locally, then compute the requested result from matched observations instead of returning `null` or "no observations found."

## When to Use This Skill

- When a GET `/Observation?...&code=...` returns `total: 0` or an empty `entry` array but the task strongly expects common observations like heart rate, blood pressure, temperature, SpO2, or labs
- When the task provides a nonstandard shorthand token such as `HEARTRATE` and a direct code-token search returns nothing
- When the task asks for an aggregate over a time window and an empty direct code search would otherwise cause you to finish with `[null, null]` or a "none found" statement
- When querying vital signs and you can use `category=vital-signs` as a broader retrieval set

## Common Failure Patterns

- Treating `code=HEARTRATE` as authoritative and stopping when `/Observation?patient=...&code=HEARTRATE` returns zero results
- Using `category=vital-signs` as a fallback but not inspecting returned resources' `code.coding[].code`, `code.coding[].display`, or `code.text`
- Returning `FINISH([null, null])` after a failed code-token search without any client-side matching attempt
- Computing a heart-rate aggregate from all vital signs returned by `category=vital-signs` instead of filtering to heart-rate observations only
- Extracting text like `"72 bpm"` instead of numeric `valueQuantity.value` for averaging
- Forgetting to use the task's explicit time windows after broad retrieval, causing the 6-hour and 12-hour values to become identical or stale

## Recommended Patterns

**Pattern 1: primary search, then broad fallback**
First try the direct query the task suggests.

If that returns no observations, broaden the search while preserving patient and relevant date bounds. For vital signs, use:
`GET /Observation?patient={patient_id_or_identifier}&category=vital-signs&date=ge{start}&date=le{end}`

Then inspect each returned Observation and keep only those whose target identity matches by any of:
- `code.coding[].code`
- `code.coding[].display`
- `code.text`

For heart rate, match known heart-rate indicators such as `8867-4`, `Heart rate`, or equivalent heart-rate display text.

CORRECT: broad retrieve, then keep only observations with heart-rate coding/display
WRONG: treat all `category=vital-signs` observations as heart rate

**Pattern 2: client-side matching and numeric extraction**
For each candidate Observation, inspect:
- `resource.code.coding[]`
- `resource.code.text`
- `resource.valueQuantity.value`
- fallback numeric representations only if `valueQuantity.value` is absent
- `effectiveDateTime` (or relevant effective field) for time-window inclusion

Only average numeric values from matched observations.

CORRECT: use `valueQuantity.value` values like `72`, `88`, `95`
WRONG: average strings like `"72 bpm"`, or include respiration rate / temperature values from the same bundle

**Pattern 3: finish with computed outputs, not search-status outputs**
After matching the correct observation type, apply the requested windows separately and compute the aggregate. Return the final output in the task-required format, typically numeric results or explicit no-data statements only after both direct and fallback retrieval strategies fail.

If no matched observations remain after client-side filtering, then you may conclude no relevant observations were found in that window.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S2016972."

**Step-by-step:**

1. Issue direct search first:
   `GET /Observation?patient=S2016972&code=HEARTRATE&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
2. If that returns empty, issue broader fallback:
   `GET /Observation?patient=S2016972&category=vital-signs&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
3. From each returned Observation, inspect `code.coding[].code`, `code.coding[].display`, and `code.text`; keep only heart-rate observations such as code `8867-4` or display `Heart rate`.
4. Extract numeric values from `valueQuantity.value` and use each Observation's effective time to build separate 6-hour and 12-hour subsets.
5. Compute each mean and return only the results.

CORRECT output: `FINISH([82.5, 79.8])`
WRONG output:   `FINISH([null, null])`
WRONG output:   `FINISH(["No heart rate observations found in the past 6 hours", "No heart rate observations found in the past 12 hours"])` after only the empty `code=HEARTRATE` search

## Success Indicators

- After an empty direct `code` search, you issue a broader Observation search rather than stopping
- You inspect `code.coding`, `code.text`, and `valueQuantity.value` on returned resources
- You compute aggregates only from observations that truly match the requested measurement
- Final answers contain computed values when matching observations exist under alternate codings

## Failure Indicators

- You finish immediately after `total: 0` from a direct `code=...` Observation search
- You use `category=vital-signs` but never filter the returned observations by coding/display
- You average unrelated vital signs together
- You output `null`, "no observations found," or narrative placeholders when matched observations were available through broader retrieval
