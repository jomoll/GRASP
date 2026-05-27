---
description: "Extract and return a patient\u2019s MRN from a FHIR Patient search,\
  \ handling not\u2011found cases correctly"
name: patient_mrn_lookup
provenance:
  action: ADD
  epoch: 0
  fixes: 7
  probe_score: 5
  regressions: 2
  triggering_sample_ids:
  - task1_23
  - task10_13
  - task10_27
  - task1_6
  - task10_12
  - task5_3
  - task10_15
  - task9_11
  - task1_15
  - task4_11
  update_cycle: 0
tags:
- patient
- mrn
- lookup
- extraction
version: 1
---

# Patient MRN Lookup and Reporting

## Pattern Description
You must reliably retrieve a patient’s Medical Record Number (MRN) from a FHIR `Patient` search result. The task usually provides a name and birthdate and expects the MRN string, or the literal "Patient not found" when no matching patient exists. The core pattern is to inspect the returned `Bundle`, verify that it contains at least one `Patient` entry, and then extract the appropriate identifier value. If the bundle is empty or the identifier cannot be located, fall back to the not‑found response.

## When to Use This Skill
- When the instruction asks for the MRN of a patient given a name and DOB (e.g., *"What’s the MRN of the patient with name X and DOB Y?"*).
- When the agent has just performed a `GET {api_base}/Patient?name=...&birthdate=...` request and received a `Bundle` response.
- When the expected answer format is a single MRN string or the exact phrase **"Patient not found"**.

## Common Failure Patterns
- Ignoring the `Bundle.total` field and always returning "Patient not found".
- Extracting the whole `Patient` resource JSON instead of the identifier value.
- Returning the identifier object (e.g., `{ "value": "12345" }`) instead of the plain string.
- Using the wrong identifier field (e.g., `id` instead of the MRN in `identifier`).
- Failing to handle bundles with multiple entries (should use the first matching entry).

## Recommended Patterns
**Pattern 1: Core MRN extraction**
1. Inspect the response JSON. If `resourceType` is `Bundle` and `total` > 0, proceed; otherwise go to fallback.
2. Locate the first entry: `response.entry[0].resource` (should be a `Patient`).
3. Within that patient, find the identifier that represents the MRN. Common heuristics:
   - If the identifier array contains an element with `type.coding.code` equal to `MR` or a system matching your institution’s MRN namespace, use its `value`.
   - If no such hint exists, default to the first identifier in the array.
4. Set `mrn = identifier.value` (a plain string).
5. Call `FINISH([mrn])`.

**Pattern 2: Fallback when no patient found**
- If `total` is 0 **or** the patient resource lacks a usable identifier, call `FINISH(["Patient not found"])`.

**Pattern 3: Defensive checks**
- Verify that `response.entry` is an array before indexing.
- Guard against missing `identifier` field with a try/except‑style conditional.
- Log (via comment) which identifier was chosen for debugging.

## Example Application
**Task:** "What’s the MRN of the patient with name Julie Rodriguez and DOB of 1962-01-20? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?name=Julie%20Rodriguez&birthdate=1962-01-20`
2. Receive bundle:
   ```json
   {"resourceType":"Bundle","total":1,"entry":[{"resource":{"resourceType":"Patient","identifier":[{"system":"http://hospital.org/mrn","value":"MRN123456"}]}}]}
   ```
3. `total` > 0 → extract first entry’s patient.
4. Find identifier with system `http://hospital.org/mrn`; value is `MRN123456`.
5. `FINISH(["MRN123456"])`.

**If the bundle had `total:0`** the agent would execute `FINISH(["Patient not found"])`.

## Success Indicators
- The final `FINISH` call contains a single‑element list with the exact MRN string when a patient exists.
- When no patient matches, the list contains exactly the string "Patient not found".
- No raw JSON objects or extra text appear in the output.

## Failure Indicators
- `FINISH` returns "Patient not found" while the bundle contains a patient entry.
- The output includes the whole patient JSON or an identifier object instead of the plain MRN.
- The agent crashes or returns an empty list because it tried to index a missing `entry` array.
