---
description: Query microbiology tests (Observation, Procedure, DiagnosticReport) for
  a patient, with optional date range and organism extraction.
name: microbiology_test_query
provenance:
  baseline_fixes: 5
  baseline_regressions: 3
  epoch: 0
  failure_mode: missing_microbiology_query
  fixes: 6
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - 031f4556ea1fe707a94f58bb
  - 04572e0972a7993db0621881
  - 0a0992495803104da30af972
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must use this skill whenever the user asks for **microbiology‑related information** about a patient, such as:
- The date of the last (or first) microbiology / serology / urine culture test.
- The organism(s) identified in a microbiology test (e.g., “first urine microbiology test since 02/2142”).
- Any request that mentions terms like *microbiology, culture, serology, blood, urine, csf, spinal fluid, specimen*.
If the question does not involve microbiology (e.g., medication, vital signs), do **not** invoke this skill.

## Procedure
1. **Retrieve resources** for the patient using `get_resources_by_patient_fhir_id` for the three FHIR types:
   - `Observation`
   - `Procedure`
   - `DiagnosticReport`
2. **Normalize text**: define `norm = lambda s: re.sub(r"\s+", " ", (s or "").strip().lower())`.
3. **Identify microbiology candidates**
   - For each resource, collect all display strings from `code.coding[*].display`, `code.coding[*].code`, and `code.text`.
   - A resource matches if the normalized concatenation contains **any** of the required keywords:
     - General microbiology: `"microbiology"`, `"culture"`, `"lab"`.
     - Site‑specific keywords (optional, used for organism queries): `"urine"`, `"csf"`, `"spinal fluid"`, `"blood"`, `"serology"`.
4. **Apply optional date filter**
   - If the user supplies a start date (e.g., "since 01/2115"), parse it to a `datetime`.
   - Discard any candidate whose effective date (`effectiveDateTime`, `issued`, or `effectivePeriod.start`) is **earlier** than the start date.
5. **Extract date**
   - For a *date‑only* query (e.g., “when was the last test”), collect the effective date of each matching resource.
   - Choose the **latest** date for "last" or the **earliest** date for "first" based on the question wording.
   - Return the date as an ISO‑8601 string with timezone stripped.
6. **Extract organism name** (only when the question explicitly asks for an organism)
   - From the selected resource (first matching after the start date), look for:
     - `valueCodeableConcept.coding[*].display` or `valueCodeableConcept.text`
     - Any `component[*].valueCodeableConcept.coding[*].display`
     - Any `component[*].valueString`
   - Return the first non‑empty organism name found. If multiple organisms are present, return them as a comma‑separated list.
7. **Return the answer**
   - For date queries: a single ISO‑8601 datetime string.
   - For organism queries: a plain string (or list) of organism names.

## Checks
- Verify that at least one resource of the three types was retrieved.
- Confirm that each candidate has a valid date field; skip those without.
- For organism extraction, ensure an organism field was actually found; otherwise answer "No organism reported".
- Ensure the answer type matches the request: date → string, organism → string/list.
- All dates must be returned in UTC‑neutral ISO format (e.g., `2024-05-12T14:30:00`).

## Avoid
- Do not treat unrelated laboratory observations (e.g., electrolytes, blood counts) as microbiology just because they contain the word "blood"; require a microbiology keyword.
- Do not return the whole resource; only the required piece of information.
- Do not ignore the optional start‑date filter – it is essential for queries like "since 02/2142".
- Do not return multiple dates; always pick the one that satisfies the "first"/"last" semantics.
- Do not assume the organism is in `valueString` only; check all possible fields listed above.
