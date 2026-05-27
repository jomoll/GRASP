---
description: Emit a structured placeholder when a patient search returns no results
name: patient_search_placeholder
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 1
  triggering_sample_ids:
  - task9_22
  - task9_1
  - task2_1
  - task9_5
  - task1_20
  - task9_9
  - task10_10
  - task5_3
  - task1_10
  - task9_8
  update_cycle: 1
tags: []
version: 2
---

# Patient Search Placeholder

## Pattern Description
You must provide a reusable way to handle empty patient search results. When a `GET /Patient` query returns a FHIR `Bundle` with `total: 0`, the agent should **not** emit a literal string such as "Patient not found". Instead, emit a structured placeholder that downstream skills can recognise and act upon. This keeps the response machine‑readable and avoids hard‑coding answer text in the search layer.

## When to Use This Skill
- When a task asks for a patient identifier (MRN, name, DOB, etc.) and the agent performs a `GET {base}/Patient?...` request.
- The response is a `Bundle` where `"total": 0` (no matching Patient resources).
- The task expects an answer about the patient (e.g., "What’s the MRN of the patient …?")

## Common Failure Patterns
- Agent calls `FINISH(["Patient not found"])` – a plain string is returned.
- Agent calls `FINISH([])` – an empty array is returned, losing the context that a patient was searched for.
- Agent includes the placeholder inside a string (e.g., `"{\"mrn\": null}"`).

## Recommended Patterns
**Pattern 1: Detect empty search and build placeholder**
1. Parse the JSON response from the `GET /Patient` call.
2. Inspect the field `bundle.total`.
3. If `total == 0`:
   - Construct a JSON object:
     ```json
     {
       "mrn": null,
       "status": "not_found",
       "detail": "Patient not found for the given search criteria"
     }
     ```
   - Call `FINISH([<object>])` – the placeholder must be the sole element of the result array.
4. If `total > 0`, proceed with normal patient extraction logic (e.g., pull `identifier` from the first entry).

**Pattern 2: Downstream handling of the placeholder**
- Any later skill that expects a patient identifier should first check whether the received value is an object with `status == "not_found"`.
- If so, translate it to the user‑visible string required by the instruction (e.g., `FINISH(["Patient not found"])`) **after** all other processing steps have completed.

## Example Application
**Task:** "What’s the MRN of the patient with name Christopher Cruz and DOB of 1940-08-28? If the patient does not exist, the answer should be \"Patient not found\""

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Patient?name=Christopher%20Cruz&birthdate=1940-08-28`.
2. Receive a Bundle with `"total": 0`.
3. Apply Pattern 1 → build placeholder object as shown above.
4. Call `FINISH([{"mrn":null,"status":"not_found","detail":"Patient not found for the given search criteria"}])`.
5. A downstream formatting skill sees the placeholder and emits the final user‑visible string `FINISH(["Patient not found"])`.

**Correct output:** `FINISH([{"mrn":null,"status":"not_found","detail":"Patient not found for the given search criteria"}])`
**Incorrect output:** `FINISH(["Patient not found"])` (plain string) or `FINISH([])` (empty array).

## Success Indicators
- The agent calls `FINISH` with an array containing a single JSON object that has `status: "not_found"`.
- No plain‑text "Patient not found" is emitted directly from the search step.

## Failure Indicators
- `FINISH` receives a plain string or an empty array when the patient search returned zero results.
- The placeholder object is malformed (missing `status` field) or wrapped inside a string.
