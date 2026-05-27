---
description: Verify patient existence before returning MRN, return "Patient not found"
  when no match
name: patient_lookup_by_name_dob
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 2
  triggering_sample_ids:
  - task9_9
  - task10_15
  - task1_7
  - task4_21
  - task4_10
  - task10_16
  - task2_6
  - task4_26
  - task2_26
  - task4_11
  update_cycle: 1
tags:
- patient_lookup
- verification
- existence_check
version: 3
---

# Patient Lookup by Name and DOB with Existence Verification

## Pattern Description
You must locate a patient using the exact family name, given name, and birthDate supplied in the task. The search is performed via a FHIR `Patient` search. After receiving the Bundle response, you must explicitly verify that the bundle contains at least one entry (`total > 0`). If a matching patient is found, extract the first entry's identifier (`identifier[0].value`) and return it as a plain string inside `FINISH`. If the bundle is empty, you must return the literal string `"Patient not found"` inside `FINISH`. This prevents false positives when the server returns an empty result set.

## When to Use This Skill
- When the task asks: *"What’s the MRN of the patient with name <given> <family> and DOB <date>? If the patient does not exist, the answer should be \"Patient not found\""*.
- When a GET request to `/Patient?family=...&given=...&birthdate=...` is required before answering.
- When the task explicitly expects a free‑text MRN or the phrase *Patient not found*.

## Common Failure Patterns
- Ignoring the `total` field and assuming an entry exists, leading to extraction of a non‑existent identifier.
- Returning the identifier from a previous request when the current bundle is empty.
- Returning a JSON array or object instead of a plain string.
- Forgetting to wrap the literal "Patient not found" in quotes inside `FINISH`.

## Recommended Patterns
**Pattern 1: Core lookup and verification**
1. Issue `GET {api_base}/Patient?family={family}&given={given}&birthdate={birthdate}`.
2. Parse the response JSON Bundle.
3. If `bundle.total == 0` **or** `bundle.entry` is missing, `FINISH("Patient not found")`.
4. Otherwise, locate the first entry: `patient = bundle.entry[0].resource`.
5. Extract the MRN: `mrn = patient.identifier[0].value` (assume the first identifier is the MRN).
6. Return `FINISH(["{mrn}"])`.

**Pattern 2: Fallback sanity check**
- If the identifier field is missing or empty, treat it as no match and return "Patient not found".

**Pattern 3: Output formatting**
- Always output a JSON array containing a single string, e.g. `FINISH(["S1234567"])` or `FINISH(["Patient not found"])`.

## Example Application
**Task:** "What’s the MRN of the patient with name Kevin Vasquez and DOB of 1953-11-19? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?family=Vasquez&given=Kevin&birthdate=1953-11-19`
2. Receive Bundle. Suppose `"total": 0`.
3. Because `total` is 0, execute `FINISH(["Patient not found"])`.

**Correct output:** `FINISH(["Patient not found"])`
**Wrong output:** `FINISH(["S6200102"])` (MRN returned despite no patient).

## Success Indicators
- The agent performs a GET request with the exact name and DOB parameters before finishing.
- The agent checks `bundle.total` (or the presence of `entry`).
- The final `FINISH` payload is either `["<MRN>"]` when a patient exists or `["Patient not found"]` when none exist.

## Failure Indicators
- The agent calls `FINISH` without a preceding GET request.
- The agent returns an MRN when `bundle.total == 0`.
- The agent returns a JSON object or array of numbers instead of a single‑string array.
- The literal "Patient not found" is omitted or misspelled.
