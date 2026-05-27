---
description: Search for a patient using split given/family name and DOB, then return
  the MRN or "Patient not found".
name: patient_search_by_given_family_and_dob
provenance:
  action: ADD
  epoch: 0
  fixes: 3
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task9_8
  - task4_10
  - task2_16
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  update_cycle: 0
tags:
- patient_search
- fhir
- mrn_lookup
version: 1
---

# Patient Search by Given/Family Name and DOB

## Pattern Description
You must locate a patient when the task provides a full name (e.g., "Glenda Hall") and a birthdate.  Instead of using the generic `name=` query parameter, split the name into `given=` (first name) and `family=` (last name) and include `birthdate=`.  This pattern works reliably with the FHIR server used in the environment and avoids false‑negative "Patient not found" results.

## When to Use This Skill
- The instruction asks for the MRN (identifier) of a patient given a full name and DOB.
- The task expects a single string MRN or the literal "Patient not found".
- The agent is about to issue a `GET /Patient` request.

## Common Failure Patterns
- Using `GET /Patient?name=Full%20Name&birthdate=YYYY-MM-DD` which returns `total: 0` even though the patient exists.
- Not URL‑encoding the name correctly, causing the server to treat the space as a separator.
- Extracting the MRN from the wrong field (e.g., from `identifier` array instead of the resource `id`).

## Recommended Patterns
**Pattern 1: Construct the correct search URL**
1. Split the supplied full name on the first space: `given = first token`, `family = remainder`.
2. Build the URL:
   ```
   GET {api_base}/Patient?given={given}&family={family}&birthdate={YYYY-MM-DD}
   ```
   URL‑encode each component.
3. Issue the request.

**Pattern 2: Interpret the response**
- If the Bundle `total` field is `0`, call `FINISH(["Patient not found"])`.
- If `total` is `1` (or >0), locate the first entry:
  ```json
  mrn = bundle.entry[0].resource.id
  ```
  (The MRN is the resource ID; most datasets also expose it via `identifier` but `id` is guaranteed.)
- Call `FINISH([mrn])`.

**Pattern 3: Fallback verification**
- If the response contains multiple entries, verify that the `birthdate` of each matches the requested date; pick the first exact match.
- If none match, fall back to "Patient not found".

## Example Application
**Task:** "What’s the MRN of the patient with name Glenda Hall and DOB of 1952-11-14? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Split name → `given=Glenda`, `family=Hall`.
2. Issue:
   ```
   GET http://localhost:8080/fhir/Patient?given=Glenda&family=Hall&birthdate=1952-11-14
   ```
3. Receive Bundle with `total: 1` and entry resource ID `S1234567`.
4. Extract `mrn = "S1234567"`.
5. `FINISH(["S1234567"])`.

**CORRECT output:** `FINISH(["S1234567"])`
**WRONG output:** `FINISH(["Patient not found"])` when the Bundle actually contains a matching patient.

## Success Indicators
- The agent issues a GET request with `given=` and `family=` parameters.
- The final FINISH call returns a single MRN string that matches the patient’s `id`.
- No "Patient not found" is returned when the server reports a matching entry.

## Failure Indicators
- The agent still uses `name=` in the query.
- The FINISH output is "Patient not found" despite a non‑zero `total` in the response.
- The extracted MRN is taken from the wrong field (e.g., a nested identifier that does not contain the MRN).
