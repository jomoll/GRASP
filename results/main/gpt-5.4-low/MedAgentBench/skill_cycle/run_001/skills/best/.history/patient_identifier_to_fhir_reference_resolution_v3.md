---
description: Resolve MRN to Patient.id once, then use that resolved id/reference in
  every downstream query and write.
name: patient_identifier_to_fhir_reference_resolution
provenance:
  action: MODIFY
  epoch: 2
  fixes: 11
  parent_version: 2
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task5_16
  - task9_11
  - task9_14
  - task5_7
  - task9_3
  - task10_21
  update_cycle: 0
tags:
- fhir
- patient-resolution
- observation-search
- resource-reference
version: 3
---

# Patient Identifier to FHIR Reference Resolution

## Pattern Description

When a task gives you a patient identifier such as an MRN, you must first resolve it through `GET /Patient?identifier=...`, then switch from the identifier string to the returned FHIR patient id for all downstream resource searches and references. The reusable rule is: identifiers are lookup inputs, but follow-on FHIR queries and write payloads should use the resolved `Patient.id` or `Patient/<id>`.

This skill should change behavior after a successful patient lookup. Once you have a matching `Patient` resource, stop reusing the original MRN in `patient=...`, `subject.reference`, or repeated patient lookups unless the first lookup truly failed. Cache the resolved id and consistently reuse it across Observation reads, ServiceRequest writes, and any other patient-linked actions.

## When to Use This Skill

- When the task names a patient by MRN or identifier like `S1311412`
- When you issue `GET /Patient?identifier=...` and receive a Bundle with `total > 0`
- When the next step is any patient-linked search such as `GET /Observation?patient=...`
- When constructing a write payload with `subject.reference` or another patient reference field
- When you notice yourself about to query `patient=<same identifier string from the prompt>` after already resolving the Patient
- When a first patient lookup succeeded and you are about to repeat `GET /Patient?identifier=...` instead of reusing the cached result

## Common Failure Patterns

- Calling `GET /Observation?patient=S1311412&code=K` after `GET /Patient?identifier=S1311412`
- Calling `GET /Observation?patient=S6192632&code=MG&date=ge...` using the MRN string rather than the resolved Patient id
- Posting a resource with `subject.reference: "Patient/S6500497"` just because the task supplied MRN `S6500497`
- Repeating `GET /Patient?identifier=...` multiple times after already receiving a matching `entry[0].resource.id`
- Using `entry[0].resource.identifier[0].value` as if it were the FHIR resource id
- Treating an empty Observation result from `patient=<MRN>` as proof that no data exists, without retrying with the resolved Patient id
- Mixing forms inconsistently across one task, such as querying with numeric id once and then posting with `Patient/<MRN>`

## Recommended Patterns

## Pattern 1: resolve once and cache the FHIR id

1. Issue `GET /Patient?identifier=<MRN>`.
2. If `Bundle.total > 0`, extract `entry[0].resource.id`.
3. Store that value mentally as the canonical patient id for the rest of the task.
4. Also form the canonical patient reference string `Patient/<resolved-id>` for write payloads.

CORRECT: `entry[0].resource.id = "1052747"` then use `patient=1052747`
WRONG:   keep using `patient=S1311412` because that was the task input

## Pattern 2: substitute the resolved id into every downstream search and write

For searches, use the bare resolved id in the search parameter.
For writes, use `Patient/<resolved-id>` in reference fields.

CORRECT search: `GET /Observation?patient=1052747&code=K`
WRONG search:   `GET /Observation?patient=S1311412&code=K`

CORRECT write: `"subject": {"reference": "Patient/1052747"}`
WRONG write:   `"subject": {"reference": "Patient/S1311412"}`

Apply this to all downstream resources, including `Observation`, `Condition`, `MedicationRequest`, and `ServiceRequest`.

## Pattern 3: do not repeat lookup or conclude absence from identifier-based queries

If patient resolution succeeded, do not call `GET /Patient?identifier=...` again unless the earlier response was malformed or empty. Reuse the cached id.

If you accidentally queried with `patient=<MRN>` and got `total: 0`, do not conclude `-1` or "not found" yet. Re-run the resource query with `patient=<resolved-id>` first, then interpret the result.

## Example Application

**Task:** "What’s the last HbA1C value in the chart for patient S2016972 and when was it recorded? If the result date is greater than 1 year old, order a new HbA1C lab test."

## Step-by-step:

1. Issue `GET /Patient?identifier=S2016972`.
2. From the Bundle, extract `entry[0].resource.id` (for example, `2016972` if that is the actual FHIR id returned).
3. Query Observations with the resolved id: `GET /Observation?patient=2016972&code=A1C`.
4. Read the most recent Observation from the returned entries.
5. If ordering is needed, construct the POST body with `"subject": {"reference": "Patient/2016972"}`.
6. Return only the requested answer format after all needed actions are complete.

CORRECT output: `FINISH([6.5,"2022-03-08T08:14:00+00:00"])`
WRONG output:   `FINISH(["-1"])` after only querying `GET /Observation?patient=S2016972&code=A1C`

## Success Indicators

- After a successful `GET /Patient?identifier=...`, your next patient-linked query uses `patient=<entry[0].resource.id>`
- You issue only one successful patient-resolution lookup per task in normal flow
- POST bodies use `subject.reference` as `Patient/<resolved-id>`
- You do not report missing labs immediately after an identifier-based patient query without first using the resolved id
- All patient-linked operations within the task use the same canonical id/reference consistently

## Failure Indicators

- Any downstream URL still contains `patient=S...` after a successful patient lookup
- Any write payload contains `"reference": "Patient/S..."` when `entry[0].resource.id` was available
- You repeat `GET /Patient?identifier=...` despite already having a valid patient match
- You return `-1`, "Patient not found", or "no result" after querying related resources with the MRN string instead of the resolved id
- You use `identifier.value` instead of `resource.id` as the patient search parameter or reference target
- The task shows inconsistent patient forms across steps, such as one query with numeric id and another with MRN
