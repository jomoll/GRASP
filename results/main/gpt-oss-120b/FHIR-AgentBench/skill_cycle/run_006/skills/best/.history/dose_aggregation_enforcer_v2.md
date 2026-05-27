---
description: "Enforce that dose\u2011based aggregations on MedicationRequest return\
  \ None when no matching dose data exists, **but only activate for questions that\
  \ actually refer to a dose**. This prevents the skill from interfering with queries\
  \ that aggregate other medication attributes (e.g., distinct medication count) or\
  \ that target other resource types (e.g., Observation)."
name: dose_aggregation_enforcer
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 11
  failure_mode: missing_data_returned_zero_instead_of_none
  fixes: 4
  parent_version: 1
  probe_score: 5
  regressions: 0
  triggering_sample_ids:
  - 01389011a3cea028b226b95b
  - 09b1b086d491d385b6744dd6
  - 0a43e2fe814473ab9035db70
  update_cycle: 1
tags: []
version: 2
---

## When to use
Trigger this skill **only** for questions that request an aggregated dose value (sum, last dose, count of doses, average, min, max, etc.) from **MedicationRequest** resources **and** explicitly mention a dose‑related term.

**Dose‑related trigger keywords** (case‑insensitive):
- "dose"
- "dose_val_rx"
- "strength"
- "amount"
- "mg", "ml", "µg", "mcg", "units"
- "prescribed dose"
- "dose quantity"
If none of these keywords appear in the user question, the skill should **skip** and leave the answer untouched.

## Procedure
1. **Guard clause – check question text**
   ```python
   question_lower = instruction.lower()
   dose_keywords = ["dose", "dose_val_rx", "strength", "amount", "mg", "ml", "µg", "mcg", "units", "prescribed dose", "dose quantity"]
   if not any(kw in question_lower for kw in dose_keywords):
       # Not a dose‑focused query – do nothing
       answer = answer  # preserve existing answer
       return
   ```
2. **Fetch data** – Ensure a `MedicationRequest` bundle has been retrieved for the patient (use `resource_query_precheck_medicationrequest` if needed).
3. **Apply filters** – Iterate over each `MedicationRequest` and keep only those that satisfy all explicit filters in the question (e.g., medication name substring, date window, route, encounter reference).
4. **Extract dose** – For each retained request, obtain the numeric dose value:
   - Prefer the top‑level `dose_val_rx` field.
   - If missing, look for an extension whose `url` ends with `dose_val_rx` and take its `valueString` or `valueQuantity.value`.
   - Parse the first numeric token from the extracted string.
5. **Aggregate** – Depending on the requested operation (sum, last, count, average, min, max), compute the result from the collected numeric values.
6. **Handle empty set** – If **no** `MedicationRequest` passes the filters **or** no dose could be extracted, set the answer to `None` (Python `None`). Do **not** return `0`.
7. **Return** – Output the aggregated value (or `None`).

## Checks
- Verify the resource type is `MedicationRequest`.
- Confirm that any date constraints are respected (year/month/day as specified).
- Ensure medication‑name matching is case‑insensitive and whitespace‑normalized.
- Validate that the aggregation operation matches the question (sum → total, last → most recent dose, count → number of dose entries, etc.).
- Before finalizing, assert that the answer is either a numeric type (int/float) **or** `None` when no data matched.

## Avoid
- Returning `0` when the filtered set is empty – this masks missing data.
- Assuming a dose exists just because the resource is present; always check for `dose_val_rx` or its extension.
- Ignoring additional filters such as route, encounter, or dosage instruction that may further limit the matching set.
- Activating on non‑dose aggregation queries or on resource types other than `MedicationRequest`.
