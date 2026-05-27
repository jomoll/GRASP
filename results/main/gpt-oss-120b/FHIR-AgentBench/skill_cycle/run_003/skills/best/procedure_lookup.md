---
description: "Detects and answers procedure\u2011related queries for a patient. The\
  \ skill only activates when the user explicitly asks about a medical **procedure**\
  \ (e.g., surgery, catheterization, infusion, biopsy, transplant, etc.). It then\
  \ retrieves Procedure resources, filters them, and returns a distilled answer (yes/no,\
  \ date, or count)."
name: procedure_lookup
provenance:
  baseline_fixes: 3
  baseline_regressions: 4
  epoch: 0
  failure_mode: no_fhir_query_executed
  fixes: 3
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - 0063d54603cf0f791a4f2d03
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill **only** when the question satisfies **both** of the following conditions:
1. The question contains a patient identifier (e.g., "patient 10001234" or a FHIR patient ID).
2. The question contains at least one procedure‑specific keyword. Acceptable keywords (case‑insensitive, whole‑word match) include:
   - procedure, operation, surgery, catheter, catheterization, angiography, biopsy, transplant, infusion, dialysis, endoscopy, resection, excision, implant, stent, laser, ablation, excision, graft, repair, removal, removal of, placement, removal of, removal, removal of, removal of
   - Common procedure names such as "right heart cardiac catheterization", "laparoscopic robotic assisted", "enteral infusion", etc.
If either condition is missing, **do not** fire this skill (return `None`).

## Procedure
1. **Normalize the target phrase** – Extract the procedure name(s) from the question, lower‑case, collapse whitespace, and store as `target`.
2. **Retrieve Procedure resources** – Call `get_resources_by_patient_fhir_id` with `resource_type="Procedure"` and the patient’s FHIR ID.
3. **Filter candidates** – For each Procedure `p`:
   - Check `p.code.coding[*].display` and `p.code.text` for a match to `target` (exact after normalization) **or** perform a partial match where any token of `target` appears in the display/text.
   - If the question mentions a date range (e.g., "since 01/02/2150", "in 10/this year"), parse the range and keep only procedures whose `performedDateTime` or `performedPeriod.start` falls inside the range.
4. **Derive the answer** based on the question type:
   - **Existence (yes/no)** – If any candidate remains, answer "Yes"; otherwise "No".
   - **First/last date** – Sort candidates by the relevant datetime and return the ISO‑8601 string of the earliest or latest.
   - **Count** – Return the integer count of matching procedures.
5. **Return only the distilled answer** (plain text, ISO‑8601 date, or integer). Do not return raw FHIR resources.

## Checks
- Ensure at least one `Procedure` resource was retrieved; if none, answer "No" for existence queries.
- Respect time‑zone offsets by stripping them before comparison.
- When a date window is supplied, enforce `start <= candidate <= end`.
- Verify that the answer type matches the question (boolean, date string, or integer) before responding.

## Guard clause (pre‑condition)
```python
import re
question_lc = question.lower()
procedure_keywords = r"\b(procedure|operation|surgery|catheter|catheterization|angiography|biopsy|transplant|infusion|dialysis|endoscopy|resection|excision|implant|stent|laser|ablation|graft|repair|placement|removal)\b"
if not re.search(procedure_keywords, question_lc):
    # Not a procedure‑related query – do not activate this skill
    return None
```

## Avoid
- Forgetting the `get_resources_by_patient_fhir_id` call.
- Matching only on exact string equality; always normalize and allow partial matches.
- Ignoring `performedPeriod` when `performedDateTime` is absent.
- Returning raw FHIR resources.
- Scoping procedures to an Encounter unless the question explicitly mentions an encounter.

## Tags
[]
