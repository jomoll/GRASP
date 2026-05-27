---
description: Handle average/min/max/total numeric queries on Observation resources
  and return plain numbers.
name: numeric_aggregation_query
provenance:
  baseline_fixes: 7
  baseline_regressions: 3
  epoch: 1
  failure_mode: answer_format_wrong_type
  fixes: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 0577ee51b3ad3c9fcf8fbbae
  - 074c7225bee20e2006c6db58
  - 09b1b086d491d385b6744dd6
  - 0a43e2fe814473ab9035db70
  - 0a8c46b684e72300d29c18aa
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must trigger this skill when the user asks for a numeric aggregation (average, mean, minimum, maximum, total, sum, count) of a lab or vital sign value for a specific patient, optionally constrained by a time window (e.g., "in 03/this year", "since 12/07/2133") or by encounter scope (first/last hospital/ICU encounter, specific encounter type).

## Procedure
1. **Parse the request** to identify:
   - The target observation (e.g., oxygen, hematocrit, output, weight) using keywords, LOINC codes, or any display/text match.
   - The aggregation function (average/mean, minimum, maximum, total/sum, count).
   - Any date constraints (month/year, explicit dates, relative periods like "this year", "last 90 days").
   - Any encounter constraints (first/last hospital encounter, first ICU visit, etc.).
2. **Retrieve Observations** for the patient via `get_resources_by_patient_fhir_id` with `resource_type="Observation"`.
3. **Filter by observation code**:
   - Examine `code.coding[*].display`, `code.coding[*].code`, and `code.text`.
   - Perform case‑insensitive comparison after normalising whitespace (`re.sub(r"\\s+", " ", s.strip().lower())`).
4. **Apply encounter filter** (if required):
   - Retrieve Encounter resources for the patient.
   - Identify the relevant encounter(s) using identifier system containing `encounter‑hosp`, `encounter‑icu`, or fallback class codes (`IMP`, `ICU`, `EMER`).
   - Resolve child encounters via `partOf` references.
   - Keep only observations whose `encounter.reference` points to one of the selected encounter IDs.
5. **Apply date filter**:
   - Convert all candidate dates (`effectiveDateTime` or `effectivePeriod.start`) to `datetime` objects.
   - Keep observations whose timestamps fall inside the parsed window.
6. **Extract numeric values**:
   - Use `valueQuantity.value` (or `valueInteger`).
   - Discard observations lacking a numeric value.
   - Record the unit (`valueQuantity.unit`) for later consistency checks.
7. **Validate data set**:
   - If no observations remain, answer "No data found for …" and stop.
   - If multiple units are present, choose the most common unit; if units differ, note the mismatch in the answer.
8. **Compute the aggregation**:
   - `average`: sum(values) / len(values)
   - `minimum`: min(values)
   - `maximum`: max(values)
   - `total`/`sum`: sum(values)
   - `count`: len(values)
   - Round the result to a sensible number of decimal places (e.g., 2 for most labs, 0 for counts).
9. **Format the final answer**:
   - Return **only** the numeric result (or "<number> <unit>" if the user explicitly asked for the unit).
   - Do **not** wrap the answer in JSON, sentences, or additional commentary.

## Checks
- Verify that the resource type is `Observation`.
- Ensure at least one observation matches all filters before performing aggregation.
- Confirm that all retained values are numeric (int or float).
- If a unit is required, ensure all values share the same unit; otherwise, report the most common unit.
- The answer must be a plain number (or number + unit) with no surrounding punctuation other than optional whitespace.

## Avoid
- Returning JSON objects, explanatory sentences, or extra text.
- Mixing units or reporting a value when no matching observations exist.
- Ignoring the requested time window or encounter scope.
- Using the wrong aggregation (e.g., returning a count when the user asked for average).
- Failing to normalize case and whitespace when matching observation codes.
