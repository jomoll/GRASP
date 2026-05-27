---
description: "Broaden trigger to capture any encounter\u2011related query (first/last,\
  \ hospital/ICU/ER, admission type, discharge date, visit count, etc.)"
name: fetch_encounters_by_patient
provenance:
  baseline_fixes: 5
  baseline_regressions: 7
  epoch: 4
  failure_mode: no_resource_query_performed
  fixes: 6
  parent_version: 1
  probe_score: 4
  regressions: 4
  triggering_sample_ids:
  - 000f58d3abb4ad76b2ebc35c
  - 00beff4406c2ee10ac9621fe
  - 01bb1845215fb7cc77678534
  - 0406ba9fa1c3ada7f76965a3
  - 0664f9448edc539d0cb228a4
  - 0874a8eb9ae4f8b6bb50a1d4
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 1
tags: []
version: 2
---

## When to use
You must invoke this skill whenever the user asks about any aspect of a patient’s encounters, including:
- References to *first*, *last*, *most recent*, *earliest*, *previous*, or *any* visit
- Specific settings such as **hospital**, **ICU**, **ER**, **emergency**, **intensive‑care**, **inpatient**, **outpatient**, or custom encounter identifiers
- Temporal constraints like *since*, *in the last X days*, *this year*, *month*, *date range*, or *on <date>*
- Questions about admission type, discharge date, length of stay, number of visits, or whether the patient ever had a certain type of encounter.

## Procedure
1. **Retrieve all Encounter resources** for the patient via `get_resources_by_patient_fhir_id` with `resource_type="Encounter"`.
2. **Identify encounter scope** based on keywords:
   - If the query mentions *hospital* or identifiers containing `encounter‑hosp`, filter encounters whose identifier system includes that string, whose `class.code` is one of `IMP, INPATIENT, INPATIENTACUTE, INPATIENTOBSERVATION`, or whose `type.coding.display` contains "hospital".
   - If the query mentions *ICU* or identifiers containing `encounter‑icu`, filter by identifier system, `class.code` equal to `ICU` (or `ACUTE` with a type display containing "ICU"), or type display containing "ICU".
   - If the query mentions *ER* or identifiers containing `encounter‑er`, filter by identifier system, `class.code` in `EMER, EMERGENCY, EMERGENT`, or type display containing "emergency".
   - If no specific scope is detected, keep all encounters.
3. **Apply temporal filters** when the instruction includes dates or relative periods:
   - Parse explicit dates (`YYYY‑MM‑DD`) or month/year patterns.
   - For relative expressions like *since 1 year ago* or *in the last X days*, compute the cutoff from the assumed current time.
   - Keep only encounters whose `period.start` (or `period.end` when relevant) falls within the computed window.
4. **Select the required encounter** based on ordering keywords:
   - *first* → sort by `period.start` ascending and pick the first.
   - *last* / *most recent* → sort by `period.start` descending and pick the first.
   - *any* → any matching encounter (return the list).
5. **Include child encounters**: collect IDs of encounters whose `partOf.reference` ends with the chosen encounter’s ID and add them to the result set.
6. **Return** a dictionary containing:
   ```json
   {
     "encounters": [<full Encounter resources>],
     "ids": [<encounter IDs including children>]
   }
   ```
   This structure can be consumed by downstream skills (e.g., `auto_fetch_linked_resources`).

## Checks
- Verify that at least one Encounter matches the scope; if none, answer with a clear statement (e.g., "No hospital encounters found").
- Confirm that date parsing succeeded; on failure, fall back to no date filter but log the issue.
- Ensure the selected encounter IDs are unique.
- When ordering is required, make sure the sort key exists; if missing, treat the encounter as having the earliest possible date.

## Avoid
- Selecting an encounter of the wrong type (e.g., treating an ICU encounter as a hospital encounter).
- Ignoring child encounters that belong to the selected parent encounter.
- Misinterpreting relative time expressions (e.g., treating "since 1 year ago" as a future date).
- Returning an empty list without informing the user why the query could not be satisfied.
