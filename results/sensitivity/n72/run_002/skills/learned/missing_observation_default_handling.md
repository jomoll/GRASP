---
description: Return sentinel values and suppress orders when a numeric Observation
  query returns an empty bundle
name: missing_observation_default_handling
provenance:
  action: ADD
  epoch: 4
  fixes: 7
  probe_score: 3
  regressions: 3
  triggering_sample_ids:
  - task9_5
  - task10_12
  - task4_11
  - task9_6
  - task9_14
  - task9_1
  - task9_27
  - task4_15
  update_cycle: 1
tags: []
version: 1
---

# Missing Observation Default Handling for Numeric Labs

## Pattern Description
You must gracefully handle the case where a GET request for a numeric Observation (e.g., magnesium, potassium, calcium) returns an empty Bundle. Instead of proceeding to a FINISH with an empty array or issuing an unnecessary ServiceRequest, emit a predefined sentinel value (‑1 for "no recent measurement") and skip any downstream ordering logic that depends on a valid result. This pattern keeps the agent from treating "no data" as a successful answer and prevents spurious orders.

## When to Use This Skill
- When the task asks for the most recent value of a lab/electrolyte within a time window (e.g., "most recent magnesium level within last 24 hours").
- When the GET request URL is of the form `.../Observation?code=<CODE>&patient=<MRN>` (optionally with a `date=` filter) and the returned Bundle has `"total": 0`.
- When the expected answer schema is a single numeric value (or a numeric‑date pair) rather than a free‑text string.
- When the task includes conditional ordering based on the numeric result (e.g., order IV magnesium if the level is low).

## Common Failure Patterns
- Agent receives an empty Observation Bundle and immediately calls `FINISH([])`.
- Agent proceeds to place a ServiceRequest even though no measurement exists.
- Agent returns the wrong sentinel (e.g., `null` or an empty array) instead of `-1`.
- The skill does not fire because it only matches lab result answer schemas (HbA1c) and ignores electrolyte queries.

## Recommended Patterns
**Pattern 1: Detect empty Observation bundle**
1. After a GET request, inspect the JSON field `total` in the Bundle response.
2. If `total == 0` **and** the task expects a numeric value, set `result = -1`.
3. Skip any conditional ordering that depends on a valid numeric result.
4. Immediately `FINISH([result])` (or `FINISH([])` only if the task explicitly says "do nothing").

```json
// Correct handling of empty magnesium query
GET http://.../Observation?code=MG&patient=S1234567
// response: {"resourceType":"Bundle","total":0,...}
// Agent action:
result = -1
FINISH([result])
```

**Pattern 2: Suppress unnecessary ServiceRequest**
1. If the task includes "If the lab value result date is greater than 1 year old, order a new test" **or** "If low, then order replacement", evaluate the condition **only** when `result != -1`.
2. When `result == -1`, do **not** issue a POST to `/ServiceRequest`.
3. Optionally log a note: `"No recent measurement found; no order placed."`

```json
// Incorrect: ordering despite missing result
POST .../ServiceRequest { ... }
FINISH([])

// Correct: skip POST when result == -1
// No POST performed
FINISH([ -1 ])
```

**Pattern 3: Formatting the final answer**
- For tasks that require a numeric answer, always return a JSON array with a single number: `FINISH([value])`.
- Do **not** wrap the number in a string or include additional text.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3213957 within last 24 hours?"

**Step‑by‑step:**
1. Issue `GET http://localhost:8080/fhir/Observation?code=MG&patient=S3213957`.
2. Receive a Bundle with `"total": 0`.
3. Apply Pattern 1 → `result = -1`.
4. No ordering logic applies (task only asks for the value).
5. Emit `FINISH([-1])`.

**Correct output:** `FINISH([-1])`
**Wrong output:** `FINISH([])` or a POST request for a replacement.

## Success Indicators
- The agent returns `FINISH([-1])` (or the appropriate sentinel) for any empty Observation query.
- No ServiceRequest POST is made when the result is `-1`.
- Logs (if any) show the check `total == 0` was performed.

## Failure Indicators
- The agent calls `FINISH([])` after an empty Observation.
- The agent issues a ServiceRequest despite `total == 0`.
- The final output contains a string or extra text instead of a numeric array.

---
*Tags:* ["observation", "missing", "default", "numeric", "electrolyte"]
