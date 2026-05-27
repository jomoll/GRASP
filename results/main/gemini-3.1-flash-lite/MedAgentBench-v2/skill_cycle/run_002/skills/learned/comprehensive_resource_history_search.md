---
description: Perform exhaustive searches across all relevant resource types and codes
  when specific queries return no results.
name: comprehensive_resource_history_search
provenance:
  action: ADD
  epoch: 0
  fixes: 8
  probe_score: 5
  regressions: 1
  triggering_sample_ids:
  - task9_28
  - task8_29
  - task3_10
  - task9_27
  - task2_15
  - task2_6
  - task3_17
  - task9_22
  - task9_1
  - task1_15
  update_cycle: 1
tags:
- fhir
- search
- history
version: 1
---

## Skill Title
Comprehensive Resource History Search

## Pattern Description
When a specific FHIR search (e.g., by code or date) returns an empty bundle, do not assume the record does not exist. The system may have stored the resource under a different code, a broader category, or a different resource type (e.g., Procedure vs. ServiceRequest vs. MedicationRequest). You must perform a broader search to verify the absence of the record before concluding it is missing.

## When to Use This Skill
- When a search for a specific code (e.g., CPT 90686) returns `total: 0`.
- When you are tasked with verifying the existence of a procedure, vaccination, or medication order and the initial targeted search fails.
- When you need to confirm a patient's history before ordering a new service or medication.

## Common Failure Patterns
- Assuming a zero-result search means the patient has no history of the event.
- Failing to search for broader categories (e.g., searching for a specific vaccine code but missing the general immunization category).
- Relying on a single search parameter (e.g., `code`) without attempting a broader search (e.g., by `patient` only) to inspect the full history.

## Recommended Patterns

**Pattern 1: Exhaustive Search**
If the initial search returns no results, perform a broader search using only the `patient` identifier and the resource type. Inspect the returned bundle for any relevant entries that might have been missed due to coding variations.

**Pattern 2: Cross-Resource Verification**
If a procedure is not found, check related resources. For example, if a vaccine is not in `Procedure`, check `Immunization` or `MedicationAdministration` if applicable.

## Example Application

**Task:** "Determine the date of the last influenza vaccine for patient S1478444."

**Step-by-step:**
1. Issue GET `http://localhost:8080/fhir/Procedure?patient=S1478444&code=90686`.
2. If `total: 0`, issue GET `http://localhost:8080/fhir/Procedure?patient=S1478444` to retrieve the full history.
3. Iterate through the returned bundle to find any influenza-related codes.
4. If still no record is found, conclude the patient has no history.

## Success Indicators
- Agent performs a broad search after a specific search fails.
- Agent identifies records that were missed by the initial narrow query.

## Failure Indicators
- Agent immediately concludes a record is missing after one failed specific search.
