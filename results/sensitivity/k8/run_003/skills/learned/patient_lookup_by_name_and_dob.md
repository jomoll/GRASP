---
description: "Retrieve a patient\u2019s MRN using family, given name and birthdate\
  \ before answering any MRN\u2011related query."
name: patient_lookup_by_name_and_dob
provenance:
  action: ADD
  epoch: 2
  fixes: 8
  probe_score: 1
  regressions: 4
  triggering_sample_ids:
  - task4_28
  - task9_1
  - task9_9
  - task5_16
  - task9_5
  - task9_27
  - task1_26
  - task4_11
  - task9_22
  - task9_8
  update_cycle: 1
tags:
- patient
- lookup
version: 1
---

# Patient Lookup by Name and DOB

## Pattern Description
You must locate the correct patient record before answering any question that requires a patient identifier (MRN).  The reusable capability is to query the FHIR server with the patient’s family name, given name, and birthdate, then extract the identifier from the returned Bundle.  This pattern prevents answering from memory or speculation and guarantees that the MRN matches the current database.

## When to Use This Skill
- When the task asks: *“What’s the MRN of the patient with name <Family> <Given> and DOB <YYYY‑MM‑DD>?”*
- When a downstream action (e.g., creating an Observation, ServiceRequest, or ordering a lab) requires a patient reference but only the name/DOB is provided.
- When the task explicitly says to return **"Patient not found"** if no match exists.

## Common Failure Patterns
- Agent attempts to answer directly without issuing a GET request.
- Agent uses a generic `name` query parameter instead of the required `family`, `given`, and `birthdate` parameters.
- Agent extracts the wrong field (e.g., uses `fullUrl` string instead of the patient identifier).
- Agent returns a free‑text sentence instead of the required JSON array format.

## Recommended Patterns
**Pattern 1: Core patient lookup**
1. Construct the GET request:
   ```
   GET {base_url}/Patient?family={Family}&given={Given}&birthdate={YYYY-MM-DD}
   ```
2. Send the request and receive a Bundle.
3. If `Bundle.total == 0` → `FINISH(["Patient not found"])`.
4. Otherwise, locate the first entry’s `resource.id` (or the identifier with system matching your MRN scheme) and set `mrn = entry.resource.id`.
5. Return the MRN in a JSON array: `FINISH(["{mrn}"])`.

   **CORRECT** example response extraction:
   ```
   mrn = bundle.entry[0].resource.id   # e.g., "S6551923"
   FINISH(["S6551923"])
   ```
   **WRONG** example:
   ```
   mrn = bundle.entry[0].fullUrl   # returns a URL, not the MRN
   FINISH([mrn])
   ```

**Pattern 2: Fallback when no match**
- If the GET returns a 404 or an empty Bundle, immediately finish with the literal string "Patient not found" as shown above.

**Pattern 3: Formatting the final output**
- Always wrap the MRN (or the not‑found string) in a JSON array passed to `FINISH`.
- Do not add extra explanatory text.

## Example Application
**Task:** "What’s the MRN of the patient with name Victoria Owens and DOB of 2002-06-07? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Patient?family=Owens&given=Victoria&birthdate=2002-06-07`.
2. Receive Bundle. Suppose `total = 1` and the patient resource has `id = "S1234567"`.
3. Extract `mrn = "S1234567"`.
4. `FINISH(["S1234567"])`.

If the Bundle had `total = 0`, the agent would instead do `FINISH(["Patient not found"])`.

## Success Indicators
- A GET request with the exact `family`, `given`, and `birthdate` parameters is performed.
- The agent extracts the patient `id` (or appropriate identifier) from the first entry.
- The final `FINISH` call contains a JSON array with either the MRN string or the literal "Patient not found".

## Failure Indicators
- No GET request is issued before `FINISH`.
- The GET request omits any of the required query parameters.
- The agent returns free‑text or a non‑array JSON payload.
- The extracted value is a URL or other field that is not the MRN.
