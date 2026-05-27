---
description: When patient search returns 0 results, try alternative search parameters
  before concluding not found
name: patient_search_fallback_strategy
provenance:
  action: MODIFY
  epoch: 1
  fixes: 0
  parent_version: 1
  probe_score: 1
  regressions: 0
  triggering_sample_ids:
  - task9_1
  - task10_13
  - task2_26
  - task5_3
  - task10_27
  - task10_8
  - task9_28
  - task9_11
  - task9_14
  - task9_3
  update_cycle: 1
tags: []
version: 2
---

# Patient Search Fallback Strategy

## Pattern Description

When searching for a patient by identifier returns zero results, you must not immediately conclude the patient does not exist. The identifier format may not match the server's expected search parameter, or the identifier may be an MRN (Medical Record Number) that requires a different query approach. This skill provides a systematic fallback strategy to exhaust alternative search methods before reporting the patient as not found.

- Always verify the search response's `total` field. A `total: 0` or empty `entry` array means no matches, not necessarily that the patient is absent.
- The identifier format `S` followed by 7 digits (e.g., `S3241217`) is a common MRN pattern that may require searching with a system-qualified identifier or using a different search parameter.

## When to Use This Skill

- When a `GET /Patient?identifier=...` returns `total: 0` or an empty `entry` array
- When the identifier value looks like an MRN (e.g., starts with a letter followed by digits like `S3241217`)
- When the task provides a patient identifier but the initial search fails to find a match
- When constructing a resource reference and the patient ID is unknown

## Common Failure Patterns

- Searching with `identifier=S3241217` when the server expects `identifier=urn:oid:1.2.3.4.5|S3241217` or a system-qualified identifier
- Giving up after a single failed search instead of trying alternative parameters
- Using `identifier` parameter when the server stores the MRN in a different identifier system
- Not checking the `total` field in the response bundle before concluding no patient exists
- Skipping the patient search entirely and using the raw identifier string as a resource reference (e.g., `Patient/S3241217` without verifying it exists)

## Recommended Patterns

**Pattern 1: Primary search with identifier**
Start with the most direct search using the identifier as provided:
- `GET /Patient?identifier=S3241217`
- Check `bundle.total` — if > 0, extract the patient ID from `entry[0].resource.id`

**Pattern 2: Fallback — try identifier with system qualifier**
If the primary search returns 0 results, try a system-qualified identifier search. Common MRN systems include:
- `GET /Patient?identifier=http://hospital.example.org/fhir/identifier/mrn|S3241217`
- `GET /Patient?identifier=urn:oid:1.2.3.4.5|S3241217`
- Try the identifier value alone without any system prefix if the server supports it

**Pattern 3: Fallback — try name-based search**
If identifier-based searches all fail, try searching by name if the task provides any name context:
- `GET /Patient?family=Dunn&birthdate=1969-05-12`
- If no name is available, try a broader search like `GET /Patient?identifier=S3241217&_id=S3241217`

**Pattern 4: Final fallback — try direct resource read**
As a last resort, attempt a direct read using the identifier as the resource ID:
- `GET /Patient/S3241217`
- If this returns a 200 with a Patient resource, the identifier is the resource ID itself

## Example Application

**Task:** "Check patient S3241217's most recent potassium level."

**Step-by-step:**

1. Issue primary search: `GET /Patient?identifier=S3241217`
   - Response: `{ "resourceType": "Bundle", "total": 0, "entry": [] }`
   - Do NOT conclude patient not found yet.

2. Apply fallback — try system-qualified identifier:
   - `GET /Patient?identifier=http://hospital.example.org/fhir/identifier/mrn|S3241217`
   - If this returns a patient, extract the ID.

3. If still no results, try direct read:
   - `GET /Patient/S3241217`
   - If this returns a Patient resource, use `S3241217` as the patient ID.

4. If all fallbacks fail, then conclude patient not found.

CORRECT: After fallback, find patient and proceed with query
WRONG:   Immediately conclude patient not found after first failed search

## Success Indicators

- Agent attempts at least one fallback search before concluding patient not found
- Agent checks `bundle.total` in each response before deciding next action
- Agent successfully resolves patient ID and proceeds with the task

## Failure Indicators

- Agent gives up after a single failed identifier search
- Agent reports "patient not found" when the patient actually exists
- Agent uses the raw identifier string as a resource reference without verification
- Agent does not check the `total` field and misinterprets an empty bundle
