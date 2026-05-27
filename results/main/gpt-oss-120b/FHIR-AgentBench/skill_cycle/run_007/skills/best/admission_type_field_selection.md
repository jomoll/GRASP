---
description: Select the correct admission type from Encounter.hospitalization.admitSource
  instead of class or type fields.
name: admission_type_field_selection
provenance:
  baseline_fixes: 4
  baseline_regressions: 1
  epoch: 4
  failure_mode: admission_type_wrong_field_extracted
  fixes: 6
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 0221f690fdea162c568ad8dc
  - 0d3343e3e64231d00abab91e
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a question asks for the **admission type**, **admission source**, or **how the patient entered the hospital** (e.g., "What was the admission type when patient X first entered the hospital?", "How was patient X admitted?", "Admission source for the first hospital encounter?").

## Procedure
1. **Query Encounters** – Use `get_resources_by_patient_fhir_id` with `resource_type="Encounter"` for the target patient.
2. **Identify hospital encounters** – Keep encounters that:
   - Have an identifier whose `system` contains `encounter-hosp` (case‑insensitive), **or**
   - Have `class.code` equal to `IMP` (inpatient) as a fallback.
3. **Sort encounters** – Order the filtered encounters by `period.start` (earliest first).
4. **Select the first encounter** – This is the “first hospital visit”.
5. **Extract admission type** from the selected encounter:
   - Look for `hospitalization.admitSource`.
   - If present, prefer the first coding's `display`; if `display` is missing, use `code`.
   - If `admitSource.text` exists and no coding, use that text.
   - **Do not** fall back to `class.code` or `type` coding – those are wrong fields for admission type.
6. **Return the extracted string** (or `None` if the field is absent).

## Checks
- Verify that at least one hospital encounter was found; otherwise answer "No hospital encounter found".
- Confirm that `hospitalization.admitSource` exists on the selected encounter; if missing, answer "Admission type not recorded".
- Ensure the final answer is a non‑empty string (or a clear "None"/error message as above).
- The answer must be plain text, not a code or object, matching the wording used in the FHIR `display` field when available.

## Avoid
- Do not use `Encounter.class.code` (e.g., `IMP`, `EMER`) as the admission type.
- Do not use `Encounter.type` codings; they describe encounter purpose, not admission source.
- Do not return the entire Encounter resource or any identifier values.
- Do not assume the admission type is always present; handle missing data gracefully as described.
