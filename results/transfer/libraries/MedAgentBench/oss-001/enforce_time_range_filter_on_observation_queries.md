---
description: "Add a 24\u2011hour date filter to Observation searches **only** when\
  \ the task explicitly asks for a recent value. The skill now activates exclusively\
  \ for GET requests targeting the Observation resource that contain a `code=` parameter\
  \ (and a patient/subject identifier) **and** when the task description includes\
  \ a clear recent\u2011time phrase (e.g., \"within last 24 hours\", \"in the past\
  \ 24 hours\", \"last day\", \"recent\"). This guard prevents the rule from interfering\
  \ with unrelated requests such as Patient look\u2011ups or ServiceRequest creations,\
  \ eliminating the regression observed in non\u2011Observation tasks."
name: enforce_time_range_filter_on_observation_queries
provenance:
  action: ADD
  epoch: 2
  fixes: 6
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - task8_14
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task8_13
  - task5_16
  - task9_11
  - task9_14
  update_cycle: 0
tags: []
version: 1
---

# Enforce Recent Time Window Filter on Observation Queries (Narrowed Scope)

## Trigger Conditions
1. **Resource Check** – The outgoing request URL must contain `/Observation` (case‑insensitive).
2. **Required Parameters** – The query must include a `code=` parameter **and** either a `patient=` or `subject=` parameter.
3. **Task Intent** – The current task description (or any sub‑instruction) must contain one of the following exact phrases (case‑insensitive):
   - `within last 24 hours`
   - `in the past 24 hours`
   - `last day`
   - `recent`
   > The phrase must be present; generic time words like "today" or "now" do **not** trigger the rule.
4. **Context Timestamp** – The task must provide a `context` field with an ISO‑8601 timestamp named `now`. If `now` is missing, the rule aborts and the original query is sent unchanged.

## Processing Steps (executed only when all triggers are satisfied)
1. **Parse the reference time** `now` from `task.context.now`.
2. **Compute the 24‑hour window**:
   - `start = now - 24h` (ISO‑8601)
   - `end   = now`
3. **Construct the date filter** using the FHIR `date` search parameter with `ge` (greater‑or‑equal) and `le` (less‑or‑equal) operators:
   ```
   date=ge{START}&date=le{END}
   ```
4. **Append the filter** to the original Observation query, preserving any existing parameters.
5. **Send the modified GET request**.
6. **Handle the response**:
   - If `total == 0`, return the task‑specified placeholder (e.g., `-1` or a custom message) **without** falling back to an unfiltered query.
   - Otherwise, process the observations as the task requires.

## Example (triggered)
Task snippet: "Check patient S12345's potassium level **within last 24 hours**."

- `now` from context: `2023-11-13T10:15:00+00:00`
- Computed window: `start = 2023-11-12T10:15:00+00:00`
- Original request:
  ```
  GET http://localhost:8080/fhir/Observation?code=K&patient=S12345
  ```
- Modified request sent by the skill:
  ```
  GET http://localhost:8080/fhir/Observation?code=K&patient=S12345&date=ge2023-11-12T10:15:00+00:00&date=le2023-11-13T10:15:00+00:00
  ```

## Non‑trigger Example (regression case preserved)
Task: "Order orthopedic surgery referral for patient S6549951."

- No recent‑time phrase → **skill does not activate**.
- The original GET `Patient?identifier=S6549951` and subsequent ServiceRequest POST are sent unchanged, preventing the earlier regression.

## Success Indicators
- The printed GET URL contains both `date=ge…` and `date=le…` **only** for Observation queries meeting the trigger conditions.
- Bundles returned reflect the 24‑hour window.
- Non‑Observation requests (e.g., Patient, ServiceRequest) remain untouched.

## Failure Indicators
- Observation GET URLs lacking the date filter despite a recent‑time phrase.
- Date filter added to non‑Observation resources.
- Incorrect operator or timestamp used.

---
*This revised rule keeps the original intent of preventing false‑negative recent Observation results while adding strict guards to avoid unintended side effects on unrelated API calls.*
