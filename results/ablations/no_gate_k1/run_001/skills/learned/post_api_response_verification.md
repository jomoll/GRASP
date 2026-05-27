---
description: Ensures FINISH is only called after inspecting API responses
name: post_api_response_verification
provenance:
  action: ADD
  epoch: 0
  no_gate: true
  triggering_sample_ids:
  - task4_7
  - task4_6
  - task1_20
  - task9_5
  - task9_1
  - task9_9
  - task9_22
  - task10_8
  - task1_13
  - task2_14
  update_cycle: 1
tags: []
version: 1
---

# Post-API Response Verification Before FINISH

## Pattern Description
You must never finalize a task (call `FINISH`) until you have inspected the data returned by any API request you issued. This pattern forces a clear separation between *request* and *decision*: first issue the GET/POST, then wait for the user‑provided response payload, extract the needed fields, and only then construct the final answer or follow‑up actions. It prevents premature answers based on assumptions or missing data.

## When to Use This Skill
- When a task asks for information that must be retrieved via a `GET` call (e.g., patient MRN, lab value, medication list).
- When a task requires you to act on the result of a `GET` (e.g., order a medication only if a lab is low).
- Immediately after any `GET` or `POST` you issue, before calling `FINISH`.

## Common Failure Patterns
- `GET …` followed directly by `FINISH("Patient not found")` without waiting for the response payload.
- Using placeholder values like `"[value]"` or empty arrays before the response is parsed.
- Issuing a `POST` and then calling `FINISH` before confirming the POST succeeded (no verification step).

## Recommended Patterns
**Pattern 1: Core verification workflow**
1. Issue the API request (e.g., `GET http://.../Patient?...`).
2. **Pause** – do not call `FINISH`. Wait for the user to supply the JSON response.
3. Parse the response:
   - For a `Bundle`, check `total` or iterate `entry`.
   - Extract the needed field (e.g., `entry[0].resource.id` for MRN, `valueQuantity.value` for labs).
4. Apply any business logic (e.g., if `total == 0` → "Patient not found").
5. Construct the final output **and only then** call `FINISH`.

**Pattern 2: POST verification fallback**
1. After a `POST`, wait for the system note or user confirmation that the resource was stored.
2. Verify the returned resource contains the expected `resourceType` and required fields.
3. If verification fails, retry or raise an error before `FINISH`.

**Pattern 3: Formatting rule**
- Always return a plain string for scalar answers (e.g., `FINISH("Patient not found")`).
- For list‑type answers, return a JSON array (e.g., `FINISH(["Referral created"])`).

## Example Application
**Task:** "What’s the MRN of the patient with name Christopher Cruz and DOB of 1940-08-28? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?name=Christopher%20Cruz&birthdate=1940-08-28`
2. *Wait* for the user to provide the response bundle.
3. Parse the bundle:
   - If `total == 0` → set answer = "Patient not found".
   - Else extract `entry[0].resource.id` as the MRN.
4. `FINISH(answer)` – only now.

**Correct output:** `FINISH("Patient not found")`
**Incorrect output:** `FINISH("Patient not found")` *immediately after the GET* (no response parsed).

## Success Indicators
- The agent’s action log shows a `GET` (or `POST`) followed by a user‑provided response before any `FINISH`.
- The final `FINISH` payload is derived from fields that were explicitly extracted from the response.
- No placeholder or hard‑coded answers appear without a preceding verification step.

## Failure Indicators
- `FINISH` appears directly after an API request with no intervening response.
- The agent uses default strings like "Patient not found" without checking `total` in the returned bundle.
- POST actions are followed by `FINISH` without a system note confirming successful storage.
