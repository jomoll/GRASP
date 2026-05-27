---
description: Extract organism name from microbiology Observation resources (culture,
  urine, pleural, CSF, etc.).
name: observation_organism_extraction
provenance:
  baseline_fixes: 4
  baseline_regressions: 3
  epoch: 11
  failure_mode: organism_observation_not_extracted
  fixes: 2
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - 0702bc77d929f78085010bb0
  - 09b1b086d491d385b6744dd6
  - 0a0992495803104da30af972
  update_cycle: 1
tags:
- observation
- microbiology
- organism_extraction
version: 1
---

## When to use
You must activate this skill whenever the user asks for the **organism** identified in a microbiology test (e.g., culture, urine, pleural fluid, CSF, sputum) for a specific patient, optionally qualified by an encounter, date range, or "first/last" qualifier.

## Procedure
1. **Ensure a FHIR query** for `Observation` resources for the target patient has been executed (use `ensure_fhir_query_executed` if needed).
2. **Filter observations** to those that are microbiology‑related:
   - The observation `code.coding.display` or `code.coding.code` contains any of the keywords `culture`, `micro`, `gram`, `pcr`, `organism` (case‑insensitive).
   - Optionally also check `category.coding.display` for similar keywords.
   - If the question mentions a specific body fluid (e.g., *pleural*, *urine*, *csf*, *spinal fluid*), require the same keyword to appear in the code display or in a `bodySite` coding display.
   - If an encounter is specified, keep only observations whose `encounter.reference` ends with the matching Encounter ID.
   - If a date range or "first/last" qualifier is present, sort the remaining observations by `effectiveDateTime` (or `issued`/`effectivePeriod.start` as fallback) and keep the appropriate one (earliest for *first*, latest for *last*).
3. **Extract the organism name** from the chosen observation:
   - If the observation has a top‑level `valueString`, use its trimmed content.
   - Else if it has a top‑level `valueCodeableConcept`, use the first coding's `display` or `code`.
   - Else iterate over `component` entries:
     - For each component, if its `code.coding.display` (or `code`) contains the word **organism** (case‑insensitive), then:
       * Prefer `valueString` if present.
       * Otherwise, if `valueCodeableConcept` exists, use its first coding's `display` or `code`.
   - Stop at the first non‑empty organism value found.
4. **Return the organism name** as a plain string. If no organism value is found after the above steps, answer with the phrase `Organism name not found`.

## Checks
- Verify that at least one Observation resource matched the microbiology filter; if none, answer `No microbiology observation found` (or the appropriate “no data” phrasing).
- Ensure the extracted organism value is a non‑empty string before returning.
- The answer must be a plain text string (no JSON, no extra wording) matching the expected answer type.

## Avoid
- Returning a generic “No data” when a microbiology observation exists but the organism field is nested in a component.
- Selecting observations that are merely laboratory panels unrelated to microbiology (e.g., electrolyte panels) – rely on the keyword filter above.
- Ignoring the encounter or date qualifier supplied in the question; always respect those constraints before picking the observation.
- Including units, timestamps, or other observation fields in the final answer – only the organism name should be returned.
