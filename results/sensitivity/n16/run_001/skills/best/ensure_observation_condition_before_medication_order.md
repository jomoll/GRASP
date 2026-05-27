---
description: Enforce evaluation of lab result before creating a conditional MedicationRequest
name: ensure_observation_condition_before_medication_order
provenance:
  action: MODIFY
  epoch: 4
  fixes: 6
  parent_version: 1
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - task10_13
  - task10_18
  - task9_3
  - task10_27
  update_cycle: 1
tags: []
version: 2
---

# ensure_observation_condition_before_medication_order

## Pattern Description
You must verify that any medication order conditioned on a lab value is truly justified by the patient’s most recent observation. First, retrieve the relevant Observation, then extract the numeric result and compare it against a clinically‑defined “low” threshold for that lab. Only if the value meets the low‑condition should you create a `MedicationRequest`. This prevents blind ordering when the lab is normal or missing.

## When to Use This Skill
- When the task description contains a conditional phrase such as *"if [lab] is low/high/abnormal then order …"*.
- When a specific lab code (e.g., potassium `K`, magnesium `MG`, calcium `CA`) is mentioned together with a medication or dosing instruction.
- When the task also asks for a follow‑up lab (e.g., “pair this order with a morning serum potassium level”).

## Common Failure Patterns
- The agent issues a `MedicationRequest` after the Observation GET **without** checking the result value.
- The agent creates a `MedicationRequest` even when the Observation bundle is empty (no recent lab).
- The agent treats the Observation’s `valueQuantity.value` as a string or ignores the `unit`, leading to a false‑positive low check.

## Recommended Patterns
**Pattern 1: Retrieve and evaluate the Observation**
1. GET the Observation using the exact code and patient reference, **including a date filter** if the task limits recency (e.g., `date=ge2023-11-12T10:15:00Z`).
2. If the bundle `total` is `0`, **do not** create a `MedicationRequest` and finish with an empty list.
3. From the first entry, extract `valueQuantity.value` **as a number** and note the `valueQuantity.unit`.
4. Compare the numeric value to the lab‑specific low threshold (see table below). If the value is **not** below the threshold, skip the order.

**Low‑threshold table (example values)**
| Lab code | Unit | Low threshold |
|----------|------|---------------|
| K (potassium) | mmol/L | 3.5 |
| MG (magnesium) | mg/dL | 1.5 |
| CA (calcium) | mg/dL | 8.5 |
*Add additional labs as needed.*

**Pattern 2: Conditional ordering**
- **If** the value is below the threshold **then** POST a `MedicationRequest` with the supplied NDC and dosage.
- **If** the task also requests a follow‑up lab, POST a `ServiceRequest` for that lab **only after** the medication order is approved.

**Pattern 3: Formatting the FINISH output**
- When no order is placed, return `FINISH([])` (empty JSON array).
- When an order is placed, return `FINISH(["MedicationRequest", "ServiceRequest"])` or any required answer format defined by the task.

## Example Application
**Task:** "Check patient S6550627's most recent potassium level. If low, then order replacement potassium …"

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=K&patient=Patient/S6550627&date=ge2023-11-12T10:15:00Z`
2. Bundle `total` = 1 → extract `valueQuantity.value = 3.2` and `unit = "mmol/L"`.
3. Compare: `3.2 < 3.5` → condition true.
4. POST `MedicationRequest` with the provided NDC and dosage.
5. POST `ServiceRequest` for the next‑day serum potassium.
6. `FINISH(["MedicationRequest", "ServiceRequest"])`.

If step 2 returned no entries **or** the value was `4.0` (≥ 3.5), skip steps 4‑5 and simply `FINISH([])`.

## Success Indicators
- The agent only creates a `MedicationRequest` when the Observation value is numerically below the defined low threshold.
- No `MedicationRequest` is posted when the Observation bundle is empty or the value is normal/high.
- The final `FINISH` output matches the expected format (empty list when no order, list of created resources otherwise).

## Failure Indicators
- A `MedicationRequest` appears in the log despite the Observation being missing or showing a normal value.
- The agent extracts the value as a string (e.g., "3.2 mmol/L") and fails the numeric comparison.
- The agent posts a `ServiceRequest` for the follow‑up lab even when the medication order was not placed.
