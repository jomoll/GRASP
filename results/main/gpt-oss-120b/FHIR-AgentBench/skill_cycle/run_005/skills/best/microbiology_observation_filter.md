---
description: "Select only true microbiology observations and extract organism names\
  \ for microbiology\u2011related questions."
name: microbiology_observation_filter
provenance:
  baseline_fixes: 2
  baseline_regressions: 4
  epoch: 11
  failure_mode: answer_not_generated_exception
  fixes: 3
  probe_score: 3
  regressions: 2
  triggering_sample_ids:
  - 0702bc77d929f78085010bb0
  - 081ba7feccd490013f102984
  - 0b9e619bdb576876f002d49a
  update_cycle: 1
tags: []
version: 1
---

## When to use
You must run this skill whenever the question explicitly asks about a microbiology test, organism identification, or any observation that is a laboratory microbiology result (e.g., pleural fluid culture, urine culture, blood culture, serology, CSF microbiology, etc.). The skill triggers on queries that contain keywords such as "culture", "microbiology", "organism", "gram stain", "urine test", "csf", "spinal fluid", "pleural fluid", "serology", "blood test" combined with a specimen type.

## Procedure
1. **Retrieve Observations** – Ensure that `Observation` resources for the patient have already been fetched.
2. **Identify microbiology observations**:
   - Keep an observation if **any** of the following is true:
     - The `category` array contains a `CodeableConcept` whose coding `display` or `code` (case‑insensitive) includes the word *microbiology*.
     - The `code.coding` includes a known microbiology LOINC code (e.g., `630‑0`, `629‑2`, `740‑5`, `743‑9`, `740‑5`, `628‑4`, `629‑2`, `630‑0`, `742‑1`, `744‑7`, etc.).
     - The `code.coding.display` or `code.text` contains keywords like *culture*, *gram stain*, *organism*, *microbiology*, *urine*, *csf*, *spinal fluid*, *pleural fluid*, *serology* (case‑insensitive).
   - Exclude observations that only mention the keyword in a free‑text note but whose `code` is unrelated (e.g., vital signs, imaging).
3. **Match specimen type (optional)** – If the question mentions a specimen (e.g., "pleural fluid", "urine", "csf"), further filter observations where:
   - `specimen` reference points to a `Specimen` resource whose `type.coding.display` or `type.text` matches the specimen keyword, **or**
   - The observation `code.coding.display` or `code.text` explicitly includes the specimen keyword.
4. **Extract organism name**:
   - First, look for `valueCodeableConcept.coding.display` or `valueCodeableConcept.coding.code`.
   - If not present, inspect each component's `valueCodeableConcept` for a display containing the organism.
   - Return the first non‑empty organism name found.
5. **Order by date** – Use `effectiveDateTime` or `effectivePeriod.start` to sort matching observations chronologically; for "last" or "most recent" queries pick the newest, for "first" pick the earliest.

## Checks
- Verify that the resource type is `Observation`.
- Confirm at least one microbiology‑category or LOINC match before proceeding.
- Ensure the observation is linked to the relevant encounter (if the question scopes to a specific encounter) by matching `encounter.reference`.
- Validate that an organism name was actually extracted; if none, answer "No organism identified" rather than leaving the answer empty.
- Output must be a plain string containing the organism name (or "No organism identified").

## Avoid
- Do not select observations whose only keyword match is in a free‑text note or comment field.
- Do not return values from non‑microbiology labs (e.g., chemistry, hematology, vital signs).
- Do not assume the first component is the organism; scan all components.
- Do not ignore the encounter scope – if the question limits to a specific hospital visit, restrict to observations whose `encounter` matches that visit.
- Do not output `null` or an empty string; always return a meaningful statement as described in Checks.
