---
description: Return a sentinel value when a queried Observation bundle is empty, but
  only for GET requests to Observation resources where the task explicitly asks for
  a sentinel fallback. This prevents the skill from interfering with other request
  types (e.g., ServiceRequest creation).
name: missing_observation_sentinel
provenance:
  action: ADD
  epoch: 0
  fixes: 17
  probe_score: 2
  regressions: 1
  triggering_sample_ids: []
  update_cycle: 3
tags: []
version: 1
---

# Missing Observation Sentinel (narrowed)

## Pattern Description
When a **GET** request for an **Observation** returns an empty Bundle (`"total": 0`), return the sentinel value defined by the task (e.g., `-1` for numeric labs or `null` for non‑numeric). This pattern is only applied when the task explicitly mentions a fallback sentinel.

## When to Use This Skill
- The current action is a **GET** request whose URL contains `/Observation` (or a FHIR search that resolves to an Observation Bundle).
- The response Bundle has `"total": 0`.
- The task description contains a sentinel directive such as "return -1 if not available" or "return null when no measurement".
- No further FHIR resources need to be created in this step; the expected output is a single value.

## Guard Clause (to avoid regressions)
```python
if request.method != "GET" or "/Observation" not in request.url:
    # Not an Observation lookup – do not apply sentinel logic
    pass  # continue with normal processing
```

## Recommended Steps
1. **Detect empty Observation bundle**
   ```python
   if response.get('total', 0) == 0:
       # Empty bundle – apply sentinel logic
   ```
2. **Determine sentinel type**
   - Parse the task description for keywords (`"return -1"`, `"return null"`, etc.).
   - Choose the appropriate sentinel (`-1` for numeric, `null` for non‑numeric).
3. **Emit the sentinel**
   ```python
   FINISH([<sentinel>])
   ```
   Ensure the sentinel matches the expected data type (use `enforce_answer_type` if needed).
4. **Normal extraction (when bundle is not empty)**
   ```python
   value = response['entry'][0]['resource']['valueQuantity']['value']
   FINISH([value])
   ```

## Example
**Task:** "What’s the most recent magnesium level of patient S6474456 within the last 24 hours? Return -1 if not available."
```text
GET /fhir/Observation?code=MG&patient=S6474456&date=ge2023-11-12T10:15:00Z
```
- Response Bundle: `{ "total": 0, ... }`
- Sentinel detected → `FINISH([-1])`

## Failure Indicators
- Attempting to access `entry[0]` when `total` is 0.
- Returning an empty array `FINISH([])` or a sentinel of the wrong type.
- Applying the sentinel logic to non‑Observation GETs or to POST/PUT requests (e.g., ServiceRequest creation).

## Success Indicators
- The agent returns exactly the sentinel defined by the task when the Observation bundle is empty.
- No index errors occur.
- The sentinel’s type matches the task’s expectation.

---
*This revised skill adds a strict guard clause to ensure it only runs for GET Observation look‑ups with an explicit sentinel requirement, preventing interference with other workflows such as ServiceRequest ordering.*
