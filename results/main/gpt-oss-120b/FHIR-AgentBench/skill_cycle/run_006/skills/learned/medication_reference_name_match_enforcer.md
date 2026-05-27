---
description: "Resolve medication references and codeable concepts before any name\u2011\
  based matching in medication queries."
name: medication_reference_name_match_enforcer
provenance:
  baseline_fixes: 2
  baseline_regressions: 1
  epoch: 15
  failure_mode: answer_time_rounded_to_hour_unexpected
  fixes: 5
  parent_version: 1
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - 017d9aef746962d1c3d9d52e
  - 024e5c4760ca03ad0215c516
  - 07f02f8bb9cf48ec09ba120e
  - 08777eb92c5be85c5613f0dd
  - 0a5e5b2f22a73ebf9ddd7a3a
  - 0a7229f1e72f42ee2dc14404
  update_cycle: 1
tags: []
version: 2
---

## When to use
Activate this skill whenever a question involves medication identification, filtering, or ordering (e.g., "was X prescribed", "first medication via IM route", "medication name contains …"). It runs before any string‑matching on medication names.

## Procedure
1. **Fetch Medication resources**
   - If not already present, call `get_resources_by_resource_id` for every `Medication` referenced by `medicationReference` in the retrieved `MedicationRequest`/`MedicationAdministration` bundles.
2. **Build a lookup table** mapping Medication IDs to a *canonical name*:
   - Prefer an identifier whose `system` contains the phrase `medication-name` (case‑insensitive); use its `value`.
   - Fallback to the first `coding.display` in `Medication.code.coding`.
   - If no display, use the first `coding.code`.
   - If still missing, use `Medication.code.text`.
3. **Resolve references** for each medication‑related resource:
   - If the resource has `medicationReference`, replace it with the canonical name from the lookup.
   - If it has `medicationCodeableConcept`, extract the first `coding.display` (or `code`, then `text`) as the name.
4. **Proceed with query logic** using these resolved names instead of raw IDs or codeable concepts.
5. When matching by substring, perform the match on the resolved canonical name after normalising whitespace and case.

## Checks
- Ensure every `medicationReference` points to an existing `Medication` resource; if a reference cannot be resolved, treat the medication as unknown and exclude it from name‑based filters.
- Verify that the final name string is non‑empty before applying substring or exact‑match logic.
- Confirm that the resource type is `MedicationRequest` or `MedicationAdministration` before applying the resolver.

## Avoid
- Performing name matching on the raw `Medication` ID (e.g., "6715bfc1…") which leads to false negatives.
- Ignoring `medicationCodeableConcept` when `medicationReference` is absent.
- Over‑matching by checking only one coding entry; always consider all codings and the `text` field.
- Leaving unresolved references that could cause downstream filters to miss valid medications.
