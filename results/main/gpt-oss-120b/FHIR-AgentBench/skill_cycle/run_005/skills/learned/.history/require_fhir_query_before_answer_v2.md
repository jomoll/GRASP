---
description: Enforce a FHIR query for any needed resource type inferred from the question
  before answering.
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 4
  baseline_regressions: 5
  epoch: 1
  failure_mode: missing_fhir_query_before_answer
  fixes: 6
  parent_version: 1
  probe_score: 7
  regressions: 0
  triggering_sample_ids:
  - 01c02f4b897bb8192e16bd1d
  - 02960e704986efbe2e56a892
  - 02a069698a803a8419fa294c
  - 05c1bc3943f37d24fbc4a227
  - 0702bc77d929f78085010bb0
  update_cycle: 1
tags: []
version: 2
---

## When to use
You must invoke this skill whenever the user asks for information that depends on FHIR data (e.g., values, counts, dates, medications, procedures, diagnoses, encounters, admissions, discharges, lab results, vital signs, or any attribute that must be retrieved from a FHIR resource). Detect this by looking for keywords such as **minimum, maximum, average, count, how many, difference, first, last, since, during, on, was, did, what, when, weight, blood pressure, heart rate, medication, drug, prescription, procedure, diagnosis, encounter, visit, discharge, admission, test, culture, output, volume**.

## Procedure
1. **Parse the question** to extract likely resource type clues:
   - Observation‑related words → `Observation`
   - Medication‑related words → `MedicationRequest` (and possibly `MedicationAdministration`)
   - Procedure‑related words → `Procedure`
   - Diagnosis / condition words → `Condition`
   - Encounter / visit / admission / discharge words → `Encounter`
   - Output / volume / fluid words → `Observation` (often with specific codes)
2. **Check the current turn’s tool call history** for a `get_resources_by_patient_fhir_id` (or `get_resources_by_resource_id`) that requested the inferred resource type.
3. If **no such query** is present, **emit a single query** for the missing resource type using the patient’s FHIR ID (the ID is always supplied in the user context). Do **not** answer the question yet; defer answer generation until the query result is available.
4. After the query returns, **re‑run the original reasoning** (the agent’s normal answer logic) now that the required data is present.
5. If the query returns an empty bundle for the needed type, answer with a clear "No data" response appropriate to the question type (e.g., `0`, `None`, `No`, or a sentence stating that the information is unavailable).

## Checks
- Verify that the inferred resource type matches at least one of the supported FHIR types: `Observation`, `MedicationRequest`, `MedicationAdministration`, `Procedure`, `Condition`, `Encounter`.
- Ensure **only one** additional query is issued per turn; if multiple resource types are inferred, prioritize the most specific one (e.g., if both Observation and Encounter are mentioned, choose Observation for value‑based queries, Encounter for admission‑type queries).
- After the query, confirm that the retrieved resources contain the fields required by the question (e.g., `valueQuantity`, `effectiveDateTime`, `code.display`).
- Confirm that the final answer’s type matches the expected format (boolean, numeric, date‑time, list, or string) as enforced by `answer_format_enforcement`.

## Avoid
- Issuing duplicate or unnecessary queries for resource types that have already been fetched in the same turn.
- Guessing a resource type when the question contains ambiguous wording; in ambiguous cases, default to the most common type (`Observation`).
- Answering before the required data is available, which leads to JSON syntax errors or incorrect answers.
- Over‑filtering the question text so that legitimate resource cues are missed (e.g., “last hospital discharge” must still trigger an `Encounter` query).
