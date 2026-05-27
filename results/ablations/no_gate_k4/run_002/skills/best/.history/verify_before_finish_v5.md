---
description: Enforce strict FINISH payload format and split combined value/date strings
name: verify_before_finish
provenance:
  action: MODIFY
  epoch: 2
  no_gate: true
  parent_version: 4
  triggering_sample_ids:
  - task10_20
  - task10_27
  - task9_28
  - task8_29
  - task9_27
  - task5_17
  - task9_8
  - task8_23
  - task5_16
  - task9_11
  update_cycle: 0
tags: []
version: 5
---

# verify_before_finish

## Pattern Description
You must guarantee that every `FINISH` call receives a **JSON array** whose elements are *bare* scalars (numbers or plain strings).  No element may contain extra explanatory text, combined value‑date phrases, or any formatting beyond the raw data required by the task.  If a task asks for both a lab value and its collection date, they must appear as **separate list items** (e.g., `["5.4%", "2023-11-02"]`).  This prevents downstream type‑mismatch errors and ensures downstream logic (e.g., conditional ordering) can reliably parse the response.

## When to Use This Skill
- After extracting any answer that will be returned via `FINISH`.
- When the task description requests multiple pieces of information (value + date, value + unit, etc.).
- Whenever the agent is about to call `FINISH` with a list that may contain combined strings such as `"5.4% on 2023-11-02"` or free‑text sentences.

## Common Failure Patterns
- `FINISH(["5.4% on 2023-11-02"])` – value and date concatenated.
- `FINISH(["Blood pressure recorded"])` when the task expects a numeric result.
- Returning a plain scalar without wrapping: `FINISH("5.4%")`.
- Including units or extra words inside the list element: `FINISH(["5.4 percent"]`).
- Supplying a date without ISO‑8601 format (e.g., `"2023-11-02"` vs `"2023-11-02T00:00:00+00:00"`).

## Recommended Patterns
**Pattern 1: Validate and split before FINISH**
1. Inspect the data you have extracted.
2. If the task asks for *both* a value and a date, store them in two separate variables.
3. Ensure each variable is a plain scalar (no surrounding text).
4. Build the final payload as a JSON array of those scalars.

   ```json
   // Correct payload for HbA1C request
   FINISH(["5.4%", "2023-11-02T00:00:00+00:00"])
   ```

   ```json
   // WRONG – combined string
   FINISH(["5.4% on 2023-11-02"])
   ```

**Pattern 2: Automatic wrapping for single‑item answers**
- If you have only one scalar (e.g., a patient MRN), wrap it in an array before calling `FINISH`.
  ```json
  FINISH(["S3213957"])   // correct
  FINISH("S3213957")     // WRONG
  ```

**Pattern 3: Date Normalization**
- Convert plain dates (`YYYY‑MM‑DD`) to full ISO‑8601 timestamps before placing them in the array.
  ```json
  // Input date string
  date_str = "2023-11-02"
  iso_date = date_str + "T00:00:00+00:00"
  FINISH([value, iso_date])
  ```

## Example Application
**Task:** "What’s the last HbA1C value for patient S0658561 and when was it recorded?"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=A1C&patient=S0658561`
2. From the Bundle, extract `valueQuantity.value` (e.g., `5.4`) and `valueQuantity.unit` (e.g., `%`).
3. Extract `effectiveDateTime` (e.g., `2023-11-02`).
4. Build the scalar strings:
   - `value_str = "5.4%"`
   - `date_iso = "2023-11-02T00:00:00+00:00"`
5. Call `FINISH([value_str, date_iso])`.

**Correct output:** `FINISH(["5.4%", "2023-11-02T00:00:00+00:00"])`
**Wrong output:** `FINISH(["5.4% on 2023-11-02"])`

## Success Indicators
- `FINISH` is always called with a JSON array.
- Each array element is a plain scalar (no spaces, no extra words).
- Dates appear in full ISO‑8601 format.
- Conditional‑ordering skills receive clean, parsable inputs.

## Failure Indicators
- `FINISH` receives a single string instead of an array.
- An array element contains combined information (e.g., value + date together).
- Dates are missing time‑zone information or are not ISO‑8601.
- Downstream skills report type‑mismatch errors (e.g., `answer_format_wrong_type`).
