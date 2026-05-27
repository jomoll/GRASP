---
description: Compute average, min, max or total of numeric observations and return
  a plain number.
name: observation_numeric_aggregation
provenance:
  baseline_fixes: 4
  baseline_regressions: 3
  epoch: 2
  failure_mode: answer_format_wrong_type
  fixes: 5
  probe_score: 1
  regressions: 3
  triggering_sample_ids:
  - 0577ee51b3ad3c9fcf8fbbae
  - 0741b96a36302acf8ace5c02
  - 074c7225bee20e2006c6db58
  - 09b1b086d491d385b6744dd6
  - 0a43e2fe814473ab9035db70
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should invoke this skill whenever a user asks for an **average**, **minimum**, **maximum**, **total** or **sum** of a numeric lab/value (e.g., oxygen, hematocrit, output, calcium) over a specified time range or encounter scope. The question typically contains keywords like *average*, *minimum*, *max*, *total*, *sum* and refers to an Observation (or Procedure) with a numeric `valueQuantity` or `valueDecimal`.

## Procedure
1. **Parse the request** to identify:
   - The target observation concept (e.g., "oxygen", "hematocrit", "output", "calcium total").
   - The aggregation function required (average, min, max, total).
   - Any date constraints (exact month, range, "since", "last X days", etc.) or encounter constraints (first/last hospital/ICU visit, specific encounter identifiers).
2. **Retrieve resources** using `get_resources_by_patient_fhir_id` for the resource types `Observation` and `Procedure` (some procedures store numeric results).
3. **Filter candidates**:
   - For each resource, collect possible textual identifiers from `code.coding.display`, `code.coding.code`, and `code.text`.
   - Normalise strings (lower‑case, collapse whitespace) and keep those that contain all keywords of the target concept.
   - Discard resources without a numeric value (`valueQuantity`, `valueDecimal`, `valueInteger`, or a numeric `valueString`).
   - Apply the date filter: parse `effectiveDateTime`, `issued`, or `effectivePeriod.start` into a `datetime` object and keep only those within the requested window.
   - If an encounter scope is required, ensure the resource’s `encounter.reference` matches the encounter(s) identified (first/last hospital, ICU, etc.).
4. **Extract numeric values** from the selected resources, converting them to `float`.
5. **Perform aggregation**:
   - **average**: sum(values) / len(values)
   - **minimum**: min(values)
   - **maximum**: max(values)
   - **total**: sum(values)
   - Round the result to a reasonable precision (e.g., two decimal places) but keep it as a numeric type.
6. **Return the answer** as a plain number (int or float). If no matching values are found, answer with `null` or a clear “No data” indicator that downstream logic can interpret as a missing numeric answer.

## Checks
- Verify that the filtered list contains at least one numeric value; otherwise signal “no data”.
- Ensure the aggregation function matches the user’s intent (average ↔ mean, total ↔ sum, etc.).
- Confirm the final answer is a numeric type, not a string or JSON object.
- If the request expects a date (e.g., *when* was the first/last occurrence), delegate to a separate date‑extraction skill; this skill only returns numbers.

## Avoid
- Returning a dictionary or formatted string (e.g., "Average = 98.6") – the answer must be a raw number.
- Using non‑numeric fields such as `valueString` that cannot be parsed to a float.
- Ignoring the requested date or encounter scope, which leads to incorrect aggregation.
- Mixing different observation concepts in the same aggregation.
