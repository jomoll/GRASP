---
description: Compute average, minimum, or maximum of numeric Observation values and
  return a plain number.
name: numeric_aggregation
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 4
  failure_mode: answer_format_wrong_type
  fixes: 4
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 0424a90b6986dc6ca2da8b3b
  - 0577ee51b3ad3c9fcf8fbbae
  - 0741b96a36302acf8ace5c02
  - 074c7225bee20e2006c6db58
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should trigger this skill when the user asks for a **single numeric summary** of a lab or vital sign, e.g., "average oxygen", "minimum hematocrit", "maximum systolic blood pressure", or any phrasing that includes words like *average*, *mean*, *minimum*, *max*, *maximum*, *lowest*, *highest*, *difference* (when the answer is a numeric delta).
The question must be answerable from Observation resources and does **not** require a textual explanation—only a number (int or float) should be returned.

## Procedure
1. **Parse the request** to identify the target observation term(s) and the aggregation type (average / mean, minimum / lowest, maximum / highest, difference).
2. **Query Observations** for the patient (use `get_resources_by_patient_fhir_id` with `resource_type="Observation"`).
3. **Filter observations**:
   - Keep only those whose `code.coding.display`, `code.coding.code` or `code.text` contain **all** target terms (case‑insensitive, whitespace‑normalized).
   - Apply any explicit date window supplied in the question (e.g., "since 03/this year", "in 10/this year").
4. **Extract numeric values** using the existing `observation_value_extraction` logic (handle `valueQuantity.value`, `valueInteger`, or parsable `valueString`). Discard observations with missing or non‑numeric values.
5. **Aggregate** the collected numbers according to the identified operation:
   - *average*: sum / count (return float with up to two decimal places).
   - *minimum*: smallest value.
   - *maximum*: largest value.
   - *difference*: if the question mentions two specific timestamps, locate the two observations exactly at those times and compute `value2 - value1`.
6. **Return the result** as a plain number (no surrounding text). If no matching observations are found, return `null`.

## Checks
- Verify that the resource type is **Observation**.
- Ensure the extracted values are numeric; if any value cannot be parsed, exclude it.
- Confirm the aggregation produced at least one value; otherwise answer `null`.
- The final answer must be a JSON‑compatible number (int or float), not a string or sentence.
- For date‑window filters, parse dates with `dateutil.parser.isoparse` and compare in UTC‑naïve form.

## Avoid
- Returning explanatory sentences (e.g., "The average oxygen is ...").
- Mixing units; assume all observations for a given term use the same unit.
- Performing aggregation when the question asks for a timestamp or a categorical answer.
- Including `null` inside a string; answer must be the literal `null` value if no data.
