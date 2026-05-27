---
description: "Provides the actual current datetime only when the user explicitly asks\
  \ for a \"now\"\u2011type value. This avoids overwriting user\u2011supplied reference\
  \ dates (e.g., \"since 02/2166\") that are needed for interval calculations."
name: dynamic_current_time
provenance:
  baseline_fixes: 1
  baseline_regressions: 3
  epoch: 13
  failure_mode: false_positive_result
  fixes: 3
  probe_score: 4
  regressions: 1
  triggering_sample_ids:
  - 02885cc1fb11efec74cb16fd
  - 06ba722e2ac0589ffacd1249
  - 0814561e80d18ee7b5e8e214
  - 09b1b086d491d385b6744dd6
  update_cycle: 0
tags: []
version: 1
---

## When to use
When a question explicitly requires the *current* moment (e.g., "how many days have passed **as of now**", "patient age **today**", "time since admission **up to now**").

## Procedure
1. **Detect a current‑time request** – Scan the user prompt for any of the following case‑insensitive cues:
   - "now"
   - "current time"
   - "today"
   - "as of now"
   - "up to now"
   - "to date"
   - "till today"
   - "present"
   If none of these cues are present, **do not** create a `CURRENT_TIME` variable and skip the rest of this skill.
2. **Parse an explicit hint** – If the prompt also contains a phrase like "Assume the current time is <ISO datetime>" (or similar), parse the ISO‑8601 string into a **timezone‑naïve** `datetime` (strip any offset) and store it as `CURRENT_TIME`.
3. **Fallback to real time** – Only when step 1 succeeded *and* no explicit hint was found, call `datetime.now()` (UTC), strip any tzinfo, and store the result as `CURRENT_TIME`.
4. **Expose `CURRENT_TIME`** – Make the variable available to downstream code. If step 1 failed, `CURRENT_TIME` is left undefined (or set to `None`).
5. **Compute results** – When the answer must be a scalar (hours, days, etc.), compute the difference between the relevant timestamp(s) and `CURRENT_TIME`, round per the question (default two decimal places). When the answer must be a datetime, format `CURRENT_TIME` (or the derived timestamp) as an ISO‑8601 string without timezone.

## Checks
- Ensure any other timestamps involved are also timezone‑naïve before comparison.
- Verify that the computed duration is non‑negative; if negative, treat the query as out‑of‑range and return `None` or the appropriate negative response.
- Confirm the final answer type matches the question’s expected format (plain number or ISO datetime).

## Avoid
- Using `CURRENT_TIME` when the user already supplied a concrete reference date (e.g., "since 02/2166").
- Mixing timezone‑aware and naïve datetimes.
- Returning a datetime string when a numeric duration is requested.

## Guard clause (to prevent regressions)
```python
import re
prompt = USER_PROMPT.lower()
needs_now = any(keyword in prompt for keyword in [
    'now', 'current time', 'today', 'as of now', 'up to now',
    'to date', 'till today', 'present'
])
if not needs_now:
    CURRENT_TIME = None  # skill does not activate
else:
    # proceed with steps 2‑5
```
