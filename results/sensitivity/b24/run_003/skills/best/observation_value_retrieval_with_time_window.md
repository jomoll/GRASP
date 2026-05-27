---
description: Retrieve and validate a lab Observation value within a specified time
  window before finishing.
name: observation_value_retrieval_with_time_window
provenance:
  action: ADD
  epoch: 1
  fixes: 16
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task4_28
  - task5_17
  update_cycle: 0
tags: []
version: 1
---

# Observation Value Retrieval with Time Window

## Pattern Description
You must reliably obtain a numeric lab or vital sign value from a FHIR Observation resource when a task requests the most recent measurement within a defined time window (e.g., last 24 hours). The pattern includes constructing the correct search query, verifying that the response contains at least one entry, selecting the newest entry, extracting the numeric `valueQuantity.value`, performing any required unit conversion, and handling the "no recent result" sentinel value (commonly `-1`). This reusable capability prevents premature `FINISH` calls that ignore missing or out‑of‑range data.

## When to Use This Skill
- When the instruction asks for "most recent *X* level/value" within a time frame (e.g., 24 h, 7 days).
- When the answer must be a single number (or a sentinel such as `-1`) rather than free‑text.
- When the task provides a code (e.g., `MG`, `K`, `A1C`) and expects unit conversion (e.g., mg/dL).
- When the agent would otherwise call `FINISH` without confirming that the Observation bundle contains a suitable entry.

## Common Failure Patterns
- Omitting `date` filters, so the GET may return older observations that should be ignored.
- Ignoring `Bundle.total` or `Bundle.entry` and calling `FINISH` immediately.
- Extracting the wrong field (`valueString`, `valueCodeableConcept`) instead of `valueQuantity.value`.
- Returning the raw string with units (e.g., `"2.2 mg/dL"`) instead of a plain number.
- Failing to convert units when the task specifies a different unit (e.g., µmol/L → mg/dL).
- Using `FINISH([-1])` even when a valid recent observation exists.

## Recommended Patterns
**Pattern 1: Core retrieval and validation**
1. Build the GET URL with the required code, patient identifier, and explicit date range:
   ```
   GET {base}/Observation?code={CODE}&patient={PATIENT_ID}&date=ge{START_ISO}&date=le{END_ISO}
   ```
   - `START_ISO` = current time minus the required window (e.g., `2023-11-12T10:15:00Z`).
   - `END_ISO` = current time (e.g., `2023-11-13T10:15:00Z`).
2. After receiving the response, **verify**:
   - `resourceType` is `Bundle`.
   - `total > 0` **and** `entry` array is non‑empty.
3. If no entries, `FINISH([-1])` (or the task‑specified sentinel) and stop.
4. Otherwise, locate the entry with the greatest `effectiveDateTime` (or `issued`).
5. Extract the numeric value:
   - Prefer `entry.resource.valueQuantity.value`.
   - If the value is in a different unit, read `valueQuantity.unit` and convert to the required unit.
6. Ensure the extracted value is a number; if parsing fails, treat as missing and use the sentinel.
7. **Finish** with the numeric value (or a tuple if a date is also required).

**Pattern 2: Fallback handling**
- If the primary `valueQuantity` field is absent, check for `valueString` that can be parsed as a number.
- If multiple observations exist, but none have `valueQuantity`, fall back to the most recent `valueString` after numeric parsing.
- If conversion fails, log the issue and return the sentinel.

**Pattern 3: Output formatting**
- Return a plain JSON array with the number (or `[number, "ISOdate"]` when a timestamp is required).
- Do **not** include units or explanatory text.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S0674240 within last 24 hours? Return `-1` if none."

**Step‑by‑step:**
1. Compute window:
   - `now = 2023-11-13T10:15:00Z`
   - `start = 2023-11-12T10:15:00Z`
2. Issue GET:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S0674240&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z
   ```
3. Inspect response:
   - If `total == 0` → `FINISH([-1])`.
   - Else locate newest entry, e.g.,
     ```json
     {"resource": {"effectiveDateTime":"2023-11-13T08:00:00Z","valueQuantity":{"value":2.2,"unit":"mg/dL"}}}
     ```
4. Extract `2.2` (already in mg/dL, no conversion needed).
5. `FINISH([2.2])`.

**Correct output:** `FINISH([2.2])`
**Incorrect output examples:**
- `FINISH(["2.2 mg/dL"])` (unit included)
- `FINISH([-1])` when a valid entry exists.

## Success Indicators
- The agent includes `date=ge…&date=le…` parameters in the Observation GET request.
- The agent checks `Bundle.total` / `entry` before calling `FINISH`.
- The final `FINISH` payload contains a plain number (or sentinel) and, when required, the ISO timestamp.

## Failure Indicators
- `FINISH` is called immediately after the GET without inspecting the bundle.
- The agent extracts `valueString` or concatenates the unit with the number.
- The agent returns a sentinel despite a valid recent observation being present.
- Missing or incorrect date filters cause older observations to be considered.
