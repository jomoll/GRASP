---
description: Resolve MedicationReference IDs before any substring name matching on
  MedicationRequests.
name: medication_name_substring_match_enforcer
provenance:
  baseline_fixes: 4
  baseline_regressions: 2
  epoch: 12
  failure_mode: medication_reference_not_resolved_before_query
  fixes: 6
  parent_version: 3
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 047259e83745142834b50838
  - 059ed55281d42669ad25d514
  - 072f960a91e48e6fe38d81a1
  - 08e4e46ffbf10a71b11cc538
  - 0c6cdc444ee911941bfd23f0
  update_cycle: 1
tags: []
version: 4
---

## When to use
Trigger this skill for any question that searches medication names by substring (e.g., “milk of magnesia”, “glucose gel”, “iv route”) within MedicationRequest resources.

## Procedure
1. **Fetch MedicationRequests** for the target patient (already done by the main query).
2. **Collect medicationReference IDs**:
   ```python
   med_refs = {mr['medicationReference']['reference'].split('/')[-1]
               for mr in med_requests
               if mr.get('medicationReference',{}).get('reference','').startswith('Medication/')}
   ```
3. **Retrieve corresponding Medication resources** in a batch using `get_resources_by_resource_id` for each ID.
4. **Build a name lookup** mapping each Medication ID to a list of possible name strings extracted from the Medication resource:
   - `code.coding[].display`
   - `code.coding[].code`
   - `code.text`
   ```python
   name_lookup = {}
   for med in medications:
       mids = med.get('id')
       names = []
       for coding in med.get('code',{}).get('coding', []):
           if coding.get('display'): names.append(coding['display'])
           if coding.get('code'):    names.append(coding['code'])
       if med.get('code',{}).get('text'): names.append(med['code']['text'])
       if names:
           name_lookup[mids] = names
   ```
5. **Create candidate name lists for each MedicationRequest**:
   - If it has a `medicationReference`, pull names from `name_lookup`.
   - If it has a `medicationCodeableConcept`, also add its `coding.display`, `coding.code`, and `text` values.
6. **Normalize strings** for matching (lower‑case, collapse whitespace).
7. **Apply the original substring filter** using these resolved names instead of the raw reference IDs.
8. **Proceed with the rest of the original skill logic** (counting, boolean existence, aggregation, etc.).

## Checks
- Verify the resource type is `MedicationRequest`.
- Ensure at least one `medicationReference` was resolved; if none can be resolved, treat the request as having no matching medication.
- Confirm that name extraction produced non‑empty strings before performing substring checks.
- Validate the final answer matches the expected type (boolean, integer count, list of names, etc.).

## Avoid
- Matching directly against the reference string like `Medication/abcd‑1234`.
- Ignoring `medicationCodeableConcept` when a reference is absent.
- Performing case‑sensitive or whitespace‑sensitive matches.
- Proceeding with aggregation when the resolved name list is empty, which would yield incorrect defaults.
