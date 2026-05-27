---
description: Resolve identifier search results into Patient.id before any downstream
  query or write.
name: patient_identifier_to_fhir_reference_resolution
provenance:
  action: MODIFY
  epoch: 4
  fixes: 9
  parent_version: 3
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task8_5
  - task10_21
  - task10_16
  - task10_12
  update_cycle: 0
tags:
- fhir
- patient-resolution
- references
- query-planning
version: 4
---

# Patient Identifier to FHIR Reference Resolution

## Pattern Description

When a task gives you an MRN or other patient identifier, you must treat that identifier as a search key, not as a guaranteed downstream resource reference. First resolve it with `GET /Patient?identifier=...`, then parse the returned `Patient.id`, and only after that issue dependent searches or writes that need `patient=` or `subject.reference`.

This skill changes two behaviors. First, it prevents premature downstream actions before the patient search response has been read. Second, it prevents accidental reuse of the input MRN, stripped digits, placeholders, or template text where a resolved `Patient.id` or `Patient/{id}` must be used.

## When to Use This Skill

- When the task names a patient by MRN/identifier such as `S0789363`
- When you plan to call `GET /Observation`, `GET /Condition`, or other patient-scoped searches after a `GET /Patient?identifier=...`
- When constructing a POST body with `subject.reference`, `patient.reference`, or another patient reference field
- When the first patient lookup succeeded (`Bundle.total > 0`) and you need to use that patient in any later step
- When you notice yourself about to use the raw input identifier in `patient=` or `Patient/...`

## Common Failure Patterns

- Issuing `GET /Observation?patient=S0789363&code=A1C` without first parsing `entry[0].resource.id`
- Issuing `GET /Observation?patient=6550627&code=A1C` after stripping the leading `S` from the MRN
- Posting `"subject":{"reference":"Patient/"}` or `"Patient/UNKNOWN"` or `"Patient/<!--resolved-id-->"`
- Repeating `GET /Patient?identifier=...` multiple times after one successful match instead of caching the resolved id
- Launching multiple actions in one line before the patient search result is available, e.g. concatenating `GET /Patient...GET /Observation...FINISH(...)`
- Treating `fullUrl` or input MRN as interchangeable with `resource.id` without checking the actual returned field

## Recommended Patterns

## Pattern 1: resolve once, then cache the returned id

1. Issue exactly one patient lookup: `GET /fhir/Patient?identifier={input_identifier}`.
2. Read the response bundle.
3. If `entry[0].resource.id` exists, store it as the resolved patient id.
4. Use that resolved id for all downstream steps in the same task.

CORRECT: read `entry[0].resource.id = "S0789363"` and then use that value
WRONG: assume the input identifier, digits-only variant, or placeholder is acceptable without reading the bundle

## Pattern 2: block downstream queries and writes until resolution is complete

Before any dependent request, ask: "Do I already have a resolved `Patient.id` from the bundle?"

- For searches, use `patient={resolved_id}`
- For writes, use `"subject":{"reference":"Patient/{resolved_id}"}`
- If the patient search returned no entries, do not invent a reference; follow the task's missing-patient behavior instead

CORRECT: `GET /fhir/Observation?patient=S2016972&code=A1C` only after confirming `entry[0].resource.id == "S2016972"`
WRONG: `GET /fhir/Observation?patient=S2016972&code=A1C` before reading the Patient bundle
WRONG: `GET /fhir/Observation?patient=2016972&code=A1C`

## Pattern 3: never transform the identifier for patient references

If the task input is an MRN like `S6550627`, you must never:

- strip prefixes (`S6550627` -> `6550627`)
- substitute digits from memory
- leave blank references
- use template literals or comments in the JSON body

Only the actual resolved value from `entry[0].resource.id` is allowed in downstream patient reference fields.

CORRECT: `"subject":{"reference":"Patient/S6550627"}`
WRONG:   `"subject":{"reference":"Patient/6550627"}`
WRONG:   `"subject":{"reference":"Patient/UNKNOWN"}`

## Example Application

## Task

"What’s the last HbA1C value in the chart for patient S0789363 and when was it recorded? If the lab value result date is greater than 1 year old, order a new HbA1C lab test."

## Step-by-step

1. Issue patient lookup:
   `GET /fhir/Patient?identifier=S0789363`
2. Read `entry[0].resource.id` from the returned Bundle.
   Suppose it is `S0789363`.
3. Use that resolved id in the lab search:
   `GET /fhir/Observation?patient=S0789363&code=A1C`
4. Extract the most recent observation value/date.
5. If ordering is needed, construct the POST body with:
   `"subject":{"reference":"Patient/S0789363"}`
6. Return only the requested answer format.

CORRECT output: `FINISH([5.2,"2022-08-09T15:33:00+00:00"])`
WRONG output:   `FINISH([-1])` after querying `patient=6550627` or querying before resolution

## Success Indicators

- After `GET /Patient?identifier=...`, you read the bundle before taking any dependent action
- Only one successful identifier lookup is needed per task
- Every later `patient=` parameter or `Patient/{id}` reference matches the resolved `entry[0].resource.id`
- No blank, placeholder, transformed, or digits-only patient references appear in requests

## Failure Indicators

- A downstream request uses the raw input identifier without confirming the returned `Patient.id`
- You issue `Observation` or POST requests before the patient lookup response arrives
- You strip `S` or otherwise alter the identifier for `patient=` or `subject.reference`
- You repeat `GET /Patient?identifier=...` after already receiving a successful bundle
- Requests contain concatenated actions such as `GET ...GET ...FINISH(...)` instead of one completed step at a time
