---
description: Aggregates dose values from MedicationRequest resources (sum, last, count)
  handling doseQuantity, dose_val_rx and extensions.
name: dose_aggregation_enforcer
provenance:
  baseline_fixes: 1
  baseline_regressions: 3
  epoch: 7
  failure_mode: dose_aggregation_missing_or_invalid
  fixes: 1
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 05a9aa5bb494b962444ac354
  - 07bde541ff2932869ecb4912
  - 081ba7feccd490013f102984
  - 08e4e46ffbf10a71b11cc538
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a question asks for **total, last, or count of medication doses** (e.g., "total dose of ondansetron prescribed", "dose of docusate sodium (liquid) last prescribed", "how many doses of omeprazole have been prescribed") and the answer depends on values stored in `MedicationRequest` resources.

## Procedure
1. **Ensure data is available** – If `MedicationRequest` resources have not been fetched, call `resource_query_precheck_medicationrequest` first.
2. **Identify the relevant encounter(s)**
   - Use the same encounter‑selection logic as other encounter‑aware skills (hospital identifiers or `class.code == 'IMP'`).
   - If the question mentions "last hospital encounter", pick the most recent encounter; if it mentions "first", pick the earliest.
3. **Match the medication**
   - Normalise the target medication string (lower‑case, collapse whitespace).
   - Use the existing `medication_name_substring_match_enforcer` logic to compare against:
     * `medicationCodeableConcept` coding displays/text
     * `medicationReference` → linked `Medication` resource displays/text
   - Accept substring matches in either direction.
4. **Extract dose values from each matching `MedicationRequest`**
   - Initialise `dose = 0` (for sum) and `dose_count = 0`.
   - For each matching request:
     a. **Standard dosageInstruction** – iterate `dosageInstruction[].doseAndRate[]` and read `doseQuantity.value` (numeric). If a `unit` is present, store it for later consistency checks.
     b. **Custom field `dose_val_rx`** – if the top‑level key `dose_val_rx` exists, coerce it to a float (strip non‑numeric characters if needed) and add.
     c. **Extension fallback** – scan `extension[]` for URLs ending with `dose_val_rx`; extract `valueString` or `valueQuantity` similarly.
     d. Increment `dose_count` for each request that yields a numeric dose.
5. **Determine the required aggregation** based on the question wording:
   - If the query contains words like "total", "sum", "amount of", return the **sum** (`dose`).
   - If it contains "last prescribed" or "last time", sort matching requests by `authoredOn`/`occurrenceDateTime` (ISO‑8601) and return the **dose of the most recent** request.
   - If it contains "how many doses" or "count", return `dose_count`.
6. **Unit handling** – If a unit was captured and all doses share the same unit, append it to the numeric answer (e.g., `300 mg`). If units differ, return the numeric value with a note that units varied.
7. **Answer formatting** – Return a plain number (or number+unit) without surrounding text; let higher‑level logic add phrasing.

## Checks
- Verify that at least one `MedicationRequest` resource was retrieved.
- Confirm that each extracted dose is a numeric type (int or float); skip non‑numeric entries.
- Ensure the encounter filter (if any) matched at least one request; otherwise answer `None`.
- When returning a summed dose, make sure all included doses share the same unit; if not, note the inconsistency.
- For "last" queries, ensure the selected request has a valid `authoredOn` or `occurrenceDateTime` to determine recency.

## Avoid
- Do not assume a single `doseQuantity` per `MedicationRequest`; multiple `doseAndRate` entries must all be summed.
- Do not ignore custom fields (`dose_val_rx`) or extensions – many datasets store the prescribed amount there.
- Do not return the medication name; the skill is only responsible for aggregating dose numbers.
- Do not round or convert units unless all units are identical; leave conversion to a dedicated unit‑conversion skill.
