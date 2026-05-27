---
description: "Extract MRN from a FHIR Patient search bundle, handling not\u2011found\
  \ cases correctly. Only activates when the user explicitly requests the MRN."
name: patient_mrn_lookup
provenance:
  action: MODIFY
  epoch: 2
  fixes: 13
  parent_version: 1
  probe_score: 4
  regressions: 2
  triggering_sample_ids:
  - task1_27
  - task10_20
  - task10_27
  - task9_28
  - task9_27
  - task1_10
  - task9_8
  - task8_13
  - task9_11
  - task1_7
  update_cycle: 0
tags: []
version: 2
---

# Patient MRN Lookup from FHIR Search (guarded)

## Trigger Guard
- This skill should only run when the **current user request or task description** contains the phrase "MRN" (case‑insensitive) or "Medical Record Number".
- If the guard is not satisfied, the skill must **do nothing** (i.e., let the normal task flow continue) and must **not call FINISH**.

## Core Extraction (executed only when guard passes)
1. Verify the response is a `Bundle` and `bundle.type == "searchset"`.
2. If `bundle.total == 0` → `FINISH(["Patient not found"])`.
3. Otherwise, take the first entry: `patient = bundle.entry[0].resource`.
4. Scan `patient.identifier` for an object where any `type.coding[*].code` matches one of:
   - "MR"
   - "MRN"
   - a system URL you use for MRNs (e.g., `http://hospital.org/mrn`).
5. If a matching identifier is found, extract its `value` as `mrn` and `FINISH([mrn])`.
6. **Fallback**: if no matching identifier is found but `patient.identifier` is non‑empty, use the first identifier's `value`.
7. If the identifier array is empty, treat as not‑found → `FINISH(["Patient not found"])`.

## Output Formatting
- Return the result as a **single‑element JSON array** containing either the MRN string or the literal "Patient not found".
- No extra wording, no surrounding sentences.

## Example Guard Usage
- User asks: "What’s the MRN of the patient with name Tina Reid and DOB of 1953-10-18?"
  - Guard matches → skill runs and returns `FINISH(["Patient not found"])` if bundle is empty.
- User asks: "What’s the last HbA1C value for patient S0789363?"
  - Guard does **not** match → skill does nothing, allowing the normal HbA1C workflow to proceed.

## Failure Indicators (unchanged)
- The agent returns an empty array or extra text.
- The skill runs on requests that do not ask for an MRN.

## Success Indicators (unchanged)
- `FINISH` is called with a single‑element array containing the MRN or "Patient not found" **only** when the MRN request guard is satisfied.
