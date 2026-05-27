---
description: Retrieve a recent Observation value (e.g., Mg, HbA1c) and handle missing
  or stale results
name: observation_recent_value_reporting
provenance:
  action: ADD
  epoch: 4
  fixes: 5
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task10_24
  - task10_21
  - task10_20
  - task10_16
  - task4_21
  - task10_12
  update_cycle: 0
tags: []
version: 1
---

# Observation Recent Value Retrieval and Staleness Handling

## Pattern Description
You must reliably fetch the most recent `Observation` for a given LOINC or custom code, optionally constrained by a time window, and return the numeric value (and date when required). If no observation exists in the window, return `-1`. If an observation exists but is older than a task‑specific freshness threshold (e.g., >1 year for HbA1c), you must decide whether to order a new test instead of reporting the stale value. This pattern prevents the agent from stalling on a retrieval request or from incorrectly ordering when a valid result is already present.

## When to Use This Skill
- When a task asks for "the most recent *X* level within the last N hours" (e.g., magnesium, potassium).
- When a task asks for the "last *X* value and its date" and includes a staleness rule (e.g., HbA1c older than 1 year triggers a new order).
- When the agent has already fetched the patient resource and is about to query `Observation` but does not know how to interpret the bundle.

## Common Failure Patterns
- Returning `[-1]` without attempting to extract any value, even though a recent observation exists.
- Extracting the entire `valueQuantity` object or the `valueString` instead of the numeric `valueQuantity.value`.
- Ignoring the `effectiveDateTime`/`issued` field, leading to stale values being reported as current.
- Ordering a new test when a recent result is already present (duplicate order).

## Recommended Patterns
**Pattern 1: Core retrieval**
1. Build the GET URL: `GET {base}/Observation?code={CODE}&patient=Patient/{MRN}&date=ge{START}` where `{START}` is `now - window` (e.g., `2023-11-12T10:15:00+00:00`).
2. Inspect the returned `Bundle.entry` array:
   - If `total == 0`, **output** `FINISH([-1])` (or `FINISH([-1])` for numeric tasks, `FINISH([])` for ordering‑only tasks).
   - Otherwise, sort entries by `resource.effectiveDateTime` (or `resource.issued`) descending and pick the first.
3. Extract the numeric value:
   - **CORRECT**: `value = entry.resource.valueQuantity.value` (a number).
   - **WRONG**: using `valueQuantity` as a string or including the unit.
4. If the task also requires the date, capture `date = entry.resource.effectiveDateTime`.
5. **Output**:
   - For pure numeric answer: `FINISH([value])`.
   - For value + date: `FINISH(["{value}% on {date[:10]}"])` (preserve formatting required by the task).

**Pattern 2: Staleness check & ordering fallback**
1. After extracting `value` and `date`, compute the age: `age_days = now - date`.
2. If `age_days > STALE_DAYS` (e.g., 365 for HbA1c):
   - **Do not** return the stale value.
   - Construct a `ServiceRequest` for the appropriate LOINC code (e.g., `4548-4` for HbA1c) with `note.text` explaining the staleness.
   - POST the request and then `FINISH(["{value}% on {date[:10]}"])` **only if** the task still expects the old result; otherwise just `FINISH([])` after ordering.
3. If the value is fresh, skip ordering and return the value as in Pattern 1.

**Pattern 3: Formatting the final output**
- Always wrap the answer in a JSON array as the task expects.
- Do **not** include explanatory sentences; the array must contain only the raw value (or value + date string).

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S0674240&date=ge2023-11-12T10:15:00+00:00`
2. Bundle contains two entries; pick the one with the latest `effectiveDateTime`.
3. Extract `valueQuantity.value` → `2.1`.
4. `FINISH([2.1])`

**Task:** "What’s the last HbA1c value for patient S6500497 and when was it recorded? If the result is >1 year old, order a new test."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=Patient/S6500497`
2. Bundle has an entry dated 2022‑08‑09 (age > 365 days).
3. Because the result is stale, construct a `ServiceRequest` with LOINC `4548-4` and a note about staleness, POST it.
4. Return the existing result: `FINISH(["5.2% on 2022-08-09"])`.

## Success Indicators
- The agent returns a numeric array (or value + date string) when a recent observation exists.
- The agent returns `[-1]` only when the bundle is empty for the requested window.
- No duplicate `ServiceRequest` is created when a fresh observation is present.
- When a stale observation is detected, a correctly formed `ServiceRequest` is posted before finishing.

## Failure Indicators
- The agent finishes with `[-1]` despite the Observation bundle containing entries.
- The returned array contains a string with units (e.g., `"2.1 mg/dL"`) instead of a pure number.
- A new `ServiceRequest` is posted even though a fresh result exists.
- The agent omits the date component when the task explicitly asks for it.
