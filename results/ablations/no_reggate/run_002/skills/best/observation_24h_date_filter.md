---
description: "Enforces a 24\u2011hour date filter on Observation queries **only when\
  \ the task explicitly requests a recent (\u226424\u202Fh) measurement**. The skill\
  \ now activates solely on clear time\u2011window phrasing and when the expected\
  \ result includes a sentinel (e.g., `-1`) for \u201Cno recent value\u201D. This\
  \ prevents accidental filtering of queries that simply ask for the \u201Clast\u201D\
  \ observation (e.g., HbA1c) and restores correct handling of those cases."
name: observation_24h_date_filter
provenance:
  action: ADD
  epoch: 2
  fixes: 3
  probe_score: 4
  regressions: 0
  triggering_sample_ids:
  - task9_28
  - task9_27
  - task5_17
  - task9_8
  - task5_16
  - task9_11
  - task9_14
  - task5_7
  - task9_3
  - task9_5
  update_cycle: 0
tags: []
version: 1
---

# 24‑Hour Observation Date Filter Enforcement (Narrowed Trigger)

## Trigger Condition
Apply this skill **only** when **both** of the following are true:
1. The instruction contains **explicit 24‑hour time‑window language**, such as any of:
   - "within last 24 hours"
   - "in the past 24 h"
   - "past 24 hours"
   - "last 24 hours"
   - "within the last day"
   - "in the past day"
   - "within 24h"
2. The expected output mentions a **sentinel for missing data** (e.g., `-1`, `null`, or a specific “no value” phrase) indicating that the absence of a recent observation must be reported.

If either condition is missing, the skill **does not modify** the query.

---

## Pattern Description
When the trigger conditions are met, ensure that any `GET` request for an `Observation` resource respects a 24‑hour window, sorts newest‑first, and limits the response to a single entry.

## Recommended Query Construction
1. **Compute cutoff**: `cutoff = now - 24h` (use the task's provided current time if available).
2. **Build URL** (replace placeholders as appropriate):
   ```
   GET {base}/Observation?code={code}&patient={patient}&date=ge{cutoff}&_sort=-date&_count=1
   ```
   - If the server does not support `date`, fall back to `effectiveDateTime=ge{cutoff}` with the same sorting.
3. **Handle empty result**:
   - If the Bundle has `total == 0` or no `entry`, return the sentinel value (e.g., `-1`).
4. **Extract value** from the first entry’s `valueQuantity.value` (do not concatenate units) and convert units only if the task explicitly requires it.

## Guard Clause (Implementation Hint)
```python
if not any(kw in instruction.lower() for kw in [
    "within last 24 hours", "past 24 hours", "last 24 hours",
    "within the last day", "in the past day", "within 24h", "in the past 24 h"
]):
    # Do not apply 24h filter
    pass
elif not ("-1" in instruction or "no recent" in instruction.lower() or "sentinel" in instruction.lower()):
    # No sentinel requirement – skip filter
    pass
else:
    # Apply 24‑hour filter as described above
    ...
```

## Success Indicators
- The GET URL includes `date=ge{cutoff}` (or `effectiveDateTime=ge{cutoff}`) **only** for tasks meeting the trigger.
- The request contains `_sort=-date&_count=1`.
- The agent returns the sentinel (`-1` or prescribed phrase) when the Bundle is empty.
- No observation older than the cutoff is used.

## Failure Indicators
- The skill adds a date filter to a query that does **not** request a 24‑hour window (e.g., “last HbA1c”).
- The agent returns a value older than 24 h for a task that explicitly required a recent measurement.
- The sentinel is not returned when no recent observation exists.
