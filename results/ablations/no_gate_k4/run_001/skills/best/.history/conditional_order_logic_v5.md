---
description: Add potassium/magnesium replacement ordering with paired repeat lab and
  confirmation output
name: conditional_order_logic
provenance:
  action: MODIFY
  epoch: 1
  no_gate: true
  parent_version: 4
  triggering_sample_ids:
  - task9_22
  - task9_1
  - task2_1
  - task9_5
  - task1_20
  - task9_9
  - task10_10
  - task5_3
  - task1_10
  - task9_8
  update_cycle: 1
tags: []
version: 5
---

# Conditional Order Logic for Potassium and Magnesium Replacement with Follow‑up Lab

## Pattern Description
You must decide whether to place a replacement medication order based on a recent electrolyte result and, when ordering, also schedule a repeat laboratory check. This pattern applies to any task that asks for "if low, then order replacement ... also pair this order with a morning serum ... level to be completed the next day at 8 am". The skill extracts the numeric value, compares it to a low‑threshold, creates the appropriate `MedicationRequest` (using the NDC supplied in the task context), creates a `ServiceRequest` for a repeat observation at the specified time, and finally returns a concise order‑confirmation string.

## When to Use This Skill
- When a task references the most recent **potassium (K)** or **magnesium (MG)** level and includes conditional ordering language (e.g., "If low, then order replacement ... also pair this order with a morning serum ... level to be completed the next day at 8am").
- When the extracted lab value is below the clinically‑defined low threshold (K < 3.5 mmol/L, Mg < 1.5 mg/dL).
- When the task provides an NDC code for the replacement medication.

## Common Failure Patterns
- The agent returns only the lab value (`FINISH(["3.9 mmol/L"])`) and never creates an order.
- No repeat‑lab `ServiceRequest` is generated even though the task explicitly asks for it.
- `order_confirmation_output` never fires because no order was placed.
- The agent posts an order but finishes with the raw lab array instead of a confirmation string.

## Recommended Patterns
**Pattern 1: Core ordering strategy**
1. Use `numeric_lab_value_extraction` to obtain the numeric result and its unit.
2. Compare the value to the low‑threshold (K < 3.5 mmol/L, Mg < 1.5 mg/dL).
3. If the value is low:
   - POST a `MedicationRequest` with:
     ```json
     {
       "resourceType": "MedicationRequest",
       "status": "active",
       "intent": "order",
       "medicationCodeableConcept": {"coding":[{"system":"http://hl7.org/fhir/sid/ndc","code":"<NDC_FROM_TASK>"}]},
       "subject": {"reference": "Patient/<MRN>"},
       "authoredOn": "<CURRENT_TIME>"
     }
     ```
   - Compute the next‑day 08:00 timestamp (`<CURRENT_TIME>` + 1 day, time set to 08:00).
   - POST a `ServiceRequest` for the repeat observation with:
     ```json
     {
       "resourceType": "ServiceRequest",
       "status": "active",
       "intent": "order",
       "code": {"coding":[{"system":"http://loinc.org","code":"<LOINC_FOR_K_OR_MG>"}]},
       "subject": {"reference": "Patient/<MRN>"},
       "occurrenceDateTime": "<NEXT_DAY_08:00>"
     }
     ```
   - Set `order_created = true`.
4. If the value is not low, set `order_created = false`.

**Pattern 2: Confirmation output**
- After the POST(s), if `order_created` is true, finish with a single‑sentence confirmation:
  - For potassium: `FINISH(["Potassium replacement ordered; repeat potassium level scheduled for <NEXT_DAY_08:00>."])`
  - For magnesium: `FINISH(["Magnesium replacement ordered; repeat magnesium level scheduled for <NEXT_DAY_08:00>."])`
- If no order was needed, finish with the numeric value only (as existing skills already handle).

**Pattern 3: Fallback / verification**
- If any POST returns an error, fall back to reporting the lab value and include a warning note in the FINISH output.

## Example Application
**Task:** "Check patient S6474456's most recent potassium level. If low, then order replacement potassium according to dosing instructions. Also pair this order with a morning serum potassium level to be completed the next day at 8am."

**Step‑by‑step:**
1. GET `.../Observation?code=K&patient=S6474456` → bundle with latest value `3.8 mmol/L`.
2. Extract numeric value `3.8`.
3. Compare: `3.8 < 3.5`? **No**, so `order_created = false`.
4. FINISH with numeric output (handled by other skills).
---
**Task (low value):** same as above but value `3.2 mmol/L`.
1‑2. Extract `3.2`.
3. `3.2 < 3.5` → true.
4. POST `MedicationRequest` using NDC from task.
5. Compute next‑day `2023-11-14T08:00:00+00:00`.
6. POST `ServiceRequest` for repeat potassium with that occurrence.
7. FINISH: `FINISH(["Potassium replacement ordered; repeat potassium level scheduled for 2023-11-14T08:00:00+00:00."])`.

## Success Indicators
- One or two POST calls (MedicationRequest and ServiceRequest) succeed (HTTP 201/200).
- The final FINISH output contains the order‑confirmation sentence, not just a lab array.
- The confirmation string mentions the correct medication (potassium or magnesium) and the correct scheduled time.

## Failure Indicators
- FINISH output is an array of lab values only.
- No POST calls are observed in the trace.
- The confirmation string is missing or malformed (e.g., includes the raw lab array).
- The repeat‑lab `ServiceRequest` is not created when the task explicitly asks for it.
