---
description: "Apply low\u2011value thresholds to lab observations and trigger appropriate\
  \ orders"
name: observation_threshold_action
provenance:
  action: ADD
  epoch: 3
  fixes: 5
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - task5_16
  - task10_17
  - task5_3
  - task9_8
  - task8_23
  - task4_26
  - task4_28
  update_cycle: 1
tags:
- lab
- threshold
- decision
- magnesium
- potassium
version: 1
---

# Observation Threshold Action

## Pattern Description
You must treat certain laboratory observations as decision points rather than simple data retrieval. For electrolytes and other critical labs, a numeric value below (or above) a clinically‑defined threshold determines whether an intervention—typically a medication or repeat test—should be ordered. This skill extracts the numeric value from the Observation, compares it against a per‑code threshold table, and either creates a ServiceRequest (or does nothing) based on the result.

## When to Use This Skill
- When a task asks to *check* a lab value (e.g., magnesium, potassium, calcium) and *act* if the value is low or high.
- When the instruction explicitly mentions a time window (e.g., "last 24 hours") and a conditional order.
- When the task does **not** request a free‑text narrative but a concrete decision based on the numeric result.

## Common Failure Patterns
- Using `valueString` or `valueQuantity.unit` instead of the numeric `valueQuantity.value`.
- Ignoring the unit conversion (e.g., mg/dL vs mmol/L) and comparing raw numbers.
- Assuming any returned value means "normal" and never ordering replacement.
- Missing the case where no recent Observation exists and still attempting an order.

## Recommended Patterns
**Pattern 1: Extract numeric value**
1. From the Observation bundle, locate the first entry with `code.coding.code` matching the requested lab code.
2. Read `valueQuantity.value` **as a number**.
3. Verify `valueQuantity.unit` matches the expected unit for the code (e.g., `mg/dL` for MG, `mmol/L` for K). If the unit differs, convert using a simple map.

**Pattern 2: Threshold lookup and decision**
```json
{
  "MG": { "low": 1.5, "unit": "mg/dL", "orderNDC": "12345-6789-01" },
  "K":  { "low": 3.5, "unit": "mmol/L", "orderNDC": "98765-4321-10" }
}
```
1. Retrieve the threshold entry for the lab code.
2. If `value < low` → construct a `ServiceRequest` with the stored NDC and appropriate dosing instructions.
3. If `value >= low` → **do not** create an order; simply return the numeric value.
4. If the Observation bundle is empty (no recent result) → also do not order; return an empty list or `-1` as instructed.

**Pattern 3: Formatting the final output**
- When no order is needed, finish with `FINISH([value])` where `value` is a plain number.
- When an order is required, POST a `ServiceRequest` with:
  ```json
  {
    "resourceType": "ServiceRequest",
    "code": { "coding": [{ "system": "http://www.nlm.nih.gov/research/umls", "code": "<lab_code>", "display": "<lab name>" }] },
    "authoredOn": "<current_time>",
    "status": "active",
    "intent": "order",
    "priority": "stat",
    "subject": { "reference": "Patient/<MRN>" },
    "medicationCodeableConcept": { "coding": [{ "system": "http://hl7.org/fhir/sid/ndc", "code": "<orderNDC>" }] },
    "note": [{ "text": "Replacement <lab name> ordered per low value" }]
  }
  ```
- After a successful POST, finish with `FINISH([value])` (the original lab value) so the caller still sees the measurement.

## Example Application
**Task:** "Check patient S1023381's last serum magnesium level within last 24 hours. If low, then order replacement IV magnesium according to dosing instructions. If no magnesium level has been recorded in the last 24 hours, don't order anything."

**Step‑by‑step:**
1. `GET http://localhost:8080/fhir/Observation?code=MG&patient=S1023381&date=ge2023-11-12T10:15:00Z&date=le2023-11-13T10:15:00Z`
2. From the returned bundle, extract `valueQuantity.value` → e.g., `2.0` and confirm unit `mg/dL`.
3. Look up threshold for `MG`: low = `1.5` mg/dL.
4. Compare: `2.0 >= 1.5` → **not low** → do **not** POST a ServiceRequest.
5. `FINISH([2.0])`.

**If the value had been `1.2`**:
1‑3 same as above, value = `1.2`.
4. `1.2 < 1.5` → construct ServiceRequest using NDC `12345-6789-01` (example) and POST.
5. After POST succeeds, `FINISH([1.2])`.

## Success Indicators
- The agent extracts a plain numeric value (no units or strings) from `valueQuantity.value`.
- The agent compares the value against the correct low threshold for the lab code.
- No ServiceRequest is posted when the value is ≥ threshold or when the bundle is empty.
- When the value is < threshold, a correctly‑structured ServiceRequest is POSTed and the agent finishes with the numeric value.

## Failure Indicators
- The agent uses `valueString` or concatenates the unit, resulting in a non‑numeric FINISH payload.
- The agent always posts a ServiceRequest regardless of the numeric result.
- The agent posts an order when the Observation bundle is empty.
- The agent returns a narrative sentence instead of a plain number.
