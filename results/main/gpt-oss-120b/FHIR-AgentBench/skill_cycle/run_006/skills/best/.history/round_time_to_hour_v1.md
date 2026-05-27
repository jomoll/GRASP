---
description: "Round datetime answers to the nearest hour before responding to time\u2011\
  based questions."
name: round_time_to_hour
provenance:
  baseline_fixes: 5
  baseline_regressions: 2
  epoch: 1
  failure_mode: answer_time_not_rounded_to_hour
  fixes: 6
  probe_score: 1
  regressions: 2
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 0874a8eb9ae4f8b6bb50a1d4
  - 098b1301820b7d581a339d0f
  update_cycle: 0
tags: []
version: 1
---

## When to use
Trigger this skill whenever the user asks for a point‑in‑time answer (e.g., "When was …?", "What time did …?", "First prescribed … at what time?") and the agent has extracted a full ISO‑8601 datetime string that includes minutes, seconds, or sub‑second components. The expected answer format for these questions is hour‑precision only.

## Procedure
1. **Detect datetime output** – After the retrieval, filtering and reasoning steps, check if the provisional answer is a string that can be parsed by `datetime.fromisoformat` (or `dateutil.parser.isoparse`).
2. **Parse the datetime** – Convert the string to a `datetime` object, preserving any existing timezone information.
3. **Round to the nearest hour**
   - If `dt.minute >= 30` then `dt = dt + timedelta(hours=1)`.
   - Set `dt = dt.replace(minute=0, second=0, microsecond=0)`.
   - If the addition pushes the hour to 24, let `datetime` handle the day overflow automatically.
4. **Re‑format** – Convert the rounded `datetime` back to an ISO‑8601 string using `dt.isoformat()`.
5. **Replace the provisional answer** with the rounded string before any final formatting (e.g., adding surrounding text).

## Checks
- Verify the resource type is irrelevant; only the answer value matters.
- Ensure the original answer was a valid datetime; if parsing fails, leave the answer unchanged.
- Confirm the final string contains exactly the pattern `YYYY‑MM‑DDTHH:00:00` (optionally with a timezone offset).
- Do not round if the question expects a date only (no time) or a duration.

## Avoid
- Rounding dates that are already hour‑exact (e.g., `2023-05-01T14:00:00`).
- Altering non‑datetime answers such as medication names, numeric counts, or boolean values.
- Stripping or changing timezone offsets; keep the original offset if present.
- Applying the skill to questions that explicitly request a full timestamp with minutes/seconds (rare but possible).
