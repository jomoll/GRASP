---
description: Emit a structured placeholder when a patient search returns no results
name: patient_search_placeholder
provenance:
  action: ADD
  epoch: 1
  no_gate: true
  triggering_sample_ids:
  - task9_28
  - task10_15
  - task10_20
  - task10_24
  - task5_17
  - task9_6
  - task1_16
  - task5_7
  - task9_27
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Patient Search Placeholder

## Pattern Description
When a FHIR `Patient` search returns an empty `Bundle`, the agent must not proceed as if a patient exists. Instead, it should emit a standardized placeholder indicating that the patient was not found. This placeholder can be used by downstream logic to skip further patient‑dependent actions.

## When to Use This Skill
- After a `GET /Patient` request (by name, birthdate, identifier, or any combination) that returns a JSON `Bundle` with `"total": 0`.
- When the task explicitly asks for an MRN or any patient‑specific answer and specifies a fallback string such as "Patient not found".

## Common Failure Patterns
- Ignoring the `total` field and attempting to extract `identifier` or other fields from an empty bundle.
- Returning a free‑form narrative instead of the exact placeholder required by the task.
- Proceeding to create orders or other resources when the patient does not exist.

## Recommended Patterns
**Pattern 1: Detect empty search result**
1. Parse the response JSON.
2. Verify `resourceType == "Bundle"`.
3. Check `total == 0`.
4. Set a flag `patient_not_found = true`.

**Pattern 2: Emit standardized placeholder**
- If `patient_not_found` is true, immediately call:
  ```
  FINISH(["Patient not found"])
  ```
- Do **not** issue any further `GET` or `POST` calls that depend on a patient identifier.

**Pattern 3: Guard downstream steps**
- Before any step that uses a patient reference, test `patient_not_found`.
- If true, skip the step and propagate the placeholder.

## Example Application
**Task:** "What’s the MRN of the patient with name Debra Dunn and DOB of 1969-05-12? If the patient does not exist, the answer should be \"Patient not found\"."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?name=Debra%20Dunn&birthdate=1969-05-12`
2. Response Bundle contains `"total": 0`.
3. Apply Pattern 1 → `patient_not_found = true`.
4. Apply Pattern 2 → `FINISH(["Patient not found"])`.
5. No further API calls are made.

## Success Indicators
- The agent calls `FINISH` with exactly `["Patient not found"]` **only** after confirming `total == 0`.
- No subsequent patient‑dependent API calls are issued.

## Failure Indicators
- The agent attempts to read `identifier` or other fields from an empty bundle.
- The final output is a narrative string or missing the required placeholder.
- Additional GET/POST requests are made despite the patient being absent.
