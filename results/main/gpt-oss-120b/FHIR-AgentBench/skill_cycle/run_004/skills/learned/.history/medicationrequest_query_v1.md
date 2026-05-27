---
description: "Fetch and filter MedicationRequest resources before answering any medication\u2011\
  related question. This skill now activates only when the user explicitly mentions\
  \ a medication\u2011specific term, preventing accidental triggering on unrelated\
  \ queries such as ICU stay length or PO\u2082 observations."
name: medicationrequest_query
provenance:
  baseline_fixes: 1
  baseline_regressions: 5
  epoch: 0
  failure_mode: medicationrequest_not_queried
  fixes: 4
  probe_score: 6
  regressions: 2
  triggering_sample_ids:
  - 062575cdb38e709723edbb54
  - 08e4e46ffbf10a71b11cc538
  - 0a8c46b684e72300d29c18aa
  - 0cd11d35e8ac3515e3c55d6c
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill **only** when the user question contains at least one medication‑specific keyword. The keyword list is:
- medication, drug, prescription, dose, dosage, route, administered, administration, Rx, tablet, capsule, infusion, drip, patch, inhalation, oral, IV, IM, subcutaneous, PO, PR, topical, "prescribed", "ordered", "given", "started", "stopped", "changed".
If none of these terms appear, do **not** invoke this skill – let other skills handle the query.

## Procedure
1. **Identify patient** – extract the patient identifier (numeric ID or FHIR ID) from the query context.
2. **Guard clause – confirm medication intent** – after extracting the patient ID, scan the original user question for any of the keywords above (case‑insensitive). If no keyword is found, abort the skill and return a special signal (e.g., `SKILL_NOT_APPLICABLE`).
3. **Retrieve resources** – call `get_resources_by_patient_fhir_id` with `resource_type="MedicationRequest"` for the identified patient.
   - If the question also refers to actual administrations (e.g., "was the medication given"), also retrieve `MedicationAdministration` resources.
4. **Initial validation** – if no MedicationRequest resources are returned, respond with "No medication orders found for this patient."
5. **Filter by date** – when the query includes a temporal constraint (e.g., "since 05/2137", "last hospital visit", "first prescription"), parse the dates and keep only records whose `authoredOn` (or `dateWritten` if `authoredOn` missing) fall inside the specified window.
6. **Filter by route** – if a route is specified (e.g., "PO", "NG", "IV drip", "inhalation"), inspect the `dosageInstruction[*].route.coding[*].display` or `text` fields for a case‑insensitive match.
7. **Filter by drug name** – when a specific drug is asked for, normalize the target name (lower‑case, collapse whitespace) and compare it to the `medicationCodeableConcept.coding[*].display`, `code`, or the referenced `Medication` resource name (if `medicationReference` is present, you may need a secondary lookup; for this skill assume the display is sufficient).
8. **Select the requested record** – depending on the phrasing, choose:
   - *last*, *most recent*: sort by `authoredOn` descending and pick the first.
   - *first*: sort ascending and pick the first.
   - *any*: return the first match.
   - *count* or *list*: aggregate as required.
9. **Extract answer fields** – retrieve the needed fields (drug name, dose amount, unit, route, date) from the selected MedicationRequest.
10. **Format the answer** – present the result in the style requested (e.g., just the drug name, "Yes/No", a date string, or a JSON list).

## Checks
- Verify that the patient FHIR ID matches the one used in the query.
- Ensure at least one MedicationRequest (or MedicationAdministration when requested) was retrieved before proceeding.
- Confirm that any date filters are correctly applied (inclusive of start/end dates).
- When a route filter is present, make sure the matching is case‑insensitive and ignores surrounding whitespace.
- Validate that the final answer conforms to the expected format (string, date‑time ISO, boolean, or numeric list) before returning it.

## Avoid
- Forgetting to query MedicationRequest resources (the primary cause of the `medicationrequest_not_queried` failure).
- Using only `MedicationAdministration` when the question is about prescriptions.
- Ignoring temporal constraints or route specifications, which leads to incorrect or ambiguous answers.
- Returning raw FHIR IDs instead of human‑readable drug names unless explicitly asked.
- Providing an answer when the filtered result set is empty; instead, return a clear "No matching medication found" message.
- Triggering this skill on non‑medication queries – the guard clause in step 2 prevents that.
