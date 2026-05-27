---
description: "Ensures MedicationRequest data is fetched before answering any medication\u2011\
  related question."
name: resource_query_precheck_medicationrequest
provenance:
  baseline_fixes: 5
  baseline_regressions: 5
  epoch: 0
  failure_mode: medication_request_not_queried_before_answer
  fixes: 4
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - 00b98d0bf4d50497625b257e
  - 0406ba9fa1c3ada7f76965a3
  - 098b1301820b7d581a339d0f
  - 0ceee1a85a040c4d57c27a09
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must invoke this skill whenever the user question mentions drugs, prescriptions, medication orders, dosing, routes, or any MedicationRequest‑related concept (e.g., "has patient X been given any drugs", "last medication prescribed", "medication via iv route", "total dose of ondansetron", etc.).

## Procedure
1. **Detect medication intent** – Scan the user query for keywords such as `medication`, `drug`, `prescribed`, `ordered`, `dose`, `route`, `iv`, `po`, `sc`, `im`, specific drug names, or any phrase indicating a medication request.
2. **Check prior queries** – Look in the current tool‑call history for a `get_resources_by_patient_fhir_id` (or `get_resources_by_resource_id`) call whose `resource_type` is `MedicationRequest` (or `MedicationAdministration`).
3. **If missing**, issue a new tool call before any further reasoning:
   ```json
   {
     "tool": "get_resources_by_patient_fhir_id",
     "args": {"resource_type": "MedicationRequest", "patient_fhir_id": "<patient_fhir_id>"}
   }
   ```
   *Optionally also fetch `MedicationAdministration` and `Medication` if the question may involve administration records.*
4. Store the retrieved resources in `retrieved_resources['MedicationRequest']` (and others) for downstream logic.
5. Continue with the specific medication‑handling logic of the original question (e.g., filtering by date, encounter, route, drug name, aggregating doses, counting distinct drugs, etc.).

## Checks
- Verify that after step 3 the `MedicationRequest` list is present (it may be empty, which is still a valid answer).
- If the question also restricts to a particular encounter type (hospital, ICU, ER), ensure the `encounter` reference in each MedicationRequest is resolved against the previously fetched Encounter resources before applying filters.
- Confirm that any date constraints (e.g., `since 2123`) are applied to the `authoredOn` or `occurrenceDateTime` fields of the MedicationRequest.
- Ensure the final answer respects the required format (e.g., `Yes/No`, count, list, dose value) and includes units when applicable.

## Avoid
- Answering medication questions without first querying MedicationRequest data, which leads to missing‑data errors.
- Assuming medication data is already available because another skill ran; always perform the explicit pre‑check.
- Ignoring encounter scope or date filters that the user specified.
- Returning default values (e.g., `0` or `None`) when the query was never executed.
