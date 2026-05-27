---
description: Block answering until all FHIR resources implied by the question have
  been queried.
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 3
  baseline_regressions: 2
  epoch: 11
  failure_mode: missing_fhir_query_before_answer
  fixes: 3
  parent_version: 6
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 01bb1845215fb7cc77678534
  - 0406ba9fa1c3ada7f76965a3
  - 065b726dbf86eb804accd168
  - 06b1eef22357320dc0f8a64a
  - 0814561e80d18ee7b5e8e214
  - 08e4e46ffbf10a71b11cc538
  - 0cf19476dc727db127ab20bf
  - 0d3343e3e64231d00abab91e
  update_cycle: 0
tags: []
version: 7
---

## When to use
You must run this skill for **any** question that refers to patient data (medications, labs, observations, procedures, encounters, specimens, outputs, etc.). The presence of domain‑specific keywords in the user query signals which FHIR resource types are required.

## Procedure
1. **Identify required resource types** by scanning the question for keyword groups:
   - *Medication* keywords: `medication`, `drug`, `prescribed`, `dose`, `administered`, `iv`, `po`, `ng`, `patch` → require `MedicationRequest`, `MedicationAdministration`, `Medication`.
   - *Lab/Observation* keywords: `lab`, `test`, `result`, `value`, `measurement`, `level`, `count`, `output`, `void`, `volume`, `amount`, `glucose`, `chloride`, `systolic`, `diastolic`, `respiratory rate`, `heart rate`, `oxygen`, `weight` → require `Observation`.
   - *Procedure* keywords: `procedure`, `repair`, `surgery`, `operation`, `graft`, `prosthesis` → require `Procedure`.
   - *Encounter* keywords: `encounter`, `visit`, `admission`, `discharge`, `hospital`, `er`, `emergency`, `icu`, `icu visit`, `hospital stay` → require `Encounter`.
   - *Specimen/Culture* keywords: `specimen`, `culture`, `microbiology`, `mrsa`, `test` when paired with `specimen` → require `Specimen`.
   - *Output* keywords: `output`, `void`, `volume`, `amount` → treat as `Observation`.
2. **Inspect the agent's action log** (the sequence of tool calls made before the final answer). For each required resource type, confirm that a tool call of the form `get_resources_by_patient_fhir_id` or `get_resources_by_resource_id` with that `resource_type` appears **prior** to any answer‑producing step.
3. If **any** required resource type is missing, abort the current answer flow and invoke the `answer_fallback` skill (or return a safe placeholder like "Insufficient data – no answer generated").
4. If all required resources are present, allow the answer to proceed unchanged.

## Checks
- Verify that the question contains at least one keyword from the lists above; otherwise, the skill does nothing.
- Ensure that for each identified resource type there is a corresponding `get_resources_by_*` call in the action trace before the final answer.
- The check must be performed **before** any formatting or post‑processing of the answer.
- The fallback must respect the expected answer type (boolean, numeric, date, list, dict) as enforced by `answer_format_enforcement`.

## Avoid
- Answering based solely on internal reasoning or hard‑coded defaults when no FHIR data has been fetched.
- Over‑rejecting answers when the question is generic and does not require a specific resource (e.g., "What is the average age of patients?"), because such queries are outside the scope of this skill.
- Mis‑classifying a keyword and demanding a resource that is not actually needed (e.g., treating the word "dose" in a non‑medication context as a medication request).
