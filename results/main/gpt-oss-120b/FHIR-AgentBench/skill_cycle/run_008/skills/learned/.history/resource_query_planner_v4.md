---
description: "Refined detection and safe issuing of FHIR resource queries. The skill\
  \ now limits the number of resource types it will request, adds stricter trigger\
  \ conditions, and includes guard clauses to avoid malformed tool calls that caused\
  \ regression in date\u2011heavy or ambiguous queries."
name: resource_query_planner
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 6
  failure_mode: missing_resource_query
  fixes: 3
  parent_version: 3
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 00fbe516569113decea8de73
  - 047259e83745142834b50838
  - 090c2ad4771d1fc8adaea4ae
  - 0af1a06bcce4aacbc5a936f4
  update_cycle: 0
tags: []
version: 4
---

## When to use
Trigger this skill **only** when:
1. The user question references clinical data (labs, vitals, diagnoses, procedures, medications, encounters, etc.) **and**
2. No `get_resources_by_patient_fhir_id` calls have been made earlier in the turn.
   - If any prior calls exist, assume the needed resources are already being fetched by another skill.
3. A patient identifier can be extracted from the conversation context (e.g., `Patient FHIR ID is <id>`). If the ID is missing, abort with an informative error.

Typical cues remain the same (lab, weight, blood pressure, medication, encounter, diagnosis, surgery, …) but the skill now applies a **strict keyword‑to‑resource map** to avoid over‑fetching.

## Procedure
1. **Extract patient identifier** – read the patient FHIR ID from context. If it is not a non‑empty string, raise an error and stop.
2. **Detect required resource types** – scan the question text (lower‑cased) and match against the refined map:
   - `Observation` → keywords: `lab`, `test`, `blood pressure`, `heart rate`, `weight`, `temperature`, `pulse`, `glucose`, `cholesterol`, `measurement`, `vital`.
   - `MedicationRequest` → keywords: `prescribed`, `ordered`, `drug`, `medication`, `iv`, `po`, `im`, `sc`, `subcutaneous`, `intravenous`, `oral`, `dose`, `tablet`, `capsule`.
   - `MedicationAdministration` → keywords: `administered`, `given`, `infusion`, `injection` (but only if the question explicitly mentions an administration event).
   - `Encounter` → keywords: `hospital visit`, `admission`, `discharge`, `er`, `emergency`, `encounter`, `stay`, `first`, `last`.
   - `Condition` → keywords: `diagnosis`, `disease`, `condition`.
   - `Procedure` → keywords: `procedure`, `surgery`, `repair`, `operation`, `graft`, `prosthesis`.
   - `Specimen` / `Location` → only if the question explicitly contains the words `specimen` or `location`.
3. **Create a unique set** of detected types.
4. **Guard against over‑querying** – if the set contains more than **three** distinct resource types, reduce it to the safest baseline: `{Encounter, Observation, MedicationRequest}` (or the first three alphabetically). This prevents extremely large or ambiguous calls that previously produced malformed JSON.
5. **Issue queries** – for each type in the (potentially reduced) set, invoke the tool exactly once:
   ```json
   {
     "resource_type": "<TYPE>",
     "patient_fhir_id": "<PATIENT_ID>"
   }
   ```
   The calls are emitted **one at a time**; each call is a separate tool action so the JSON payload never exceeds a single object.
6. **Record results** – the tool populates `retrieved_resources` with keys matching each requested type.
7. **Proceed** – downstream skills can now safely operate on the fetched data.

## Checks
- Verify the patient FHIR ID is present and non‑empty before any call.
- Ensure the final set of resource types is not empty; if keyword detection yields none, default to `{Encounter, Observation}`.
- After each tool call, confirm `retrieved_resources[TYPE]` exists (it may be an empty list – that is acceptable).
- Log the selected resource types in a comment for debugging.

## Avoid
- Requesting more than three resource types in a single turn (to keep tool payloads small and well‑formed).
- Performing any filtering (dates, values, routes) inside this skill – leave that to later aggregation or extraction skills.
- Triggering when prior `get_resources_by_patient_fhir_id` calls have already been made.
- Assuming a single resource type; the reduced‑set logic still respects multiple needed types while staying safe.

## Tags
[]
