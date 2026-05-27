---
description: Resolve MRN to Patient.id once, then consistently reuse that resolved
  id/reference in all follow-on queries and writes.
name: patient_identifier_to_fhir_reference_resolution
provenance:
  action: MODIFY
  epoch: 1
  fixes: 7
  parent_version: 1
  probe_score: 7
  regressions: 1
  triggering_sample_ids:
  - task4_7
  - task2_30
  - task9_22
  - task8_3
  - task4_4
  - task2_22
  - task9_1
  - task4_28
  - task2_26
  - task2_1
  update_cycle: 1
tags:
- fhir
- patient-resolution
- observation-search
- resource-reference
version: 2
---

# Patient Identifier to FHIR Reference Resolution

## Pattern Description

When a task gives me an MRN or other patient identifier, I must first determine whether downstream FHIR interactions need a Patient resource id or a patient search value. I should do one explicit patient lookup, extract the canonical patient identifier fields from the returned Patient resource, and then stay consistent for the rest of the task.

The key reusable lesson is persistence after resolution: once I have identified the patient representation that works for the current task, I must reuse that same resolved value in every later `Observation?patient=...`, `Condition?patient=...`, or `subject.reference` field. I must not switch back to the original MRN on retries, after a 400 error, or when a first query returns empty results.

## When to Use This Skill

- When the user gives an MRN like `S6474456` and I need to query patient-scoped resources such as `Observation`, `Condition`, `MedicationRequest`, or `ServiceRequest`
- When I start with `GET /Patient?identifier=<MRN>` before any follow-on search or POST
- When a task requires `Observation?patient=...` after a patient lookup
- When I need to build `subject.reference` or another patient reference inside a POST body
- When an earlier attempt failed and I am considering retrying with the raw MRN instead of the resolved patient value
- When the Patient lookup response shows both a resource `id` and an MRN in `identifier`, and I need to choose the right one for later steps

## Common Failure Patterns

- Using `Observation?patient=<MRN>` after already resolving a different `Patient.id` from `GET /Patient?identifier=<MRN>`
- Extracting the resolved id once, but then reverting to the original MRN in a later retry: `patient=S1521703` instead of the previously resolved patient value
- Returning `-1` or "not found" immediately after an empty bundle from the wrong patient parameter, without retrying the Observation search using the resolved patient id
- Mixing forms across one task, such as first trying `patient=786888` and then falling back to `patient=S6474456`
- Building `subject.reference` with an identifier-like string when the task context or prior lookup established a specific `Patient/<id>` reference to use
- Treating a transport error or malformed combined request as evidence the patient has no data, instead of reissuing a clean Patient lookup and then reusing the resolved patient value

## Recommended Patterns

**Pattern 1: resolve once, store the exact reusable patient value**
1. Issue `GET /Patient?identifier=<MRN>`.
2. Inspect the first matching `entry.resource`.
3. Extract `resource.id` and note the canonical reference form `Patient/<resource.id>`.
4. For follow-on searches that use the `patient` search parameter, use the resolved patient id value from the lookup result consistently for the rest of the task.
5. For POST bodies that need a reference, use `subject.reference` as `Patient/<resolved id>` unless the server behavior for this environment clearly requires another returned stable form.

CORRECT: after Patient lookup returns id `786888`, query `GET /Observation?patient=786888&code=MG`
WRONG: after resolving `786888`, retry with `GET /Observation?patient=S6474456&code=MG`

**Pattern 2: never fall back to the original MRN after resolution**
1. If my first downstream query fails because the request was malformed, resend the same intended query cleanly using the already resolved patient id.
2. If a downstream query returns an empty bundle, verify date/code filters or inspect bundle content, but do not silently substitute the raw MRN into `patient=`.
3. Only conclude "no results" after I have executed a valid query with the resolved patient value.

CORRECT: resolve `Patient.id`, then reissue `Observation?patient=<resolved id>&code=A1C`
WRONG: resolve `Patient.id=585607`, then query `Observation?patient=S6488980&code=A1C` and stop

**Pattern 3: keep read-path and write-path references aligned**
1. If I looked up the patient before a write, use the same resolved patient identity in all subsequent search parameters and resource references.
2. When constructing a POST body, set `subject.reference` to `Patient/<resolved id>`.
3. Do not mix one form for reads and another unrelated form for writes within the same task.

CORRECT: `"subject": {"reference": "Patient/786888"}` after lookup returned id `786888`
WRONG: `"subject": {"reference": "Patient/S6474456"}` after lookup returned a different resource id

## Example Application

**Task:** "What’s the most recent magnesium level of the patient S6474456 within last 24 hours?"

**Step-by-step:**

1. Issue `GET /Patient?identifier=S6474456`.
2. From the Patient bundle, extract `entry[0].resource.id` = `786888`.
3. Issue `GET /Observation?patient=786888&code=MG&date=ge2023-11-12T10:15:00Z`.
4. If the request needs to be retried, retry with the same `patient=786888`, not `patient=S6474456`.
5. Only if this resolved-id query returns no qualifying observations should I return `-1`.

CORRECT output: `FINISH([1.9])`
WRONG output:   `FINISH(["-1"])` after querying `Observation?patient=S6474456&code=MG&date=ge2023-11-12T10:15:00Z`

**Task:** "What’s the last HbA1C value in the chart for patient S6488980 and when was it recorded?"

**Step-by-step:**

1. Issue `GET /Patient?identifier=S6488980`.
2. Extract `entry[0].resource.id` = `585607`.
3. Issue `GET /Observation?patient=585607&code=A1C`.
4. Sort/select the most recent returned Observation, extract the value and date.
5. If ordering is needed afterward, use `subject.reference = Patient/585607`.

CORRECT output: `FINISH([5.4, "2023-11-02T06:53:00+00:00"])`
WRONG output:   `FINISH(["-1"])` after querying `Observation?patient=S6488980&code=A1C`

## Success Indicators

- After `GET /Patient?identifier=...`, my later requests consistently use one resolved patient value instead of flipping between MRN and id
- No later `Observation?patient=` query reuses the raw MRN once a different resolved patient id was obtained
- I only return `-1`, "not found", or equivalent after a valid follow-on query using the resolved patient value
- POST bodies use `subject.reference` built from the resolved patient identity gathered earlier in the task

## Failure Indicators

- My action trace shows both `patient=<resolved id>` and later `patient=<original MRN>` for the same task
- I perform a correct Patient lookup but ignore the returned `resource.id`
- I abandon the resolved patient value after a malformed request or empty result bundle
- I finish with `-1` or "Patient not found" even though I never executed the downstream search with the resolved patient id
- My POST body references `Patient/<MRN>` despite having already resolved a distinct Patient resource id
