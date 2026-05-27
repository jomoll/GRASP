---
description: Search for a patient by name/DOB, then parse the identifier array to
  return the MRN or "Patient not found"
name: extract_mrn
provenance:
  action: ADD
  epoch: 1
  fixes: 13
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task9_6
  - task1_26
  - task1_16
  - task1_13
  - task5_7
  - task9_27
  update_cycle: 0
tags: []
version: 1
---

# extract_mrn

## Pattern Description
You must reliably locate a patient when the task provides a full name and date of birth, then extract the Medical Record Number (MRN) from the Patient resource’s `identifier` array.  The MRN is the value of the identifier whose `type.coding.code` is `MR` (or whose `system` matches the institution’s MRN namespace).  This skill also defines the correct FHIR search parameters for name‑based queries, avoiding the common mistake of using the generic `name` parameter which often returns no results.

## When to Use This Skill
- The instruction asks: *“What’s the MRN of the patient with name **X Y** and DOB **YYYY‑MM‑DD**?”*.
- The task expects either the MRN string (e.g., `"S3213957"`) or the literal response `"Patient not found"`.
- The agent has just performed a `GET /Patient` request and received a Bundle response.

## Common Failure Patterns
- Using `GET /Patient?name=First%20Last&birthdate=...` which returns an empty Bundle even though the patient exists.
- Returning the whole identifier object or the wrong field (e.g., `system` instead of `value`).
- Forgetting to handle the case where the Bundle has `total = 0` and responding with an empty string instead of the required phrase.

## Recommended Patterns
**Pattern 1: Correct patient search**
1. Split the full name into `family` (last name) and `given` (first name).  If a middle name is present, include it in `given`.
2. Issue the request:
   ```
   GET {api_base}/Patient?family={family}&given={given}&birthdate={YYYY-MM-DD}
   ```
3. Inspect the Bundle:
   - If `total == 0`, immediately `FINISH(["Patient not found"])`.
   - If `total >= 1`, proceed to extraction.

**Pattern 2: MRN extraction from identifier array**
1. Locate the first entry in `entry[0].resource.identifier` where:
   - `type.coding[].code == "MR"` **or**
   - `system` matches a known MRN system (e.g., contains `hospital.org/mrn`).
2. Extract the `value` field of that identifier.
3. Return it as a JSON string array:
   ```
   FINISH(["{mrn_value}"])
   ```
4. If no such identifier is found, fall back to the first identifier’s `value` as a best‑effort MRN.

**Pattern 3: Fallback / verification**
- If the search with `family/given` fails but a previous request with `identifier={some}` succeeded, you may reuse that MRN.
- Always verify that the extracted MRN matches the pattern `^S\d+$` (or the institution’s MRN regex).  If it does not, treat it as not found.

## Example Application
**Task:** "What’s the MRN of the patient with name Victoria Owens and DOB of 2002-06-07? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Split name → `family=Owens`, `given=Victoria`.
2. GET `http://localhost:8080/fhir/Patient?family=Owens&given=Victoria&birthdate=2002-06-07`.
3. Bundle response shows `total = 1` and contains:
   ```json
   "identifier": [
     {"system":"urn:oid:1.2.3.4","value":"S1234567","type":{"coding":[{"code":"MR"}]}}
   ]
   ```
4. Extract `value` → `S1234567`.
5. FINISH(["S1234567"]).

**Incorrect flow (what to avoid):**
- Using `name=Victoria%20Owens` → Bundle `total = 0` → agent incorrectly returns `Patient not found` even though the patient exists.
- Returning the whole identifier object instead of just the `value`.

## Success Indicators
- The agent issues a GET request with `family` and `given` parameters.
- The FINISH output is either `"Patient not found"` or a plain MRN string matching the expected pattern.
- No identifier objects or extra JSON structures appear in the final answer.

## Failure Indicators
- The request URL contains `name=` instead of `family=`/`given=`.
- The FINISH payload includes an object, array of objects, or extra text (e.g., `"MRN: S1234567"`).
- The agent returns an empty array or a non‑string when the patient is missing.
