---
description: Select the earliest hospital encounter (and its child encounters) for
  a patient.
name: first_hospital_encounter_selection
provenance:
  baseline_fixes: 1
  baseline_regressions: 3
  epoch: 12
  failure_mode: false_positive_result
  fixes: 2
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - 02885cc1fb11efec74cb16fd
  - 0577ee51b3ad3c9fcf8fbbae
  - 09b1b086d491d385b6744dd6
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must invoke this skill whenever the user query refers to the **first** (i.e., earliest) hospital visit/encounter of a patient – e.g., *"first hospital visit", "initial admission", "first stay", "first hospital encounter"* – and the answer depends on observations or other resources linked to that encounter.

## Procedure
1. **Query Encounters** – Use `get_resources_by_patient_fhir_id` with `resource_type="Encounter"`.
2. **Identify hospital encounters**
   - Keep an encounter if **any** of the following is true:
     - Its `identifier[].system` (case‑insensitive) contains the substring `encounter-hosp`.
     - Its `class.code` (case‑insensitive) equals `IMP` (the MIMIC inpatient code).
3. **Choose the earliest encounter**
   - For each candidate, read `period.start`.  If missing or unparsable, treat the start as `datetime.max` so it is ignored.
   - Select the encounter with the **minimum** `period.start` value.
4. **Collect child encounter IDs**
   - Initialise a set `enc_ids` with the selected encounter’s `id`.
   - Iterate over **all** retrieved encounters; if an encounter’s `partOf.reference` ends with the selected encounter’s `id`, add its `id` to `enc_ids`.
5. **Return** the set `enc_ids` (or a list) for downstream filtering of Observations, Conditions, MedicationRequests, etc.

## Checks
- Verify that at least one hospital encounter was found; if none, answer `None` or raise a clear “no hospital encounter” flag.
- Ensure each `period.start` is a valid ISO‑8601 datetime; ignore malformed values.
- Confirm that child‑encounter detection uses the exact ID after the last `/` in the `partOf.reference` string.
- The returned IDs must be plain strings, no surrounding JSON objects.

## Avoid
- Do **not** pick the most recent encounter (i.e., do not use `max` on `period.start`).
- Do not rely on `type` or `serviceType` fields; the definition above is the canonical way in the dataset.
- Do not drop child encounters – many observations are linked to sub‑encounters.
- Do not return the entire Encounter resource; only the IDs are needed for filtering.
