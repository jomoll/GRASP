---
description: Add fallback code search and robust numeric extraction for lab observations
name: observation_lookup_and_value_extraction
provenance:
  action: MODIFY
  epoch: 3
  fixes: 8
  parent_version: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task9_11
  - task9_27
  - task10_8
  - task10_17
  - task9_20
  - task9_9
  - task9_28
  - task4_20
  update_cycle: 0
tags: []
version: 2
---

# Observation Lookup and Numeric Value Extraction with Fallback

## Pattern Description
You must retrieve the most recent laboratory or electrolyte Observation for a patient and return **only the raw numeric value** (or the defined sentinel `-1` when unavailable).  The skill first tries to map a shorthand name (e.g., "K", "MG") to its LOINC code and query using that code.  If the LOINC query returns no entries, you must fall back to searching with the original token supplied in the task (the raw code string) to handle systems that store the observation under a local code.  After a bundle is returned, extract the numeric value from the Observation regardless of how it is represented – `valueQuantity.value`, a numeric `valueString`, or a component entry that contains a `valueQuantity`.  Never emit human‑readable summary text; only emit a JSON array containing the number (or `-1`).

## When to Use This Skill
- When a task asks for the most recent value of a lab/electrolyte (e.g., potassium, magnesium, HbA1c) and expects a plain number.
- When the task provides a shorthand code that may need LOINC translation.
- When the Observation may be stored under the original token instead of the LOINC code.
- When the Observation value can appear as `valueQuantity`, `valueString`, or within a `component` array.

## Common Failure Patterns
- Querying only the LOINC code and receiving an empty bundle even though the observation exists under a local code.
- Extracting `valueQuantity.value` but the Observation uses `valueString` like `"3.5"` or includes units (e.g., `"3.5 mmol/L"`).
- Ignoring `component` entries that hold the desired measurement, resulting in `-1`.
- Returning a string or an array with units instead of a pure numeric value.

## Recommended Patterns
**Pattern 1: Core lookup and extraction**
1. Translate the supplied shorthand (e.g., "K", "MG") to its LOINC code using the internal map.
2. Issue `GET {base}/Observation?code={LOINC}&patient={MRN}`.
3. If the bundle `total` is 0, **fallback**: issue `GET {base}/Observation?code={original_token}&patient={MRN}`.
4. From the returned bundle, select the entry with the most recent `effectiveDateTime` (or `issued`).
5. Extract the numeric value:
   - If `valueQuantity` exists, use `valueQuantity.value`.
   - Else if `valueString` exists, parse the string for a leading number (ignore trailing units).
   - Else if `component` array exists, locate the component whose `code.coding.code` matches the target LOINC or original token and extract its `valueQuantity.value`.
6. Return `FINISH([numeric_value])`. If no numeric value can be found, return `FINISH([-1])`.

**Pattern 2: Fallback handling**
- After step 3, if the second query also yields `total` = 0, immediately return `FINISH([-1])`.
- Log (conceptually) that the observation was not found for debugging, but do not emit any text to the user.

**Pattern 3: Formatting rule**
- The final output must be a JSON array containing a single number (or `-1`).
- Do **not** wrap the number in a string, do not include units, and do not add explanatory text.

## Example Application
**Task:** "Check patient S3228213's most recent potassium level. If low, then order replacement potassium."

**Step‑by‑step:**
1. Shorthand `K` → LOINC `2823-3`.
2. `GET /Observation?code=2823-3&patient=S3228213` → bundle empty.
3. Fallback: `GET /Observation?code=K&patient=S3228213` → bundle contains an Observation with `valueQuantity.value = 3.2`.
4. Extract `3.2`.
5. Return `FINISH([3.2])`.

**Correct output:** `FINISH([3.2])`
**Incorrect output:** `FINISH(["3.2 mmol/L"])` or `FINISH([-1])` when the observation exists.

## Success Indicators
- The agent finishes with `FINISH([<number>])` for tasks that have a valid observation, even when the LOINC‑only query would have been empty.
- Numeric values are extracted from any of the supported fields without trailing units.

## Failure Indicators
- The agent returns `FINISH([-1])` despite the Observation being present in the fallback query.
- The output contains a string, units, or additional text (e.g., `"Potassium is 3.2 mmol/L"`).
- The agent does not attempt the fallback query when the first query yields no entries.
