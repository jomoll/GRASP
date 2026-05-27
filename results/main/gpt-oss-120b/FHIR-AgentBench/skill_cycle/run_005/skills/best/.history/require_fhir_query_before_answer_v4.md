---
description: Force a FHIR query for every resource type inferred from the question
  before any answer is generated.
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 4
  baseline_regressions: 3
  epoch: 4
  failure_mode: missing_fhir_query_before_answer
  fixes: 5
  parent_version: 3
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 003276cc7c1bc688813d5aca
  - 01c441f58a97f89226067a93
  - 0221f690fdea162c568ad8dc
  - 04572e0972a7993db0621881
  - 073c3923948729f403a5e5a3
  - 0741b96a36302acf8ace5c02
  - 0c6cdc444ee911941bfd23f0
  - 0d3343e3e64231d00abab91e
  update_cycle: 0
tags: []
version: 4
---

## When to use
Trigger this skill whenever the user asks for a value that must come from a specific FHIR resource (e.g., Observation, Encounter, Condition, MedicationRequest, MedicationAdministration, Procedure, etc.) and the agent has not yet performed a `get_resources_by_patient_fhir_id` or `get_resources_by_resource_id` call for that resource type.

## Procedure
1. **Infer needed resource types** from the natural‑language question (look for keywords such as "weight", "blood pressure", "admission type", "medication", "procedure", "culture", "organism", "dose", "route", etc.).
2. **Inspect the current tool‑call history** (the `retrieved_fhir_resources` dictionary) to see which resource types have already been fetched.
3. For every inferred resource type that is missing or has an empty list in `retrieved_fhir_resources`:
   - Issue a `get_resources_by_patient_fhir_id` call with the missing `resource_type` and the known patient FHIR ID.
   - If the patient ID is not yet known, first fetch the `Patient` resource using the identifier supplied in the question.
4. **Wait for the query result** before proceeding to any data extraction or calculation steps.
5. After all required queries have returned, continue with the normal reasoning pipeline (filtering, computation, formatting).

## Checks
- Verify that each inferred resource type appears as a key in `retrieved_fhir_resources` **and** that the associated list is non‑empty.
- Ensure the query was performed **before** any Python code execution that accesses those resources.
- Confirm that the patient FHIR ID used in the query matches the ID mentioned in the question (or was resolved from a prior Patient lookup).
- If any required resource remains unavailable after the query, answer with "Unable to determine …" rather than fabricating data.

## Avoid
- Skipping the query step because you assume the data is already in memory.
- Answering with default or placeholder values when the needed resources have not been fetched.
- Performing the query after you have already attempted to compute an answer.
- Mixing up resource types (e.g., using MedicationRequest data when the question asked for a Observation).
