---
description: "Improve medication name and date\u2011filter detection for MedicationRequest\
  \ queries"
name: medicationrequest_query
provenance:
  baseline_fixes: 2
  baseline_regressions: 3
  epoch: 5
  failure_mode: medicationrequest_not_queried
  fixes: 2
  parent_version: 4
  probe_score: 2
  regressions: 1
  triggering_sample_ids:
  - 00249e27093cdde779012293
  - 00c6c1102d545178bf7380f3
  - 05a9aa5bb494b962444ac354
  update_cycle: 1
tags: []
version: 5
---

## When to use
Trigger this skill for any user question that asks whether a specific drug (or class of drugs) was prescribed, the dose of a drug, the route of administration, or the timing of a prescription. The question must contain a medication name (including synonyms, trade names, abbreviations, dosage forms such as “liquid”, “gel”, “flush”, “solution”, “IV drip”, “PO/NG”, etc.) **and** a temporal constraint (e.g., “since 03/2178”, “in 05/2137”, “last hospital encounter”, “first hospital visit”).

## Procedure
1. **Parse the question**
   - Lower‑case the text and split on punctuation.
   - Identify candidate medication tokens using a whitelist of common substrings (e.g., `docusate`, `acetaminophen`, `lidocaine`, `heparin`, `glucose`, `gel`, `soln`, `flush`, `iv drip`, `po/ng`).
   - Expand each token with known synonyms from a small built‑in map (e.g., `soln` → `solution`, `gel` → `gel`, `flush` → `flush`).
   - Detect a date filter: look for patterns `since <date>`, `in <month>/<year>`, `<year>`, `<month>/<year>` or relative phrases like “last hospital encounter”. Convert the extracted date to a Python `datetime` (default to the start of the month when only month/year are given).
2. **Build the FHIR query**
   - Call `get_resources_by_patient_fhir_id` with `resource_type="MedicationRequest"`.
   - After retrieval, filter the list in Python:
     a. **Medication name match** – for each `MedicationRequest`:
        - If `medicationCodeableConcept` exists, collect all `coding.display`, `coding.code`, and the top‑level `text`. Normalise by removing extra whitespace and lower‑casing.
        - If any of those strings contain **all** tokens of the candidate medication (allow partial matches, e.g., `docusate sodium` matches `docusate sodium (liquid)`), consider it a match.
        - If the request only contains a `medicationReference`, defer name resolution: store the referenced Medication ID for a secondary lookup.
     b. **Date filter** – keep the request only if `authoredOn` or `dateWritten` (or `recordedDate` if present) is ≥ the parsed start date.
3. **Resolve medicationReference when needed**
   - For any matched request that still lacks a name, fetch the referenced `Medication` resource via `get_resources_by_resource_id` and extract the first available `code.coding.display`, falling back to `code.coding.code` or `title`.
4. **Compose the answer**
   - If the original question asks for a **yes/no** (e.g., “Has … been prescribed?”), return "Yes" if any filtered request exists, otherwise "No".
   - If the question asks for the **first/last** prescription, sort the filtered requests by the parsed date field and return the ISO‑8601 timestamp of the appropriate record.
   - If the question asks for the **drug name**, return the resolved name of the earliest matching request.
   - If the question asks for a **dose total** or **dose of a specific administration**, sum the `doseQuantity.value` fields across the filtered requests (handling both `doseAndRate` and top‑level `doseQuantity`).
5. **Handle empty results**
   - When no MedicationRequest satisfies both name and date criteria, answer with a clear statement such as "No matching medication found for the requested period".

## Checks
- Verify that at least one `MedicationRequest` resource was retrieved for the patient.
- Confirm that the medication name matching used normalized strings and that **all** tokens from the query appear in the resource name (order‑agnostic).
- Ensure the date comparison uses timezone‑agnostic `datetime` objects.
- If a `medicationReference` is used, confirm the secondary `Medication` fetch succeeded before extracting the name.
- Answer format must match the question type (Yes/No, ISO‑8601 timestamp, drug name string, numeric dose total).

## Avoid
- Matching on a single generic token (e.g., matching "gel" to any medication containing the word "gel" unrelated to the query).
- Ignoring the temporal constraint; never return a medication that falls outside the requested window.
- Returning a `Medication` identifier instead of the human‑readable drug name.
- Selecting the **maximum** value when the question asks for the **first** or **last** occurrence.
- Assuming the presence of `authoredOn`; fall back to `dateWritten` or `recordedDate` when needed.
