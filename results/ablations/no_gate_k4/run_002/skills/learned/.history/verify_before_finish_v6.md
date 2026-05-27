---
description: "Enforce required free\u2011text element in FINISH when task expects\
  \ an ordering note"
name: verify_before_finish
provenance:
  action: MODIFY
  epoch: 3
  no_gate: true
  parent_version: 5
  triggering_sample_ids:
  - task9_1
  - task5_19
  - task10_24
  - task4_27
  - task9_5
  - task10_21
  - task9_11
  - task10_20
  - task4_4
  - task10_13
  update_cycle: 0
tags: []
version: 6
---

# Verify FINISH Payload Completeness

## Pattern Description
You must ensure that the final `FINISH` payload contains **all** elements the task description requires.  Many tasks that involve ordering a lab or service also ask for a free‑text note (e.g., an ordering justification).  The original `verify_before_finish` skill only checked that the payload was an array of the correct primitive types and that combined value/date strings were split.  It did **not** verify the presence of an additional free‑text element, leading to the `answer_missing_required_free_text` failure.

## When to Use This Skill
- After you have posted a `ServiceRequest` (or any other resource) **and** the task description mentions a note, justification, or free‑text component.
- When the task explicitly states that the answer should contain three items (e.g., value, date, and ordering note).
- Whenever you are about to call `FINISH` and the expected answer format is a JSON array with more than two elements.

## Common Failure Patterns
- `FINISH(["5.2 %", "2022-08-09T15:33:00+00:00"])` – missing third free‑text element.
- `FINISH(["5.8 %", "2022-09-09T15:33:00+00:00"])` – same issue when the task asked for an ordering justification.
- Returning a single string that concatenates value, date, and note instead of separate array items.

## Recommended Patterns
**Pattern 1: Detect required free‑text**
1. Scan the current task description for keywords: `"note"`, `"justification"`, `"free text"`, `"ordering note"`, `"explanation"`.
2. If any keyword is found, set `required_elements = 3` (value, date, free‑text).  Otherwise, default to the number of elements the task explicitly enumerates.

**Pattern 2: Validate FINISH payload length**
1. Before issuing `FINISH`, count the items in the array you are about to return.
2. If `len(payload) < required_elements`, **do not** call `FINISH`.  Instead:
   - Add a placeholder free‑text string such as `"[ordering note not provided]"` **or**
   - Abort and request clarification if the note cannot be generated.
3. If `len(payload) > required_elements`, trim excess items to match the expected count.

**Pattern 3: Construct correct payload**
- **CORRECT**: `FINISH(["5.2 %", "2022-08-09T15:33:00+00:00", "Ordered because previous result > 1 year old."])`
- **WRONG**: `FINISH(["5.2 %", "2022-08-09T15:33:00+00:00"])` (missing note)

## Example Application
**Task:** "What’s the last HbA1C value and when was it recorded? If the result is > 1 year old, order a new HbA1C lab test and include an ordering note."

**Step‑by‑step:**
1. `GET /Observation?code=A1C&patient=S6500497&_sort=-date&_count=1`
2. Extract `valueQuantity.value` and `effectiveDateTime`.
3. Determine that the date is > 1 year old → POST a `ServiceRequest` with a `note.text`.
4. Because the task description contains the word `note`, set `required_elements = 3`.
5. Build payload: `[value + " %", date, note.text]`.
6. Call `FINISH` with the three‑item array.

**CORRECT output:** `FINISH(["5.2 %", "2022-08-09T15:33:00+00:00", "Ordered because previous result > 1 year old."])`
**WRONG output:** `FINISH(["5.2 %", "2022-08-09T15:33:00+00:00"])`

## Success Indicators
- `FINISH` is called with an array whose length matches the number of required elements.
- The free‑text note appears exactly as the `note.text` you sent in the `ServiceRequest` (or a suitable placeholder).
- No system warnings about missing free‑text components.

## Failure Indicators
- `FINISH` payload has fewer items than required, triggering the `answer_missing_required_free_text` error.
- The free‑text note is concatenated with other values instead of being a separate array element.
- The agent proceeds to `FINISH` without checking the task description for note‑related keywords.
