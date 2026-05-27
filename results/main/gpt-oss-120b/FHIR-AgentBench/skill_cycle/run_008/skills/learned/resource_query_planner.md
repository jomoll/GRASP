---
description: Detects when a question needs a FHIR resource query and issues the correct
  safe get_resources_by_patient_fhir_id call.
name: resource_query_planner
provenance:
  baseline_fixes: 5
  baseline_regressions: 2
  epoch: 8
  failure_mode: missing_resource_query
  fixes: 5
  parent_version: 4
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 01c02f4b897bb8192e16bd1d
  - 02a069698a803a8419fa294c
  - 059ed55281d42669ad25d514
  - 0a8c46b684e72300d29c18aa
  update_cycle: 0
tags: []
version: 5
---

## When to use
You must invoke this skill whenever the user asks for any clinical information that lives in a FHIR resource (e.g., medication, prescription, lab test, microbiology, vital sign, observation, condition, procedure, encounter) and the question contains:
- medication‑related keywords: *prescribed, medication, drug, dose, route, iv drip, po, ng, im, patch, tablet, infusion*;
- lab/observation keywords: *lab, test, result, value, measurement, blood pressure, respiratory rate, creatinine, chloride, hematocrit, weight, daily weight, microbiology, culture, mrsa screen, urine, serology, specimen*;
- temporal keywords: *since, after, before, on, in <month/year>, last, first, most recent, earliest, minimum, maximum*.
If any of these patterns appear, you must plan a query for the appropriate resource type before any aggregation or comparison logic runs.

## Procedure
1. **Normalize the question** – lower‑case, strip punctuation, collapse whitespace.
2. **Identify the target resource** using keyword groups:
   - `MedicationRequest` if the text contains any medication keyword.
   - `Observation` if the text contains any lab/measurement keyword.
   - `Condition` for words like *diagnosis, disease, condition*.
   - `Procedure` for *procedure, operation, repair, infusion*.
   - `Encounter` for *hospital visit, ICU stay, admission, discharge*.
3. **Disambiguate when multiple groups match** – prioritize in the order MedicationRequest → Observation → Condition → Procedure → Encounter.
4. **Construct the tool call**:
   ```json
   {"resource_type": "<identified>", "patient_fhir_id": "<patient_fhir_id>"}
   ```
   - Ensure the `resource_type` is one of the allowed types.
   - Do **not** request more than 5 different resource types in a single interaction.
5. **Insert the tool call** immediately after the planning phase and before any Python‑code execution.
6. **Pass the retrieved resources** to downstream skills (e.g., numeric_aggregation, observation_value_extraction, resolve_medication_reference).

## Checks
- Verify that the patient FHIR ID is present in the user context.
- Confirm the identified `resource_type` is in the whitelist {Patient, Encounter, Condition, MedicationRequest, Procedure, Observation, MedicationAdministration, Location, Specimen, Medication}.
- Ensure the generated JSON for the tool call is syntactically correct (commas, quotes, braces).
- After the query, check that at least one resource was returned; if none, return a graceful “No relevant records found” answer.

## Avoid
- Failing to issue a query when the question mentions medication, lab tests, or observations (the dominant missing_resource_query failure).
- Issuing a query for the wrong resource type (e.g., querying Observation for a medication question).
- Over‑querying unrelated resources or exceeding the safe limit of resource types.
- Producing malformed JSON that causes a tool‑call error.
- Assuming date filters are applied inside the query; date handling should be done later in Python code after the resources are fetched.
