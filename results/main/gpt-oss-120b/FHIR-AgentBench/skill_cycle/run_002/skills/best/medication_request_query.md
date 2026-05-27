---
description: Add medicationReference resolution to retrieve drug names from Medication
  resources.
name: medication_request_query
provenance:
  baseline_fixes: 5
  baseline_regressions: 1
  epoch: 1
  failure_mode: medication_reference_not_resolved
  fixes: 7
  parent_version: 2
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - 00beff4406c2ee10ac9621fe
  - 0266d6e5d007484e57bf12d6
  - 0406ba9fa1c3ada7f76965a3
  update_cycle: 1
tags: []
version: 3
---

## When to use
You should invoke this skill whenever a user asks about a medication prescribed or administered and the query may involve **MedicationRequest** or **MedicationAdministration** resources that reference a **Medication** via `medicationReference`. Typical patterns include:
- "Did patient X receive clonidine?"
- "What was the first drug given via IV in October?"
- "List all medications prescribed during the first hospital encounter."
If the request mentions drug names, routes, dates, or encounter scopes **and** the medication may be stored as a reference, this skill must resolve that reference.

## Procedure
1. **Fetch Encounter(s)** (if the query limits by encounter):
   - Retrieve all **Encounter** resources for the patient.
   - Identify the relevant encounter(s) (first, last, by type, etc.) using identifiers (`encounter‑hosp`, `encounter‑icu`) or `class.code`.
2. **Retrieve MedicationRequest and MedicationAdministration** for the patient.
3. **Collect medicationReference IDs**:
   - For each **MedicationRequest** and **MedicationAdministration**, inspect `medicationReference.reference`.
   - Extract the resource id (the part after `Medication/`).
   - Store all unique ids in a set `med_ref_ids`.
4. **Bulk‑fetch Medication resources** for the ids collected in step 3 using `get_resources_by_resource_id` (batch calls are allowed).
5. **Build a lookup table** `med_id_to_name`:
   - For each fetched **Medication**:
     - Prefer `code.coding.display`.
     - If missing, fall back to `code.coding.code`.
     - If still missing, check `identifier` entries where `system` is a known medication‑name system (e.g., `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name`).
     - Store the first non‑null normalized name (lower‑cased, whitespace‑collapsed).
6. **Resolve medication names** for every request/administration:
   - If the resource contains `medicationCodeableConcept`, extract the name using the same priority as step 5.
   - Else, look up the name in `med_id_to_name` using the reference id.
7. **Apply query filters** (date range, route, dosage, encounter id, etc.) on the resolved medication entries.
8. **Select the answer** according to the user question (e.g., existence → Yes/No, earliest → name, latest → name, list → comma‑separated).  Format the answer exactly as requested (bool, string, list, numeric).

## Checks
- Verify that every `MedicationRequest`/`MedicationAdministration` used in the answer has a resolved drug name (non‑null).
- Confirm that any date, route, or encounter filter matches the retrieved resources.
- Ensure units or dosage forms are not required unless explicitly asked; otherwise ignore them.
- Validate the final answer type matches the question (Yes/No, drug name, list, numeric value).
- If no medicationReference ids could be fetched, fall back to the names already present in `medicationCodeableConcept` and answer accordingly.

## Avoid
- Assuming the drug name is always present in `medicationCodeableConcept` – many records store only a reference.
- Returning raw reference strings like `Medication/abcd‑1234`.
- Ignoring route or date filters after name resolution.
- Mixing medications from unrelated encounters; always respect the encounter scope identified in step 1.
- Leaving unresolved ids in the final answer; if a name cannot be found, treat the entry as non‑matching rather than guessing.
