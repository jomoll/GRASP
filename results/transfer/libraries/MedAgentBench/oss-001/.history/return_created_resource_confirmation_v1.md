---
description: Return the ID of a newly created Observation or ServiceRequest instead
  of an empty answer
name: return_created_resource_confirmation
provenance:
  action: ADD
  epoch: 3
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - task9_9
  - task3_3
  - task1_6
  - task8_23
  - task8_3
  - task10_16
  - task8_14
  - task9_3
  - task9_14
  - task5_7
  update_cycle: 1
tags:
- resource_creation
- confirmation
- observation
- servicerequest
version: 1
---

# Return Created Resource Confirmation

## Pattern Description
You must ensure that whenever you create a FHIR resource (e.g., `Observation` or `ServiceRequest`) you return a concrete confirmation that the resource exists.  The default behaviour of many tasks is to call `FINISH([])` or to return a generic string such as `"Referral placed"`.  This provides no verifiable answer to the user and leads to the *answer_missing_value* failure mode.  The skill forces a follow‑up read of the just‑created resource and extracts its identifier (or the whole resource) for the final answer.

## When to Use This Skill
- When the task description explicitly asks you to *record* a measurement or *order* a referral/service request.
- After you have issued a `POST` to `/Observation` or `/ServiceRequest` and the user response is only "POST request accepted and executed successfully" (no body).
- When you are about to call `FINISH` with an empty list `[]` or with a non‑resource placeholder.

## Common Failure Patterns
- `FINISH([])` immediately after a successful `POST`.
- `FINISH(["Observation recorded"])` or `FINISH(["Referral placed"])` – the answer does not contain the created resource ID.
- No subsequent `GET` request to verify that the resource was stored.

## Recommended Patterns
**Pattern 1: Verify creation and fetch identifier**
1. After a successful `POST`, immediately issue a `GET` for the same resource type.
   - For an `Observation`: `GET {base}/Observation?patient=Patient/<MRN>&code=<code>&_sort=-_lastUpdated&_count=1`
   - For a `ServiceRequest`: `GET {base}/ServiceRequest?subject=Patient/<MRN>&code=<code>&_sort=-_lastUpdated&_count=1`
2. Inspect the returned bundle. If `total == 1`, extract the resource's `id` field (e.g., `entry[0].resource.id`).
3. Return the identifier (or the full resource) in the final answer:
   - `FINISH(["Observation", "<id>"])`  or  `FINISH(["ServiceRequest", "<id>"])`
   - If you prefer to return the whole resource, use `FINISH([entry[0].resource])`.

**Pattern 2: Fallback when the GET returns no results**
- If the verification `GET` returns `total == 0`, retry the `GET` after a short pause (e.g., 1 second) up to two times.
- If still empty, fall back to returning a clear error message: `FINISH(["Error: created resource not found"])`.

**Pattern 3: Formatting the final output**
- Always wrap the answer in a JSON‑compatible list as required by the platform.
- Do **not** embed free‑text explanations; only return the identifier or the resource object.

## Example Application
**Task:** "I just measured the blood pressure for patient S6192632, and it is \"118/77 mmHg\". Help me record it."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S6192632`
2. `POST http://localhost:8080/fhir/Observation` with the BP payload.
3. *Immediately after* the POST, issue:
   ```
   GET http://localhost:8080/fhir/Observation?patient=Patient/S6192632&code=BP&_sort=-_lastUpdated&_count=1
   ```
4. The response bundle contains:
   ```json
   { "entry": [{ "resource": { "id": "440306", ... } }] }
   ```
5. Extract `440306` and finish:
   ```
   FINISH(["Observation", "440306"])
   ```

**Correct output:** `FINISH(["Observation", "440306"])`
**Wrong output:** `FINISH([])` or `FINISH(["Observation recorded"])`

## Success Indicators
- The final `FINISH` payload contains a two‑element list where the second element is a non‑empty string matching the `id` of the created resource.
- The verification `GET` returns `total == 1` before `FINISH` is called.

## Failure Indicators
- `FINISH` is called with an empty list or a generic message after a `POST`.
- No verification `GET` is performed after a creation request.
- The extracted `id` is missing or empty.
