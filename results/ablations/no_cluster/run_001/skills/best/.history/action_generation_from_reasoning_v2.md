---
description: "Add response\u2011inspection rules and conditional decision logic for\
  \ Patient and Observation lookups"
name: action_generation_from_reasoning
provenance:
  action: MODIFY
  epoch: 0
  fixes: 12
  parent_version: 1
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - task1_20
  - task9_5
  - task9_1
  - task9_22
  - task10_8
  - task1_13
  - task1_16
  - task2_6
  - task9_28
  - task2_17
  update_cycle: 1
tags: []
version: 2
---

# Response‑Based Action Generation

## Pattern Description
You must not assume that a GET request succeeded or that the needed data is present. After every FHIR GET, inspect the returned Bundle (or single resource) to verify that the expected entry exists, extract the exact field you need, and base any subsequent API calls on that extracted value. This pattern applies to any task that:
- Looks up a Patient by identifier, name + birthdate, or other search parameters and needs the MRN.
- Computes an age from a Patient’s `birthDate`.
- Retrieves a lab Observation (e.g., potassium, magnesium, HbA1c) and must read the numeric value (`valueQuantity.value` or `valueString`) and the timestamp (`effectiveDateTime`).
- Makes a clinical decision (order replacement, order repeat test) only when a threshold or recency rule is met.

## When to Use This Skill
- When a task issues `GET /Patient?...` and the instruction later asks for the MRN, age, or to verify the patient exists before ordering.
- When a task issues `GET /Observation?...` and the instruction requires the latest value, its date, or a conditional order based on that value.
- When a task must decide whether to create a `MedicationRequest` or `ServiceRequest` based on a lab value falling below a low‑threshold or being older than a defined interval.

## Common Failure Patterns
- Returning a hard‑coded "Patient not found" without checking the Bundle `total` field.
- Using a guessed age instead of calculating `floor((now - birthDate) / 365.25)`.
- Ignoring the Observation payload and finishing with a generic message (e.g., "No potassium replacement needed") regardless of the actual value.
- Failing to order a repeat HbA1c when the latest result is > 365 days old.
- Posting a ServiceRequest before confirming the patient lookup succeeded.

## Recommended Patterns
**Pattern 1: Verify GET response and extract required field**
1. After a `GET /Patient?...` inspect the Bundle:
   - If `total == 0` → FINISH(["Patient not found"]).
   - Else locate the first entry’s `resource.identifier` where `type.coding.code == "MR"` (or take the first identifier) and extract its `value` as `mrn`.
2. After a `GET /Observation?...` inspect the Bundle:
   - If `total == 0` → use the task‑specified fallback (e.g., return -1 or skip ordering).
   - Else sort entries by `effectiveDateTime` descending, pick the first entry.
   - Extract `valueQuantity.value` (or `valueString` for BP) as `obs_value` and `effectiveDateTime` as `obs_date`.
3. For age calculation:
   - Parse `resource.birthDate` (ISO‑8601) and compute `age = floor((now - birthDate) / 365.25)`.

**Pattern 2: Conditional ordering based on extracted data**
- **Potassium**: If `obs_value < 3.5` mmol/L → create `MedicationRequest` for potassium replacement **and** a `ServiceRequest` for a repeat serum potassium at `now + 1 day` 08:00.
- **Magnesium**: If `obs_value < 1.5` mg/dL → create `MedicationRequest` for IV magnesium.
- **HbA1c**: If `obs_date` is more than 365 days before `now` → create a `ServiceRequest` for a new HbA1c test.
- If the condition is not met, simply FINISH with the extracted value (or -1).

**Pattern 3: Formatting the final FINISH output**
- Return numeric results as plain numbers (e.g., `FINISH([2.5])`).
- Return paired results as an array in the order requested (e.g., `FINISH(["6.1%","2023-10-13"])`).
- When an order is placed, optionally return a confirmation string (e.g., `FINISH(["Potassium replacement ordered"])`).

## Example Application
**Task:** "What’s the most recent potassium level for patient S1796597? If low, then order replacement potassium and schedule a repeat test tomorrow at 8 am."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=S1796597`
2. Inspect the Bundle:
   - `total > 0` → sort entries, pick newest.
   - Extract `valueQuantity.value = 3.2` and `effectiveDateTime = "2023-11-12T09:00:00+00:00"`.
3. Compare: `3.2 < 3.5` → low.
4. `POST http://localhost:8080/fhir/MedicationRequest` with potassium NDC and dosage.
5. `POST http://localhost:8.../ServiceRequest` for repeat serum potassium at `now+1d` 08:00.
6. `FINISH(["Potassium replacement ordered","Repeat test scheduled"])

## Success Indicators
- The agent extracts `mrn`, `age`, or `obs_value` from the actual FHIR response instead of using a placeholder.
- Conditional orders are only created when the extracted lab value meets the low‑threshold or recency rule.
- FINISH output contains the exact numeric value (or -1) and, when applicable, a confirmation of the order.

## Failure Indicators
- FINISH returns "Patient not found" while the GET Patient Bundle shows `total > 0`.
- Age is returned without computing from `birthDate` (e.g., a static string).
- Lab value is ignored and the agent always says "No replacement needed".
- An order is posted even though the lab value is within normal range or the result is recent.
- The final output mixes strings with numbers (e.g., `"[3.5 mmol/L]"` instead of `[3.5]`).
