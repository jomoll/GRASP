---
description: Expand to detect needed resource types from the question and issue the
  appropriate get_resources_by_patient_fhir_id calls.
name: resource_query_planner
provenance:
  baseline_fixes: 5
  baseline_regressions: 3
  epoch: 5
  failure_mode: missing_resource_query
  fixes: 5
  parent_version: 2
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - 0406ba9fa1c3ada7f76965a3
  - 044289b85d5894aef9a9825d
  - 047259e83745142834b50838
  - 061afbb7908a8ff0d6a68a50
  - 0741b96a36302acf8ace5c02
  - 098b1301820b7d581a339d0f
  - 09b1b086d491d385b6744dd6
  - 0a403bb61217529f94970734
  - 0cd11d35e8ac3515e3c55d6c
  update_cycle: 0
tags: []
version: 3
---

## When to use
Trigger this skill whenever the user asks for any information that depends on FHIR resources other than the ones already in the agent’s context. Typical patterns include:
- Mentions of a specific resource type (e.g., *medication*, *medication request*, *medication administration*, *observation*, *condition*, *procedure*, *encounter*).
- Phrases that imply a resource lookup such as *last prescribed*, *first measured*, *since*, *during the last hospital visit*, *on the last encounter*, *total output*, *count of ICU visits*, *had a lab test*, etc.
- Requests that require filtering by encounter scope (hospital, ICU, emergency) or by date range.
If the question contains any of these cues and the required resource has not yet been retrieved, invoke this skill.

## Procedure
1. **Parse the instruction** to identify the target FHIR resource:
   - Look for keywords: `medication`, `medication request`, `medication administration`, `prescribed`, `ordered` → **MedicationRequest** or **MedicationAdministration**.
   - `observation`, `lab`, `test`, `value`, `measurement`, `output`, `sodium`, `creatinine`, `blood pressure`, `weight`, `respiratory rate`, `hematocrit`, `calcium`, `output` → **Observation**.
   - `diagnosis`, `condition`, `disease` → **Condition**.
   - `procedure`, `operation`, `surgery`, `laparoscopic` → **Procedure**.
   - `encounter`, `visit`, `admission`, `discharge`, `hospital stay`, `icu stay`, `emergency room` → **Encounter**.
2. **Determine any additional filters** required for the query:
   - Date constraints (e.g., "since 08/2142", "in 07/this year", "last 12 months").
   - Encounter scope (hospital, ICU, emergency) – use identifier system strings like `encounter-hosp`, `encounter-icu`, `encounter-ed` or fallback to `class.code` values (`IMP`, `EMER`, `ACUTE`).
   - Route or route‑specific terms for medications (`iv`, `im`, `sc`, `po`, `ih`).
3. **Issue the retrieval call** before any downstream processing:
   ```json
   {
     "tool": "get_resources_by_patient_fhir_id",
     "arguments": {
       "resource_type": "<DetectedResource>",
       "patient_fhir_id": "<patient_fhir_id>"
     }
   }
   ```
   Do this **once per resource type** per question. Cache the result in `retrieved_resources` for later skills.
4. **If the question also requires linking** (e.g., a MedicationRequest that references a Medication resource), schedule a second retrieval for the referenced resource after the first call returns.
5. **Proceed to the next skill** (numeric aggregation, observation extraction, etc.) now that the necessary data is available.

## Checks
- Verify that the detected resource type matches at least one of the supported FHIR types (Encounter, Observation, Condition, MedicationRequest, MedicationAdministration, Procedure, Medication).
- Ensure the patient FHIR ID is known; if not, abort with a clear error.
- After the `get_resources_by_patient_fhir_id` call, confirm that `retrieved_resources[<Resource>]` is a list (could be empty). If empty and the question expects a value, prepare to return a "None" or appropriate "No records found" answer downstream.
- When a secondary resource (e.g., Medication) is required, confirm that the reference string matches the pattern `Resource/<id>` before issuing the second query.

## Avoid
- Assuming the required resource is already present; always perform the lookup if the pattern is detected.
- Over‑fetching unrelated resources – only request the exact type identified.
- Ignoring date or encounter scope filters; they must be applied later but the initial query should retrieve the full set for the patient.
- Duplicating queries for the same resource within a single request – cache results after the first call.
