---
description: Extract numeric dose values from MedicationRequest dosageInstruction
  structures when dose_val_rx is missing, **but only when the question is explicitly
  about medication dosing**. This prevents the skill from running on unrelated queries
  (e.g., microbiology tests or vital signs).
name: dose_extraction_from_dosage_instruction
provenance:
  baseline_fixes: 2
  baseline_regressions: 4
  epoch: 9
  failure_mode: dose_field_not_found
  fixes: 4
  probe_score: 3
  regressions: 3
  triggering_sample_ids:
  - 07bde541ff2932869ecb4912
  - 081ba7feccd490013f102984
  - 09469e7ae520d7c2a28ad15f
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill **only** when the user question contains dosage‑related keywords **and** the retrieved resources include at least one `MedicationRequest`.

**Dosage‑related keywords (case‑insensitive)**: `dose`, `doses`, `dose amount`, `dose quantity`, `total dose`, `how many`, `number of doses`, `mg`, `tablet`, `pill`, `prescribed`, `medication amount`, `strength`.

If none of these words appear in the question, skip this skill.

## Procedure
1. **Validate trigger** – Scan the user question for any of the dosage‑related keywords. If none are found, abort the skill (return no result).
2. **Collect MedicationRequest resources** – Retrieve all `MedicationRequest` resources that were fetched for the current patient/encounter.
3. **Medication name match** – For each request, extract the medication name using the existing medication‑name extraction logic. Keep only requests whose medication name matches the drug mentioned in the question (case‑insensitive substring match). If no requests match, abort the skill.
4. **Locate dose information** within each matching request:
   - If `dosageInstruction` exists and is a list, inspect each element (or just the first if you prefer).
   - Check, in order, for a numeric value:
     a. `dosageInstruction[i].doseAndRate[0].doseQuantity.value`
     b. `dosageInstruction[i].doseQuantity.value`
     c. `dosageInstruction[i].doseAndRate[0].doseQuantity` may contain `value` and `unit`; use the numeric `value`.
   - If none of the above yield a value, fall back to a top‑level `dose_val_rx` field (legacy records).
5. **Convert** the extracted value to a float. If conversion fails, ignore that request.
6. **Aggregate** according to the question intent (detected from keywords):
   - **Count** (`how many doses`, `number of doses`) – return the number of matching requests.
   - **Sum** (`total dose`, `total amount`) – return the sum of the numeric values.
   - **First/Last** (`first dose`, `last dose`) – determine the earliest or latest date using `authoredOn`, `occurrenceDateTime`, or `dispenseRequest.validityPeriod.start` and return that request’s dose value.
7. **Return** a plain number (int or float). Append the unit (e.g., `mg`) only if the question explicitly asks for a unit.

## Checks
- Ensure at least one `MedicationRequest` passed the medication‑name filter before proceeding.
- Verify the extracted dose is numeric before any aggregation.
- Respect any encounter or time‑window constraints present in the question by filtering on `encounter.reference` and the appropriate date fields.
- The final answer must be a scalar number (or number + unit when requested).

## Guard clauses (to avoid regressions)
- **Keyword guard** – If the question lacks dosage‑related keywords, the skill does nothing.
- **Resource guard** – If no `MedicationRequest` resources are present after the medication‑name filter, the skill does nothing.
- **Non‑medication resources** – The skill never inspects `Observation`, `Procedure`, etc.; it only processes `MedicationRequest`.

## Avoid
- Do not assume a dose field exists; always check each possible location and fall back gracefully.
- Do not sum doses from unrelated medications.
- Do not duplicate doses from multiple `dosageInstruction` entries unless explicitly required.
- Do not return a string or dictionary; the answer must be a numeric scalar (or scalar + unit when asked).
