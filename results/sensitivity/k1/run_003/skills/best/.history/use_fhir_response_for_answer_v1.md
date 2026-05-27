---
description: Force extraction of required data from a FHIR GET response before issuing
  FINISH.
name: use_fhir_response_for_answer
provenance:
  action: ADD
  epoch: 0
  fixes: 11
  probe_score: 11
  regressions: 3
  triggering_sample_ids:
  - task9_5
  - task2_30
  - task8_23
  - task9_8
  - task2_16
  - task1_11
  - task2_14
  - task9_14
  - task10_20
  - task10_8
  update_cycle: 0
tags: []
version: 1
---

# Use FHIR Response for Answer

## Pattern Description
You must never answer a clinical question based on assumptions or hard‑coded values. After issuing a `GET` request to the FHIR server, you are required to parse the returned JSON bundle, locate the exact element that satisfies the task, and use that extracted value in the final `FINISH` output. This pattern applies to any task that asks for a patient attribute (age, MRN, etc.) or a lab/observation value (potassium, magnesium, HbA1c, etc.).

## When to Use This Skill
- When a task asks for a numeric or textual value that should come from a FHIR `Patient` or `Observation` resource.
- When you have just performed a `GET` request and the next step is to provide an answer or make a decision based on that data.
- When the task includes a threshold check (e.g., "if potassium < 3.5 mmol/L then order…").

## Common Failure Patterns
- Returning a hard‑coded number (e.g., `FINISH(["80"])`) without inspecting the `Bundle`.
- Using the request URL or parameter values as the answer instead of the resource content.
- Ignoring the `entry` array and extracting from the wrong field (e.g., using `effectiveDateTime` instead of `valueQuantity`).
- Answering with a placeholder string like `"No data"` when the bundle actually contains a result.

## Recommended Patterns
**Pattern 1: Verify GET succeeded and locate the first entry**
1. After a `GET`, check that the response JSON has `resourceType == "Bundle"` and `total > 0`.
2. Access the first entry via `response["entry"][0]["resource"]`.
3. If the bundle is empty, treat the data as unavailable and follow the task’s "no data" branch.

**Pattern 2: Extract a Patient attribute (age, MRN, etc.)**
- For age: locate `resource["birthDate"]`, parse the ISO date, compute years difference from the current task context time.
- For MRN: locate `resource["identifier"]` array, find the identifier where `type.coding.code == "MR"` (or use the first identifier) and read its `value`.
- Example (correct):
  ```json
  {"resourceType":"Patient", "birthDate":"1950-04-12"}
  ```
  → age = floor((now - 1950‑04‑12) / 365.25).

**Pattern 3: Extract an Observation value**
- Identify the observation code you queried (e.g., `code=K` for potassium).
- Preferred field: `resource["valueQuantity"]["value"]` (numeric) and optionally `unit`.
- If the observation uses `valueString`, extract that string and, if needed, parse the numeric part.
- Example (correct):
  ```json
  {"resourceType":"Observation","valueQuantity":{"value":3.8,"unit":"mmol/L"}}
  ```
  → potassium = 3.8.

**Pattern 4: Threshold decision**
1. After extraction, compare the numeric value to the task‑specified threshold.
2. If the value is below the threshold, proceed with the ordering steps defined in the task.
3. If the value meets or exceeds the threshold, **do not** place an order and finish with a statement that no replacement is needed.

**Pattern 5: Formatting the FINISH output**
- Return only the required primitive(s) in the exact type expected by the task (e.g., a number, a string, or a list of numbers).
- Do **not** embed explanatory text unless the task explicitly asks for it.
- Example (correct): `FINISH([3.8])` for a numeric answer, or `FINISH(["No potassium replacement needed"])` when only a message is required.

## Example Application
**Task:** "Check patient S1796597's most recent potassium level. If low (<3.5 mmol/L), order replacement potassium. Also schedule a serum potassium draw tomorrow at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597`
2. Verify response bundle has entries.
3. Extract the most recent observation (assume entries are sorted newest first) → `obs = response["entry"][0]["resource"]`.
4. Pull `potassium = obs["valueQuantity"]["value"]`.
5. Compare: `if potassium < 3.5:`
   - POST a `MedicationRequest` for replacement potassium (using the NDC supplied in the task context).
   - POST a `ServiceRequest` for a serum potassium draw with `occurrenceDateTime` set to tomorrow 08:00.
   - `FINISH(["Replacement ordered and draw scheduled"])`.
6. Else:
   - `FINISH(["No potassium replacement needed; latest level {potassium} mmol/L is above threshold."])`.

## Success Indicators
- The agent extracts a numeric value from `valueQuantity.value` (or parses `valueString`) before any `FINISH`.
- The agent respects the threshold logic and only creates orders when the condition is met.
- The final `FINISH` payload matches the type expected by the task (number vs. string list).

## Failure Indicators
- `FINISH` is called immediately after a `GET` without any parsing of the response.
- The answer contains hard‑coded numbers that do not appear in the received bundle.
- Orders are placed without confirming the lab result is below the required threshold.
- The output includes extra explanatory text when the task expects a raw value.
