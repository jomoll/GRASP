---
description: Ensures MRN is returned only after confirming a patient record exists
  in the GET /Patient response
name: patient_mrn_lookup_with_validation
provenance:
  action: ADD
  blind_select: proposer-preferred
  epoch: 0
  fixes_unused: 12
  probe_score_unused: 2
  regressions_unused: 0
  triggering_sample_ids:
  - task1_10
  - task2_25
  - task9_28
  - task4_20
  - task9_20
  - task1_7
  - task2_17
  - task8_14
  - task8_19
  - task1_23
  update_cycle: 1
tags:
- patient_lookup
- mrn_extraction
- validation
version: 1
---

# Patient MRN Lookup with Existence Validation

## Pattern Description
You must reliably retrieve a patient’s Medical Record Number (MRN) from a FHIR Patient search. The core capability is to **validate the search result before deciding what to answer**. After issuing a `GET /Patient` request, inspect the returned Bundle: if it contains at least one entry, extract the identifier that represents the MRN; if the Bundle is empty, answer "Patient not found". This prevents the agent from assuming a missing patient without evidence and guarantees correct handling of both identifier‑based and name‑plus‑DOB searches.

## When to Use This Skill
- When the task asks for the MRN of a patient given a name and DOB (e.g., `family=Cruz&given=Christopher&birthdate=1940-08-28`).
- When the task asks for the MRN of a patient given an identifier query (e.g., `identifier=S0658561`).
- Whenever a `GET {api_base}/Patient?...` request is performed and the next step is to produce either an MRN or the literal string "Patient not found".

## Common Failure Patterns
- Skipping inspection of the Bundle and immediately returning "Patient not found".
- Extracting the MRN from the request URL or from the query parameters instead of the response payload.
- Returning the whole Patient resource or a JSON object instead of a plain string inside a JSON array.
- Using the wrong field (`id` instead of the identifier of type MRN) which yields internal FHIR IDs rather than the clinical MRN.

## Recommended Patterns
**Pattern 1: Validate the Patient search result**
1. Issue the GET request exactly as instructed (e.g., `GET http://.../Patient?name=John%20Doe&birthdate=1970-01-01`).
2. When the response arrives, parse it as a JSON Bundle.
3. Check `bundle.total` (or the length of `bundle.entry`).
   - **If `total == 0`** → `FINISH(["Patient not found"])` and stop.
   - **If `total > 0`** → proceed to extraction.

**Pattern 2: Extract the MRN**
1. Locate the first entry: `patient = bundle.entry[0].resource`.
2. The MRN is stored in `patient.identifier` where the identifier’s `type.coding.code` equals `MR` (or any system your data uses). If no type filter is available, fall back to the first identifier.
3. Retrieve the identifier value: `mrn = patient.identifier[0].value`.
4. Return the MRN as a JSON string inside an array: `FINISH([mrn])`.

**Pattern 3: Fallback for identifier‑only queries**
- If the original request used `identifier=XYZ`, the response will usually contain the same identifier as the MRN. You can still apply the same validation steps; after confirming `total > 0`, simply return the identifier value from the first entry.

## Example Application
**Task:** "What’s the MRN of the patient with name Christopher Cruz and DOB of 1940-08-28? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?family=Cruz&given=Christopher&birthdate=1940-08-28`
2. Parse response Bundle.
   - `total` is 1 → continue.
3. `patient = bundle.entry[0].resource`
4. `mrn = patient.identifier[0].value` (e.g., `"S0658561"`)
5. `FINISH(["S0658561"])`

**Correct output:** `FINISH(["S0658561"])`
**Incorrect output:** `FINISH(["Patient not found"])` when `total` is 1, or `FINISH([{"id":"..."}])`.

## Success Indicators
- The agent issues a GET request, parses the Bundle, and makes a decision based on `total`.
- When a patient exists, the final FINISH contains a single string element that matches the MRN from the Patient resource.
- When no patient exists, the final FINISH contains exactly `["Patient not found"]`.

## Failure Indicators
- The agent returns "Patient not found" without checking `bundle.total`.
- The FINISH payload contains a JSON object, number, or extra whitespace instead of a plain string.
- The MRN extracted does not match any identifier value in the Patient resource (e.g., using the internal FHIR `id`).
