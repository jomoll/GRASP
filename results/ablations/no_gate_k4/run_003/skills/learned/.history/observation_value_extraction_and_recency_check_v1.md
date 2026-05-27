---
description: Extract the latest Observation value and date, then decide if a new order
  is needed based on age.
name: observation_value_extraction_and_recency_check
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task4_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Observation Value Extraction and Recency Check

## Pattern Description
You must reliably pull the quantitative result and the timestamp from a FHIR Observation bundle. The core capability is to locate the most recent entry, read the numeric value (or string that can be parsed), and read the `effectiveDateTime` (or `issued` when `effectiveDateTime` is absent). After extraction you compare the result date to the current execution time to decide whether the result is stale (e.g., older than 1 year) and whether a follow‑up ServiceRequest should be created.

## When to Use This Skill
- When a task asks for "the last *X* value in the chart" and provides a code (e.g., `code=A1C`).
- When the task also includes a conditional ordering clause such as "if the result is older than N days/years, order a new test".
- When the GET request returns a `Bundle` of `Observation` resources (may be empty, may contain multiple entries).

## Common Failure Patterns
- Returning a placeholder like `-1` instead of the actual value and date.
- Extracting the unit together with the numeric value (e.g., `"5.6 %"` instead of `5.6`).
- Looking at the wrong timestamp field (`issued` vs `effectiveDateTime`).
- Ignoring the case where the bundle has `total: 0` and treating it as a valid result.
- Selecting the first entry rather than the most recent (`effectiveDateTime` descending).

## Recommended Patterns
**Pattern 1: Locate the latest Observation and extract value & date**
1. Verify the response is a `Bundle` with `type = "searchset"`.
2. If `total == 0` → treat as *no recent result*.
3. Otherwise, sort `entry.resource` by `effectiveDateTime` (or `issued` if missing) descending.
4. From the first resource:
   - If `valueQuantity` exists, take `valueQuantity.value` as a number and ignore `valueQuantity.unit`.
   - Else if `valueString` exists, attempt to parse a numeric prefix.
   - Else if `component` array contains a numeric entry, use that.
5. Capture `effectiveDateTime` (or `issued`).

**Pattern 2: Determine recency**
1. Parse the extracted timestamp as an ISO‑8601 datetime.
2. Compute the difference between the current execution time (provided in the task context) and the observation date.
3. If the difference > the allowed age (e.g., 365 days), set a flag `stale = true`.

**Pattern 3: Conditional ServiceRequest creation**
1. If `stale == true` **or** no observation was found, build a `ServiceRequest` with the ordering LOINC code supplied in the task.
2. Populate required fields:
   - `resourceType: "ServiceRequest"`
   - `code.coding[0].system = "http://loinc.org"`
   - `code.coding[0].code = <ordering_loinc>`
   - `authoredOn` = current execution time
   - `status = "active"`, `intent = "order"`, `priority = "stat"`
   - `subject.reference = "Patient/<mrn>"`
   - Optional `note.text` explaining why the order was placed.
3. If `stale == false`, **do not** create a ServiceRequest; simply return the extracted value and date.

## Example Application
**Task:** "What’s the last HbA1C (hemoglobin A1C) value in the chart for patient S6550627 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

**Step‑by‑step:**
1. GET `http://localhost:8080/fhir/Observation?code=A1C&patient=S6550627`.
2. Response bundle contains three entries; sort by `effectiveDateTime` → newest is `2022-09-10T08:30:00Z` with `valueQuantity.value = 7.2`.
3. Compute age: current time `2023-11-13T10:15:00Z` → 1 year + 34 days → `stale = true`.
4. Because `stale`, POST a ServiceRequest using LOINC `4548-4` (HbA1c order) with `authoredOn = 2023-11-13T10:15:00Z`.
5. FINISH with:
   ```
   FINISH(["HbA1c = 7.2% recorded on 2022-09-10T08:30:00Z. New test ordered."])
   ```

If the newest observation had been dated `2023-06-01`, the FINISH output would be:
```
FINISH(["HbA1c = 7.2% recorded on 2023-06-01T08:30:00Z. No new test needed."])
```

## Success Indicators
- The FINISH payload contains a numeric value (no units) and an ISO‑8601 date.
- When the observation is older than the allowed threshold, a ServiceRequest POST is performed before FINISH.
- When no observation exists, the agent either orders a new test (if the task demands) or returns a clear "no result" message without posting.

## Failure Indicators
- FINISH returns `-1` or any non‑numeric placeholder.
- The posted ServiceRequest is created even though a recent observation exists.
- The extracted value includes the unit string (e.g., `"7.2 %"`).
- The agent uses the first bundle entry without sorting by date.
- The timestamp field is missing or incorrectly parsed, leading to wrong age calculation.

---
*Tags:* ["observation","extraction","recency","conditional_order"]
