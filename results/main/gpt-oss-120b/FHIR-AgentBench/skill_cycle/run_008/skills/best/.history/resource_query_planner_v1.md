---
description: "Select and fetch the correct FHIR resource(s) for medication\u2011related\
  \ queries before extraction."
name: resource_query_planner
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 2
  failure_mode: missing_resource_query
  fixes: 4
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 0266d6e5d007484e57bf12d6
  - 02a069698a803a8419fa294c
  - 072f960a91e48e6fe38d81a1
  update_cycle: 1
tags: []
version: 1
---

## When to use
Use this skill whenever the user asks about **medications, prescriptions, drug names, routes, counts, distinct drugs, first/last prescribed, or any query that involves MedicationRequest resources**. Typical trigger phrases include "prescribed", "medication", "drug", "dose", "route", "iv drip", "im", "po", "order", "count of distinct drugs", "first prescribed", etc. It also applies to any question that needs other non‑Observation resources (e.g., Condition, Procedure) if the pattern matches those domains.

## Procedure
1. **Parse the user instruction** to identify:
   - The target domain (medication, condition, procedure, etc.).
   - Any temporal qualifiers (e.g., "since 05/2142", "in 09/this year").
   - Encounter scope qualifiers (e.g., "first hospital encounter", "last ICU visit").
   - Route or formulation filters (e.g., "iv drip", "im", "po/ng").
2. **Map the domain to a FHIR resource type**:
   - Medication‑related → `MedicationRequest` (and optionally `MedicationAdministration` if the question mentions administration).
   - Procedure‑related → `Procedure`.
   - Condition‑related → `Condition`.
   - Encounter‑related → `Encounter`.
   - Observation‑related → defer to existing `observation_value_extraction`.
3. **Construct the query**:
   - Use `get_resources_by_patient_fhir_id` with the determined `resource_type` and the patient’s FHIR ID.
   - If the question specifies a particular encounter (e.g., "first hospital encounter"), first retrieve `Encounter` resources, select the matching encounter ID, and include it in a second query for the target resource (e.g., filter `MedicationRequest` where `encounter.reference` equals `Encounter/<id>`).
   - If a date range is provided, **do not apply the filter yet** – just retrieve all resources; downstream extraction skills will handle date filtering.
4. **Store the retrieved resources** in `retrieved_resources[<ResourceType>]` for later steps.
5. **Proceed to the appropriate extraction skill** (e.g., `observation_value_extraction` for vitals, a new medication‑extraction routine, etc.).

## Checks
- Confirm that the determined `resource_type` is a valid FHIR type (MedicationRequest, Procedure, Condition, Encounter, Observation).
- Verify that the patient FHIR ID is present; if missing, raise a clear error.
- After the query, ensure that `retrieved_resources[resource_type]` is not empty; if empty, return a polite answer indicating no matching records.
- When an encounter filter is requested, validate that the chosen encounter exists before using its ID.

## Avoid
- Defaulting to `Observation` for every query, which leads to *missing_resource_query* failures.
- Ignoring temporal or encounter qualifiers and returning unrelated records.
- Attempting to query resources not supported by the tool set (e.g., `Medication` directly without a reference).
- Applying date or route filters during the fetch step; those belong to the extraction/analysis phase to keep this skill reusable.
