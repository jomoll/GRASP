---
description: Validate and replace placeholder procedure codes with correct LOINC identifiers
  for Procedure resources
name: procedure_code_validation
provenance:
  action: ADD
  epoch: 0
  fixes: 9
  probe_score: 3
  regressions: 0
  triggering_sample_ids:
  - task8_26
  - task1_20
  - task8_23
  - task8_29
  - task1_13
  - task3_10
  - task2_14
  - task8_5
  - task4_21
  - task3_1
  update_cycle: 1
tags:
- procedure
- code
- validation
version: 1
---

# Procedure Code Validation

## Pattern Description
You must ensure that any CPT‑style or placeholder codes used in a GET request for `/Procedure` are translated to the appropriate LOINC identifiers before the request is sent. This guard prevents the agent from querying the FHIR server with unknown or non‑standard codes, which would return empty results or cause malformed URLs. The skill is scoped **only to Procedure resources** and activates on GET requests that contain a `code=` query parameter.

## When to Use This Skill
- When the agent issues a `GET /Procedure?...&code=...` request.
- The `code` parameter contains values that are not known LOINC identifiers (e.g., `IMGCT0491`, `IMGIL0001`).
- The request is intended to locate existing imaging studies or other procedures.

## Common Failure Patterns
- `code=IMGCT0491,IMGIL0001` – non‑LOINC CPT codes cause the server to return no matches.
- The agent proceeds with the original request, leading to an empty bundle and a premature FINISH.
- No fallback local filter is applied after the GET, so the missing mapping is never compensated.

## Recommended Patterns
**Pattern 1: Pre‑request code translation**
1. Inspect the request URL for a `code=` query parameter.
2. Split the comma‑separated list of codes.
3. For each code, check a built‑in mapping table (e.g., `{ "IMGCT0491": "LOINC-12345-6", "IMGIL0001": "LOINC-67890-1" }`).
4. If a mapping exists, replace the original code with the LOINC code.
5. Re‑assemble the URL and issue the GET request.

   CORRECT: `GET /Procedure?code=LOINC-12345-6,LOINC-67890-1&patient=S123`
   WRONG:   `GET /Procedure?code=IMGCT0491,IMGIL0001&patient=S123`

**Pattern 2: Fallback local filter**
- If any code has no mapping, still send the request but **after** receiving the bundle apply a client‑side filter that removes entries whose `code.coding.code` does not match any of the original request codes. This prevents false‑positive matches.

**Pattern 3: Output formatting**
- When reporting the found procedure date, return a plain JSON array of ISO‑8601 dates, e.g., `FINISH(["2023-06-14"])`.
- Do **not** embed explanatory text inside the array; that triggers `answer_format_wrong_type` failures.

## Example Application
**Task:** "Find the date of the most recent CT Abdomen procedure for patient S2016972. If the study was performed more than 12 months ago, order a new CT Abdomen with IV contrast."

**Step‑by‑step:**
1. Detect the GET request: `GET /Procedure?code=IMGCT0491,IMGIL0001&patient=S2016972`.
2. Translate codes using the mapping table → `GET /Procedure?code=LOINC-12345-6,LOINC-67890-1&patient=S2016972`.
3. Issue the GET request and parse the bundle for the most recent `performedDateTime`.
4. If the date is older than 12 months, construct a ServiceRequest POST with the CPT code `74177`.
5. Return only the date array: `FINISH(["2023-06-14"])`.

## Success Indicators
- The GET request URL contains only LOINC codes.
- The returned bundle contains at least one entry when a matching procedure exists.
- The FINISH output is a JSON array of strings (dates) with no extra text.

## Failure Indicators
- The request URL still includes unknown CPT codes.
- The FINISH output contains a sentence or object instead of a plain array.
- The agent proceeds to order a new study without correctly checking the date because the prior GET returned empty.
