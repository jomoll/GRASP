---
description: "Guarantee the agent extracts needed data and finishes with a proper\
  \ answer after any GET request, **but only for tasks that expect a raw numeric,\
  \ boolean, or ISO\u2011datetime answer** (e.g., patient age, lab values, observation\
  \ dates). This prevents the rule from interfering with queries that expect arbitrary\
  \ string identifiers such as MRNs."
name: ensure_answer_after_query
provenance:
  action: ADD
  epoch: 0
  fixes: 15
  probe_score: 15
  regressions: 0
  triggering_sample_ids:
  - task5_16
  - task9_1
  - task2_25
  - task10_27
  - task4_26
  - task4_27
  - task10_18
  - task1_20
  - task9_6
  - task9_28
  update_cycle: 1
tags: []
version: 1
---

## Ensure Answer After Data Query (Numeric/Datetime Only)

### When to Apply
- The user asks for a **numeric** value (integer or float) or an **ISO‑datetime** (e.g., age, potassium level, HbA1c, observation date).
- The task explicitly states a fallback numeric sentinel (e.g., `-1` when missing) or a date format.
- **Do NOT apply** when the expected answer is an arbitrary **string identifier** (e.g., MRN, patient name) or a free‑text message.

### Core Extraction Pattern
1. **After a GET response** arrives, inspect the top‑level `resourceType` and `total` fields.
2. If `total == 0`:
   - For numeric labs with a sentinel, set `answer = -1`.
   - For date queries, set `answer = ""` (empty string) or the task‑specified sentinel.
3. If `total > 0`:
   - Locate the first entry: `entry[0].resource`.
   - **Patient age**: read `birthDate`, compute `age = floor((now - birthDate) / 365.25 days)`.
   - **Lab value**: read `valueQuantity.value` (numeric) and, if needed, convert units.
   - **Observation date**: read `effectiveDateTime`.
4. Apply any required unit conversion **before** formatting.
5. **Immediately** call `FINISH([<answer>])` where `<answer>` is a raw number, boolean, or ISO‑datetime string.

### Fallback When Expected Field Is Missing
- If the expected field (`birthDate`, `valueQuantity.value`, `effectiveDateTime`) is absent, treat it as missing and follow step 2.

### Formatting Rules
- Return a JSON‑compatible list with **no explanatory text**.
  - `FINISH([42])` for an integer.
  - `FINISH([3.5])` for a float.
  - `FINISH(["2023-10-01T12:00:00+00:00"])` for a datetime.
- Do **not** wrap the answer in sentences or additional strings.

### Guard Clause (String‑Answer Tasks)
If the task description indicates the answer should be a **string identifier** (e.g., MRN, patient name) or contains phrases like "return \"Patient not found\"", **skip** this skill. Let the normal reasoning flow issue the GET request, parse the response, and produce a `FINISH(["<string>"])` manually.

### Success Indicators
- A `FINISH` call appears immediately after the GET response.
- The value inside `FINISH` matches the expected numeric or datetime type.
- No extra explanatory text is present.

### Failure Indicators
- The agent ends the turn with only reasoning and no `FINISH`.
- The answer list contains a sentence or extra characters.
- The agent returns a sentinel when a valid measurement exists, or vice‑versa.
- The skill fires on a task that expects a string identifier (e.g., MRN), causing the agent to skip the necessary GET.

---
*This revised rule keeps the original benefit of forcing a complete answer after data retrieval while adding a guard to avoid interfering with tasks that require string identifiers such as MRNs.*
