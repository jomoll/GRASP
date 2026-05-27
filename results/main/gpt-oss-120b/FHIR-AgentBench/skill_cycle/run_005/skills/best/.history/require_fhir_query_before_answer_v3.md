---
description: Enforce that a FHIR query for every inferred resource type is performed
  before answering.
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 1
  baseline_regressions: 6
  epoch: 2
  failure_mode: missing_fhir_query_before_answer
  fixes: 1
  parent_version: 2
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - 003276cc7c1bc688813d5aca
  - 0063d54603cf0f791a4f2d03
  - 00beff4406c2ee10ac9621fe
  - 0114a64085ec7d751f6e1bfd
  - 0266d6e5d007484e57bf12d6
  - 02759807d268a649ffbc56e0
  - 031f4556ea1fe707a94f58bb
  - 04572e0972a7993db0621881
  - 05a9aa5bb494b962444ac354
  - 072f960a91e48e6fe38d81a1
  update_cycle: 1
tags: []
version: 3
---

## When to use
You must apply this skill whenever the user asks a question that requires data from the FHIR store (e.g., observations, medication requests, procedures, encounters, conditions, etc.). If the question implies any specific FHIR resource type, you must verify that a query for that resource type has been executed before you generate a final answer.

## Procedure
1. **Infer required resource types** from the natural‑language question. Look for keywords that map to FHIR resource types:
   - "observation", "measurement", vital signs, lab, test → `Observation`
   - "medication", "prescribed", "drug", "dose", "order" → `MedicationRequest` (or `MedicationAdministration` when administration is asked)
   - "procedure", "operation", "screen", "test" (when referring to a performed clinical action) → `Procedure` or `Observation` for microbiology
   - "encounter", "visit", "hospitalisation", "admission", "discharge", "icu" → `Encounter`
   - "condition", "diagnosis", "problem" → `Condition`
2. **Check the agent’s tool‑call log** for any `get_resources_by_patient_fhir_id` or `get_resources_by_resource_id` calls whose `resource_type` matches each inferred type.
3. If **any required type is missing**, abort the answer generation and raise an error message such as:
   > "I need to retrieve {MissingResource} data before I can answer this question."
   This forces the agent to issue the appropriate FHIR query first.
4. If all required queries are present, allow the normal answer generation to continue.

## Checks
- Verify that the list of inferred resource types is not empty.
- Confirm that for each inferred type there is at least one tool call with `resource_type` equal to that type.
- Ensure the check runs **before** any answer formatting or reasoning steps.

## Avoid
- Assuming a single generic query covers all needed data; each distinct resource type must be queried.
- Passing the check when the only query was for an unrelated resource (e.g., querying `Patient` when `Observation` is needed).
- Ignoring case or spelling variations in the resource type name in the tool‑call log.
