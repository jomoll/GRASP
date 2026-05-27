---
description: Filters Observation resources to those linked to the identified hospital/ICU
  encounter before value extraction.
name: filter_observations_by_encounter
provenance:
  baseline_fixes: 1
  baseline_regressions: 4
  epoch: 8
  failure_mode: false_positive_result
  fixes: 2
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - 02885cc1fb11efec74cb16fd
  - 0577ee51b3ad3c9fcf8fbbae
  - 09b1b086d491d385b6744dd6
  - 09c4726f77bd8073eeb8d985
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must invoke this skill whenever a question explicitly ties a measurement to a specific encounter, e.g., phrases like *"during this hospital visit", "last ICU visit", "first hospital encounter", "in the current admission", or any wording that scopes the request to a particular encounter.

## Procedure
1. **Detect Encounter Scope** – Scan the user query for keywords that indicate an encounter context (`hospital visit`, `ICU visit`, `first/last encounter`, `admission`, `encounter`).
2. **Query Encounters** – Use `get_resources_by_patient_fhir_id` with `resource_type="Encounter"` to retrieve all encounters for the patient.
3. **Identify Relevant Encounter(s)**
   - Prefer encounters whose `identifier.system` contains a case‑insensitive match for `encounter‑hosp` (hospital) or `encounter‑icu` (ICU).
   - If none match, fall back to `class.code` values (`IMP` for inpatient, `ACUTE` for emergency, etc.).
   - Resolve the *first*, *last*, or *nth* encounter as required by the query (by `period.start`).
   - Include any child encounters whose `partOf.reference` ends with the chosen encounter’s `id`.
4. **Retrieve Observations** – Call `get_resources_by_patient_fhir_id` for `Observation`.
5. **Filter by Encounter Reference**
   - For each Observation, examine `encounter.reference`. Keep the observation only if the referenced encounter ID is in the set from step 3.
   - If an Observation lacks an explicit `encounter` field, discard it for encounter‑scoped queries.
6. **Proceed with Existing Extraction** – Pass the filtered Observation list to the normal numeric aggregation or value‑extraction logic (e.g., `observation_value_extraction`, `numeric_aggregation`).
7. **Answer Formatting** – Return the result in the format expected by the downstream skill (plain number, datetime, etc.).

## Checks
- Verify that at least one Encounter matching the scope was found; if none, answer “No data” or a suitable null response.
- Ensure every retained Observation has a valid `effectiveDateTime`/`effectivePeriod.start` within the encounter’s period (optional extra safety).
- Confirm that the filtered list is not empty before performing aggregation; otherwise return `None`.
- Preserve unit handling and numeric conversion as defined in the downstream numeric aggregation skill.

## Avoid
- Do **not** assume all observations within the same calendar window belong to the encounter; always require an explicit `encounter` reference.
- Do not filter out observations that belong to child encounters; include them by checking `partOf` links.
- Avoid applying this filter to queries that do **not** mention an encounter context, as it would incorrectly exclude valid data.
