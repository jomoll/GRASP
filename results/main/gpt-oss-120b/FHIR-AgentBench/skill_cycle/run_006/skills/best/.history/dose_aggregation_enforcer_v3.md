---
description: Fix dose queries by correctly detecting missing dose fields and extracting
  available dose data.
name: dose_aggregation_enforcer
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 13
  failure_mode: medication_dose_field_missing
  fixes: 3
  parent_version: 2
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 05a9aa5bb494b962444ac354
  - 08e4e46ffbf10a71b11cc538
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 1
tags: []
version: 3
---

## When to use
You must activate this skill for any question that explicitly asks for a medication dose, amount, strength, quantity, or any numeric value that comes from a **MedicationRequest** (e.g., "What was the dose of …?", "How many mg of … were prescribed?", "First dose of heparin flush", etc.). The query must reference a medication name or identifier.

## Procedure
1. **Confirm resource type** – Ensure the agent has fetched `MedicationRequest` resources for the patient.
2. **Detect dose‑related intent** – Look for keywords such as `dose`, `amount`, `strength`, `quantity`, `mg`, `ml`, `units`, `dose_val_rx`, `dosageInstruction`, `doseAndRate` in the user question (case‑insensitive).
3. **Search each MedicationRequest** for dose information in the following order:
   - Extension with URL ending in `dose_val_rx`.
   - `dosageInstruction` → `doseAndRate` → `doseQuantity` (or `doseRange`).
   - Direct top‑level fields `doseQuantity` or `doseRange` if present.
4. **Collect values**:
   - If a numeric `value` is found, keep the value and its unit.
   - If multiple dose entries exist, apply the aggregation requested by the question (e.g., `first`, `last`, `average`, `sum`).
5. **Handle missing data** – If **no** dose information is found for any matching MedicationRequest, set the answer to `null` (or `None`) and skip further processing for this query.
6. **Return the result** – Provide the numeric dose (or aggregated value) together with its unit, formatted as a plain number or "{value} {unit}" string.

## Checks
- Resource type must be `MedicationRequest`.
- The question must contain at least one dose‑related keyword.
- At least one MedicationRequest must match the medication name/sub‑string criteria.
- If a dose value is returned, ensure it is a numeric type (int/float) and the unit is a string.
- If no dose is found, the final answer must be `null`/`None` (not zero or an empty string).

## Avoid
- Returning a numeric default when the dose field is absent.
- Interfering with queries that aggregate other medication attributes (e.g., distinct drug count).
- Matching on unrelated resources such as `Observation` or `Procedure`.
- Formatting the answer as a boolean or a free‑text sentence; keep it strictly numeric or `null`.
