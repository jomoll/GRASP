---
description: "Retrieve Encounter resources for a patient and filter by type, date\
  \ range, or identifier to answer admission, discharge, visit\u2011count and encounter\u2011\
  type queries."
name: fetch_encounters_by_patient
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 2
  failure_mode: no_resource_query_performed
  fixes: 5
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 003276cc7c1bc688813d5aca
  - 0063d54603cf0f791a4f2d03
  - 0221f690fdea162c568ad8dc
  - 0266d6e5d007484e57bf12d6
  - 04e24b204bd0cfa1f803ee70
  - 05bb819666668fc43bad2666
  - 05ffeff678368c17b77078d6
  - 072f960a91e48e6fe38d81a1
  - 073c3923948729f403a5e5a3
  - 07bde541ff2932869ecb4912
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must invoke this skill whenever the user asks about any aspect of a patient’s encounters, such as:
- admission type (ER, ICU, hospital, etc.)
- discharge date or time
- number of visits in a given period
- whether a visit of a particular kind occurred (e.g., ER visit this year, ICU stay, cardiac catheterization procedure linked to an encounter)
- the latest or first encounter matching a criterion
If the question mentions *Encounter*, *admission*, *discharge*, *hospital visit*, *ICU*, *ER*, *procedure on a stay*, or asks for a count of visits, trigger this skill.

## Procedure
1. **Retrieve all Encounter resources** for the patient using the tool:
   ```json
   {"resource_type": "Encounter", "patient_fhir_id": "<patient_fhir_id>"}
   ```
2. **Normalize identifiers**: for each Encounter, collect the `identifier[].system` strings lower‑cased.
3. **Determine the target encounter set** based on the query:
   - **Hospital encounter**: identifier.system contains `encounter-hosp` OR `class.code` is `IMP` (inpatient) OR `class.code` is `ACUTE` with a hospital‑type `type.coding.display` containing "hospital".
   - **ICU encounter**: identifier.system contains `encounter-icu` OR `class.code` equals `ICU`.
   - **ER encounter**: identifier.system contains `encounter-er` OR `class.code` equals `EMER` OR `type.coding.display` contains "emergency".
   - **Specific procedure linked to an encounter**: if the user mentions a procedure code/name, keep only encounters whose `type.coding` or `reasonCode` matches the procedure terms (e.g., "cardiac catheterization").
4. **Apply date filters** if the question includes a date range, month, or year:
   - Parse the start and/or end dates from the user text.
   - Compare against `period.start` and `period.end` (treat missing end as ongoing).
   - Keep encounters where the period overlaps the requested interval.
5. **Select the required encounter**:
   - *first* encounter → sort by `period.start` ascending and pick the first.
   - *last* encounter → sort by `period.start` descending and pick the first.
   - *count* → length of the filtered list.
6. **Extract the answer** based on the original intent:
   - **Admission type**: return `class.display` if present, otherwise the most specific `type.coding.display`.
   - **Discharge date/time**: return `period.end` (ISO‑8601). If `end` is missing, answer "still admitted".
   - **Visit count**: return the integer count.
   - **Existence check**: return a boolean (`true`/`false`).
   - **Specific encounter identifier**: return the Encounter `id`.
7. **Validate** the extracted value:
   - Ensure the resource type is Encounter.
   - Verify any required field (e.g., `period.end` for discharge) is present.
   - Confirm the value respects the requested time window and unit (ISO‑8601 timestamps for dates, plain integers for counts, short strings for types).
8. **Return the answer** in the exact format the user asked for (boolean, ISO datetime, integer, or short text).

## Checks
- Resource type must be **Encounter**.
- If a date range is supplied, the selected encounter’s `period.start`/`period.end` must intersect that range.
- For admission‑type answers, the value must be a non‑empty string from `class.display`, `type.coding.display`, or a fallback identifier.
- For discharge answers, `period.end` must be present and a valid ISO‑8601 datetime.
- For counts, ensure the result is an integer ≥ 0.
- For existence checks, return a boolean.

## Avoid
- Skipping the initial `get_resources_by_patient_fhir_id` call (the most common cause of *no_resource_query_performed* failures).
- Assuming a single Encounter when multiple may satisfy the criteria; always sort and select according to “first” or “last”.
- Mixing up `class.code` with `type.coding`; both can indicate encounter kind, so check both.
- Returning the whole Encounter JSON; only the requested field/value should be output.
- Forgetting to apply user‑specified date filters, which leads to answers outside the requested window.
