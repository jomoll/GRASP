---
description: Ensure FINISH output for order actions is a bare empty list, not a generic
  string
name: order_response_formatting
provenance:
  action: ADD
  epoch: 2
  fixes: 14
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - task10_24
  - task9_22
  - task9_28
  - task9_1
  - task5_17
  - task10_20
  - task4_21
  - task9_11
  - task9_20
  - task9_8
  update_cycle: 0
tags: []
version: 1
---

# Order Response Formatting

## Pattern Description
You must control the final response format for any task that creates or updates FHIR resources (MedicationRequest, ServiceRequest, Observation, etc.). The agent’s job is to perform the required POST/PUT calls and then signal completion with a minimal FINISH payload. Extra human‑readable sentences or status strings (e.g., "Completed", "Referral created successfully") cause downstream failures because the evaluation expects a JSON list with either no elements or only the required data values.

## When to Use This Skill
- After you have successfully POSTed a FHIR resource as part of the task.
- The instruction does **not** ask you to return a narrative summary, only to “order” or “record” something.
- The expected FINISH payload is an empty list `[]` (or a list containing only the numeric answer when the task asks for a value).

## Common Failure Patterns
- `FINISH(["Completed"])` – a generic string instead of an empty list.
- `FINISH(["Referral created successfully"])` – extra confirmation text.
- `FINISH(["No magnesium replacement needed. Current magnesium level is 2.1 mg/dL."])` – combines status and data in a single string.
- Returning a list of strings when the task expects a bare number (e.g., `FINISH(["3.8"])`).

## Recommended Patterns
**Pattern 1: Primary FINISH rule for order actions**
1. Perform the required GET(s) to locate the patient and any prerequisite data.
2. Execute the POST/PUT request(s) to create the order.
3. **Immediately after the POST succeeds, call** `FINISH([])` **with no arguments**.
   - CORRECT: `FINISH([])`
   - WRONG: `FINISH(["Order placed"])`

**Pattern 2: FINISH rule when a numeric answer is required**
1. Extract the numeric value using the `lab_observation_numeric_extraction` skill.
2. Return the bare number inside a list, **without any surrounding text**.
   - CORRECT: `FINISH([2.1])`
   - WRONG: `FINISH(["2.1 mg/dL"])` or `FINISH(["Result: 2.1"])`

**Pattern 3: Conditional ordering with no‑order outcome**
1. If the lab value is missing or not low enough to trigger an order, do **not** create any POST.
2. Signal completion with an empty list.
   - CORRECT: `FINISH([])`
   - WRONG: `FINISH(["No replacement ordered"])`

## Example Application
**Task:** "Check patient S0581164's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium. If no magnesium level has been recorded, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Patient?identifier=S0581164`
2. `GET http://localhost:8080/fhir/Observation?code=MG&patient=Patient/S0581164&date=ge2023-11-12T10:15:00Z`
3. Extract the most recent `valueQuantity.value` (e.g., `2.1`).
4. Compare to the low‑threshold (e.g., `<1.5`).
5. If low, `POST` a MedicationRequest for IV magnesium.
6. **FINISH([])** – no extra text.
7. If no observation or value not low, **FINISH([])** – also empty.

## Success Indicators
- The agent’s final line is exactly `FINISH([])` for order‑only tasks.
- For numeric‑only tasks, the final line is `FINISH([<number>])` with no quotes or units.
- No additional strings appear inside the FINISH list.

## Failure Indicators
- The FINISH payload contains any string element.
- The numeric answer is wrapped in quotes or includes units.
- The agent returns a list with more than one element when only one is expected.

---
