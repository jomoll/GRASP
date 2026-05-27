---
description: Deduplicate medication names across coding variations when counting distinct
  drugs.
name: distinct_drug_count_normalization
provenance:
  baseline_fixes: 3
  baseline_regressions: 2
  epoch: 6
  failure_mode: count_aggregation_error
  fixes: 5
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - 02a069698a803a8419fa294c
  - 072f960a91e48e6fe38d81a1
  - 09c4726f77bd8073eeb8d985
  - 0c6cdc444ee911941bfd23f0
  update_cycle: 1
tags:
- count_aggregation
- medication
- normalization
version: 1
---

## When to use
You must invoke this skill for any question that asks for a **count of distinct drugs/medications** prescribed to a patient within a specific time window (e.g., "how many unique drugs were prescribed", "count of distinct medications", etc.). The failure mode it addresses is inflated counts caused by different representations of the same drug (different `display`, `code`, NDC, whitespace, or case).

## Procedure
1. **Ensure required FHIR queries** – Verify that `MedicationRequest` and `Medication` resources have been fetched for the patient.
2. **Build a medication ID → name map**:
   - For each `Medication` resource, extract a candidate name in the following order:
     a. `code.coding[0].display`
     b. `code.coding[0].code` (e.g., NDC)
     c. `code.text`
   - If a name is found, **normalize** it:
     - Lower‑case the string.
     - Collapse consecutive whitespace to a single space.
     - Strip leading/trailing whitespace.
   - Store the normalized name keyed by the medication resource `id`.
3. **Iterate over all `MedicationRequest` resources** that fall inside the date range specified in the question:
   - Determine the request date using the first available of `authoredOn`, `occurrenceDateTime`, or `dispenseRequest.validityPeriod.start`.
   - If the date is outside the window, skip the request.
   - Extract the medication name:
     a. If `medicationCodeableConcept` exists, use the same extraction order as for `Medication` (display → code → text).
     b. Else if `medicationReference` exists, resolve the reference (`Medication/<id>`) against the map built in step 2.
   - **Normalize** the extracted name using the same routine as step 2.
   - Add the normalized name to a Python `set` of distinct drug names.
4. After processing all qualifying requests, compute `answer = len(distinct_name_set)`.
5. Return the integer answer.

## Checks
- **Resource presence**: confirm that both `MedicationRequest` and `Medication` were queried; if not, raise a prompt to fetch the missing type.
- **Date filtering**: ensure the date window matches the question (month/year, "since", "this year", etc.).
- **Normalization**: verify that each name added to the set is a non‑empty string after normalization.
- **Answer type**: the final answer must be an integer (numeric count).

## Avoid
- Counting the same drug multiple times because of different capitalisation, extra spaces, or using the raw code instead of the normalized display name.
- Including medication requests that lack a resolvable medication name.
- Ignoring the required date constraints, which can lead to counts from outside the requested period.
- Returning a non‑numeric type (e.g., a list) for a count question.
