---
description: Return a clear 'no data' response when a query yields no matching resources.
name: no_data_handling
provenance:
  baseline_fixes: 1
  baseline_regressions: 4
  epoch: 10
  failure_mode: answer_provided_when_no_data
  fixes: 3
  probe_score: 3
  regressions: 3
  triggering_sample_ids:
  - 02885cc1fb11efec74cb16fd
  - 0577ee51b3ad3c9fcf8fbbae
  - 06ba722e2ac0589ffacd1249
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill whenever the agent has filtered FHIR resources (Encounter, Observation, MedicationRequest, Procedure, etc.) based on the question's criteria and the resulting collection is empty. Typical cases include requests for maximum/minimum/average values, counts, or timestamps where no matching observations exist.

## Procedure
1. After executing any resource‑specific filtering logic, check the length of the filtered list.
2. If the list is empty:
   - Construct a concise response that explains the lack of data. Use the pattern:
     - For value‑based queries: "No [observation name] observation found for patient {patient_id} in the specified period."
     - For count‑based queries: "No {resource type} records found for patient {patient_id} matching the criteria."
     - For timestamp queries: "No {observation name} observation was recorded for patient {patient_id} during the requested timeframe."
   - Do **not** attempt to fabricate a value, date, or calculation.
   - Return this response immediately, bypassing any further answer‑format or rounding steps.
3. If the list is not empty, allow the normal processing flow to continue (e.g., compute max, average, etc.).

## Checks
- Verify that the filtered collection (observations, encounters, medication requests, etc.) is non‑empty before any aggregation or formatting.
- Ensure the patient identifier used in the response matches the one from the original question.
- Confirm that the response string matches one of the predefined templates above; it must be a plain English sentence, not a JSON or numeric value.

## Avoid
- Returning a default or placeholder date/value when no data exists.
- Proceeding to answer‑format validation on an empty result set.
- Using vague phrases like "Data not available" without specifying the missing resource or timeframe.
