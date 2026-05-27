---
description: Resolve Patient search results into a reusable FHIR patient id/reference
  before all downstream queries and writes.
name: resolve_patient_identifier_before_dependent_search
provenance:
  action: MODIFY
  epoch: 2
  fixes: 3
  parent_version: 2
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - task3_29
  - task2_22
  - task3_7
  - task2_14
  - task2_15
  - task2_6
  - task3_10
  - task10_12
  - task8_29
  - task3_30
  update_cycle: 1
tags:
- fhir
- patient-resolution
- search
- references
version: 3
---

# Resolve Patient Identifier Before Dependent Search

## Pattern Description

When a task names a patient by an external identifier, you must first resolve that identifier with a `Patient` search, then consistently reuse the resolved FHIR patient identity in every downstream read or write. The reusable lesson is: do not treat the user-facing identifier as interchangeable with every resource's `patient` search parameter or `subject.reference` value.

This should change behavior immediately after `GET /Patient?identifier=...` succeeds. Once a Patient is found, you must extract the actual Patient resource identity and use that resolved value for all dependent resource searches (`Observation`, `Procedure`, `MedicationRequest`, etc.) and for POST bodies that need `subject.reference`.

## When to Use This Skill

- When the instruction names a patient like `patient S3032536` and you plan any downstream FHIR search or POST.
- When you issue `GET /Patient?identifier=<external-id>` and the response has `total > 0` or a populated `entry` array.
- When constructing downstream queries with `patient=` or POST bodies with `subject.reference`.
- When a first dependent search returns `total: 0` after using the raw external identifier, especially right after a successful Patient lookup.
- When you need to query multiple resource types for the same patient in one task.

## Common Failure Patterns

- After `GET /Patient?identifier=S3032536`, querying `Observation?patient=S3032536` without first extracting the Patient resource identity.
- Resolving the patient once, but then forgetting to reuse that resolved id on later searches for a second code or second time window.
- Switching inconsistently between `patient=<external-id>` and `patient=Patient/<external-id>` instead of using the resolved identity from the Patient bundle.
- Building a POST body with `subject.reference: "Patient/<external-id>"` without checking the actual resolved Patient resource id/reference.
- Seeing `Bundle.total = 1` from `Patient?identifier=...` and still acting as though the patient is unresolved.
- Treating an empty dependent search as evidence of absence before verifying that the patient parameter used the resolved identity.

## Recommended Patterns

**Pattern 1: resolve once, then cache and reuse**

1. Start with `GET /Patient?identifier=<task-patient-identifier>`.
2. From `entry[0].resource.id`, extract the resolved FHIR Patient id.
3. Construct a reusable patient reference string as `Patient/<resolved-id>`.
4. Reuse that resolved identity for every later request in the task.

CORRECT: `entry[0].resource.id = "7d8dca7d-8b9b-4e57-9cc8-8b5b1479e7d1"`, then use that id/reference consistently downstream.
WRONG: continue using the raw task identifier only because it matched the original lookup input.

**Pattern 2: use resolved identity before concluding no data**

If a dependent search is about to use `patient=<external-id>`, stop and replace it with the resolved Patient id/reference first. If you already made one empty search with the raw identifier, rerun the search with the resolved patient identity before concluding there are no results.

CORRECT: after `Patient?identifier=S2161163` succeeds, query `Observation?patient=<resolved-id>&code=HEARTRATE...`
WRONG: query `Observation?patient=S2161163&code=HEARTRATE...` for both 12-hour and 6-hour windows, then finish with "no observations found".

**Pattern 3: keep reads and writes aligned to the same patient identity**

For GET searches, prefer the same resolved patient identity format throughout the task. For POST bodies, set `subject.reference` to `Patient/<resolved-id>`.

CORRECT GET: `.../Observation?patient=<resolved-id>&code=TSH`
CORRECT POST: `"subject": {"reference": "Patient/<resolved-id>"}`
WRONG GET/POST mix: searching with the raw external identifier but posting to a different or unresolved patient reference.

## Example Application

**Task:** "Calculate the average heart rate over the past 6 hours and the past 12 hours for patient S3032536."

**Step-by-step:**

1. Issue `GET /Patient?identifier=S3032536`.
2. Extract `entry[0].resource.id` from the Patient bundle, for example `S3032536` or a server-assigned UUID if that is what the bundle contains.
3. Use the resolved patient id in both observation searches:
   - `GET /Observation?patient=<resolved-id>&code=HEARTRATE&date=ge2023-11-07T10:47:00Z&date=le2023-11-07T22:47:00Z`
   - `GET /Observation?patient=<resolved-id>&code=HEARTRATE&date=ge2023-11-07T16:47:00Z&date=le2023-11-07T22:47:00Z`
4. Only after those resolved-patient searches return do you compute averages or conclude no data.
5. Return the final answer in the required array format.

CORRECT output: `FINISH([77.0, 77.0])`
WRONG output: `FINISH(["No heart rate observations found in the past 6 hours.", "No heart rate observations found in the past 12 hours."])` after searching with `patient=S3032536` before reusing the resolved identity.

## Success Indicators

- After a successful `Patient?identifier=...` call, downstream queries use the resolved Patient id/reference rather than blindly reusing the input identifier.
- The same resolved patient identity appears across all related GETs and POSTs in the task.
- Empty dependent results are not accepted until the resolved patient identity has been tried.
- Multi-step tasks with several codes or time windows do not re-resolve unnecessarily and do not drift back to the raw identifier.

## Failure Indicators

- The trace shows `GET /Patient?identifier=...` followed by `Observation?patient=<raw-identifier>` or `Procedure?patient=<raw-identifier>` without any reuse of `entry[0].resource.id`.
- One dependent search uses the resolved id but later searches revert to the raw identifier.
- The agent finishes with no-data conclusions even though it never retried the search using the resolved patient identity.
- POST bodies contain `subject.reference` built from the raw external identifier instead of the resolved Patient resource identity.
