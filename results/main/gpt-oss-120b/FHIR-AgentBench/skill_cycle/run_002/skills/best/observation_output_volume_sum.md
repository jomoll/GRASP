---
description: "Sum volume\u2011type observation values (e.g., foley output, urine output)\
  \ with proper keyword and unit handling."
name: observation_output_volume_sum
provenance:
  baseline_fixes: 2
  baseline_regressions: 4
  epoch: 4
  failure_mode: output_volume_aggregation_error
  fixes: 4
  probe_score: 3
  regressions: 3
  triggering_sample_ids:
  - 02759807d268a649ffbc56e0
  - 09b1b086d491d385b6744dd6
  - 0d012e621517a4059d3caf10
  - 0d22269bdd7bfa8481b101b5
  update_cycle: 1
tags: []
version: 1
---

## When to use
Trigger this skill when a question asks for a **total amount of fluid output** (e.g., foley output, urine output, drain output) for a patient over a specified date range or since a given date.
Typical question patterns:
- "total volume of foley output since 12/07/2133"
- "total amount of output since 12/25/2174"
- "total output amount of patient X since 86 days ago"
- "total volume of output since <date>"
The skill is not for generic numeric aggregations like labs or vitals; it is scoped to observations whose code or text indicates a fluid output measurement.

## Procedure
1. **Retrieve Observations** for the target patient using `get_resources_by_patient_fhir_id` with `resource_type="Observation"`.
2. **Define the start datetime** based on the question (explicit date, relative offset, or start of today). If no date is supplied, assume the beginning of records.
3. **Normalize code strings**:
   - Collect `code.coding.display`, `code.coding.code`, and `code.text` for each Observation.
   - Apply `norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().lower())`.
4. **Keyword filter** – keep only observations where the normalized combined string contains **both**:
   - One of the output identifiers: `"output"`, `"urine"`, `"foley"`, `"drain"`, `"fluid"`.
   - Optionally, also require a body‑site term if the question is site‑specific (e.g., "urine").
5. **Date filter** – extract the observation timestamp from the first available of:
   - `effectiveDateTime`
   - `issued`
   - `effectivePeriod.start`
   Convert to a timezone‑naïve `datetime` and keep only those `>= start`.
6. **Value extraction** – obtain the numeric value from the first available of:
   - `valueQuantity.value`
   - `valueDecimal`
   - `valueInteger`
   - `valueString` (attempt `float`).
   If the observation also provides a `valueQuantity.unit`, **accept only** units that denote milliliters (`"ml"`, `"milliliter"`, `"milliliters"`). If the unit is missing, assume the value is already in milliliters.
7. **Summation** – convert each accepted value to `float` and accumulate a running total.
8. **Return** the total as a plain number (no extra formatting). If no matching observations are found, return `0`.

## Checks
- Verify the resource type is **Observation**.
- Confirm the normalized code contains the required output keywords.
- Ensure the observation date is on or after the start date derived from the question.
- Validate the numeric value can be parsed as a float.
- If a unit is present, check it is a milliliter‑type unit; otherwise discard the observation.
- Final answer must be a single numeric value (e.g., `34063.049`).

## Avoid
- Summing unrelated numeric observations (e.g., lab results, vital signs) that happen to contain a numeric value.
- Including observations with non‑volume units (e.g., `L`, `kg`, `mmHg`).
- Double‑counting the same observation due to multiple date fields.
- Returning an empty string or `None` when the correct answer is `0`.
- Relying solely on the presence of the word "output" without confirming a fluid‑related site keyword, which can capture unrelated codes.
