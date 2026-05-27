---
description: Capture resource ID from POST response and return it directly
name: return_created_resource_confirmation
provenance:
  action: MODIFY
  epoch: 4
  fixes: 7
  parent_version: 1
  probe_score: 1
  regressions: 1
  triggering_sample_ids:
  - task10_13
  - task10_10
  - task8_13
  - task8_9
  - task9_3
  update_cycle: 1
tags: []
version: 2
---

# Return Created Resource ID from POST Response

## Pattern Description
You must extract the identifier of a newly created FHIR resource directly from the **POST** response instead of relying on a subsequent GET request.  Many FHIR servers return the full resource (including the `id` field) in the response body of a successful POST.  Using that `id` guarantees a reliable confirmation even when the server’s search endpoint does not immediately expose the new record.

## When to Use This Skill
- The task involves creating an **Observation** or **ServiceRequest** (or any other resource) via a POST request.
- The most recent agent action is a `POST` to a FHIR endpoint and the user has not yet called `FINISH`.
- The POST response body is JSON and contains an `id` field at the top level of the resource.

## Common Failure Patterns
- Agent posts a resource, then performs a GET to verify it; the GET returns an empty bundle, causing `FINISH(["Error: created ... not found"])`.
- The skill never inspects the POST response, so the `id` is never captured.
- The final output is an error string instead of the newly created resource identifier.

## Recommended Patterns
**Pattern 1: Direct ID extraction from POST response**
1. After a `POST` request, capture the raw JSON response returned by the server.
2. Parse the JSON and look for a top‑level field named `id`.
3. If `id` exists, construct the final answer as a JSON list containing the id (e.g., `FINISH(["{id}"])`).
4. **Do not** issue any additional GET requests unless the POST response lacks an `id`.

**Pattern 2: Fallback verification**
1. If the POST response does **not** contain an `id` (or the response is empty), fall back to the original verification strategy: perform a GET search for the resource using patient reference and code, then extract the `id` from the first entry.
2. Return the extracted id in the same list format.

**Pattern 3: Formatting rule**
- Always return a JSON list with a single string element representing the resource id.
- Never embed free‑text explanations or error messages in the list.

## Example Application
**Task:** "Order orthopedic surgery referral for patient S6547257 and include free‑text note."

**Step‑by‑step:**
1. `POST http://localhost:8080/fhir/ServiceRequest` with the ServiceRequest payload.
2. Receive response:
   ```json
   {
     "resourceType": "ServiceRequest",
     "id": "sr-9876",
     "status": "active",
     ...
   }
   ```
3. Extract `id = "sr-9876"`.
4. `FINISH(["sr-9876"])`.

**Correct output:** `FINISH(["sr-9876"])`
**Incorrect output:** `FINISH(["Error: created ServiceRequest not found"])`

## Success Indicators
- The final `FINISH` call returns a list containing the newly created resource id.
- No error messages are present in the output.
- The agent does not perform unnecessary GET requests after a successful POST.

## Failure Indicators
- `FINISH` returns a string starting with "Error:" instead of a list.
- The agent issues a GET verification that returns an empty bundle, leading to the error.
- The POST response is ignored and the id is never extracted.
