---
description: Fetch the most recent lab Observation for a patient, apply a time window,
  and return a raw numeric value or -1.
name: recent_lab_observation_query
provenance:
  action: ADD
  epoch: 1
  fixes: 5
  probe_score: 6
  regressions: 0
  triggering_sample_ids:
  - task10_27
  - task10_12
  - task9_1
  - task10_18
  - task1_15
  - task4_10
  - task9_20
  - task9_5
  - task10_15
  - task9_3
  update_cycle: 1
tags:
- lab
- observation
- retrieval
- numeric_output
version: 1
---

# Recent Lab Observation Query

## Pattern Description
You must retrieve a single numeric result for any lab Observation when a task asks for the "most recent" value of a specific code (e.g., MG, K, A1C) within a defined time window (commonly 24 hours). The skill isolates the query, filters by `effectiveDateTime`, selects the newest entry, extracts the pure number, and formats the answer as a raw scalar (or `-1` if no qualifying result exists). This pattern prevents the agent from stalling on reasoning alone and ensures consistent numeric output for downstream decision logic.

## When to Use This Skill
- The task description includes phrases like "most recent *level*", "last *value*", or "within the last X hours" for a lab code.
- The required answer is a single number (or `-1` when unavailable), not a structured object or free‑text sentence.
- No prior GET request for the Observation has been made in the current execution trace.

## Common Failure Patterns
- Agent provides reasoning but never issues a `GET /Observation` request.
- Agent returns a formatted sentence or array instead of a raw number.
- Agent extracts `valueQuantity.unit` together with the value, producing a string like `"3.5 mmol/L"`.
- Agent returns `null` or an empty array when a valid observation exists.

## Recommended Patterns
**Pattern 1: Core retrieval strategy**
1. Identify the lab code (`code`) and patient identifier (`patient`) from the task.
2. Construct the GET URL:
   ```
   GET {api_base}/Observation?code={code}&patient={patient}
   ```
3. When a time window is specified (e.g., "last 24 hours"), add a date filter using `date` (or `effectiveDateTime` if the server supports it):
   ```
   GET ...&date=gt{window_start_iso}
   ```
   where `window_start_iso = current_time - window_duration`.
4. From the returned Bundle, locate the entry with the greatest `effectiveDateTime` that falls inside the window.
5. Extract the numeric value:
   - Prefer `valueQuantity.value` (number).
   - If only `valueString` is present, attempt to parse a leading number.
6. If a qualifying observation is found, `FINISH([value])`.
   If none, `FINISH([-1])`.

**Pattern 2: Fallback when primary field missing**
- If `valueQuantity` is absent, look for `valueString` and use a regex to capture the first numeric token.
- If parsing fails, treat as no result and return `-1`.

**Pattern 3: Output formatting rule**
- Always output a JSON array containing a single number (or `-1`).
- Do **not** include units, text, or additional metadata.

## Example Application
**Task:** "What’s the most recent magnesium level of the patient S3213957 within last 24 hours?"

**Step‑by‑step:**
1. Determine `code=MG` and `patient=S3213957`.
2. Compute window start: `2023-11-12T10:15:00+00:00` (current time minus 24 h).
3. Issue:
   ```
   GET http://localhost:8080/fhir/Observation?code=MG&patient=S3213957&date=gt2023-11-12T10:15:00+00:00
   ```
4. Parse the Bundle, pick the entry with the latest `effectiveDateTime` inside the window.
5. Extract `valueQuantity.value` → e.g., `2.3`.
6. Return:
   ```
   FINISH([2.3])
   ```
   If no entry meets the criteria, return `FINISH([-1])`.

## Success Indicators
- A `GET /Observation` request appears in the trace before any `FINISH`.
- The final `FINISH` payload is a JSON array with a single numeric element (or `-1`).
- The numeric value matches the `valueQuantity.value` of the most recent qualifying Observation.

## Failure Indicators
- No GET request for Observation is made despite the task asking for a lab value.
- The `FINISH` output contains a string, an object, or extra text.
- The returned number does not correspond to the most recent observation within the requested window.
- The agent returns `FINISH([])` or omits the `-1` sentinel when no data exists.
