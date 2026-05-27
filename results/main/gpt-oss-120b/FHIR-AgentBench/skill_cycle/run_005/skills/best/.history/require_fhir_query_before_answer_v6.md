---
description: Strictly enforce that every needed FHIR resource is queried before any
  answer is derived.
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 2
  baseline_regressions: 2
  epoch: 9
  failure_mode: missing_fhir_query_before_answer
  fixes: 5
  parent_version: 5
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 02784e491e61842ddb4de275
  - 059ed55281d42669ad25d514
  - 0d012e621517a4059d3caf10
  update_cycle: 1
tags: []
version: 6
---

## When to use
You must invoke this skill whenever a user question references patient data that depends on one or more FHIR resource types (e.g., MedicationRequest, Observation, Procedure, Encounter, Condition, MedicationAdministration, etc.) and no prior `get_resources_*` call for the required type appears in the action log.

## Procedure
1. **Detect required resource types**
   - Scan the natural‑language question for keywords and map them to FHIR resources:
     - medication‑related words (`prescribed`, `drug`, `dose`, `iv`, `po`, `route`, `order`) → `MedicationRequest` (and possibly `MedicationAdministration`/`Medication`).
     - lab / test / microbiology words (`lab`, `test`, `culture`, `mrsa`, `creatinine`, `blood pressure`, `weight`) → `Observation` (or `Procedure` for procedural tests).
     - procedure / surgery words (`procedure`, `surgery`, `repair`, `catheterization`) → `Procedure`.
     - encounter / admission words (`hospital stay`, `encounter`, `visit`, `admission`, `ICU`) → `Encounter`.
     - diagnosis / condition words (`diagnosis`, `condition`, `disease`) → `Condition`.
2. **Check the action log**
   - Look at `retrieved_resources` (the result of previous tool calls) to see whether each identified resource type already has an entry.
3. **Insert missing queries**
   - For every resource type that is absent, issue a `get_resources_by_patient_fhir_id` call with the correct `resource_type` and the patient FHIR ID supplied in the context.
   - If the question mentions a specific resource ID, prefer `get_resources_by_resource_id`.
4. **Proceed only after queries**
   - After all required queries have been performed, allow subsequent `execute_python_code` or answer generation steps.
5. **Fallback handling**
   - If a required resource type cannot be queried (e.g., API error), abort the current answer path and invoke the `answer_fallback` skill.

## Checks
- Confirm that **at least one** query exists for each required resource type before any Python execution or final answer.
- Verify that the query uses the patient’s FHIR ID (`patient_fhir_id`) and the exact `resource_type` string.
- Ensure the query is placed **before** any `execute_python_code` or answer output in the trace.
- If any required query is missing, raise an internal flag and trigger the missing‑query insertion step.

## Avoid
- Answering based on assumptions or hard‑coded defaults when the needed data has not been fetched.
- Performing the query check **after** the answer has already been produced.
- Re‑querying a resource type that is already present in `retrieved_resources` (duplicate calls waste time).
- Ignoring the patient‑specific context; always use the supplied patient FHIR ID.
