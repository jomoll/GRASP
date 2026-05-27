---
description: "Ensures that a FHIR query for needed resource types is performed before\
  \ attempting to answer the question, but only issues a single query per turn and\
  \ defers answer generation until the data is available. This prevents malformed\
  \ multi\u2011call JSON and avoids answering before the required resources have been\
  \ retrieved."
name: require_fhir_query_before_answer
provenance:
  baseline_fixes: 6
  baseline_regressions: 4
  epoch: 1
  failure_mode: answer_not_generated_exception
  fixes: 7
  probe_score: 2
  regressions: 3
  triggering_sample_ids:
  - 00fbe516569113decea8de73
  - 0114a64085ec7d751f6e1bfd
  - 031f4556ea1fe707a94f58bb
  - 09469e7ae520d7c2a28ad15f
  - 0a36ca6e9f221dc69fc7f8de
  - 0d22f4703425e474ebd63580
  update_cycle: 0
tags: []
version: 1
---

## When to use
You should trigger this skill whenever the user asks for a value that comes from a specific FHIR resource (e.g., Observation, MedicationRequest, MedicationAdministration, Condition, Procedure, Encounter, etc.) and the agent has not yet issued a `get_resources_by_patient_fhir_id` (or `get_resources_by_resource_id`) call for that resource type.

Typical question patterns include:
- "When was the last ... test?"
- "What was the value of ... measured on ...?"
- "Has the patient received any ...?"
- "How many ... were prescribed ...?"
- Any query that mentions a clinical concept (lab, medication, procedure, diagnosis, encounter) without an explicit prior resource fetch.

## Procedure
1. **Parse the question** to extract keywords that map to FHIR resource types. Use a simple lookup table, e.g.:
   - Observation keywords: "test", "lab", "measurement", "value", "rate", "count", "culture", "microbiology", "sodium", "creatinine", etc.
   - MedicationRequest/MedicationAdministration keywords: "prescribed", "ordered", "given", "administered", "dose", "drug", "medication".
   - Condition keywords: "diagnosis", "disease", "condition", "disorder".
   - Procedure keywords: "procedure", "operation", "catheterization", "infusion", "surgery".
   - Encounter keywords: "visit", "hospital", "icu", "er", "admission", "discharge".
2. **Determine the required resource type(s)** based on the matched keywords.
3. **Check `retrieved_resources`** (the in‑memory store of previously fetched resources) for each required type.
4. If any required type is missing **and** no fetch for that type has already been issued in the current turn, **issue a single** `get_resources_by_patient_fhir_id` call for **the first missing type** (prioritising the order defined in step 1).
5. **Immediately stop further processing for this turn** – do not attempt to run any answer‑generation logic until the requested resources are returned. The system will invoke the agent again after the fetch, at which point the normal reasoning can proceed with the now‑available data.
6. On the subsequent turn, the normal answer‑generation flow runs as usual, now having the needed resources.

## Checks
- Verify that for every required resource type identified in step 2, either `retrieved_resources` already contains a non‑empty list **or** a fetch for that type has been issued in the current turn.
- Ensure that **only one** `get_resources_by_patient_fhir_id` call is made per turn.
- Confirm that the answer generation is deferred until after the fetch completes; the skill must not produce a final answer in the same turn it issues a fetch.
- Validate that the retrieved resources belong to the patient identified in the conversation context (match patient FHIR ID).

## Avoid
- Do not issue blanket queries for all resource types; only fetch the first missing type needed for the current question.
- Do not duplicate a query that has already been performed in the same turn.
- Do not answer before the required data is available; defer answer generation until after the fetch.
- Do not fetch unrelated resources that could cause unnecessary processing or privacy concerns.
