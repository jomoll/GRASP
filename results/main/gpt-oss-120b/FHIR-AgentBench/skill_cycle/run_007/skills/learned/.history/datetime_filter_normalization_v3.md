---
description: "Strip time from ISO\u2011datetime answers when the question asks for\
  \ a date only."
name: datetime_filter_normalization
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 5
  failure_mode: datetime_format_mismatch
  fixes: 4
  parent_version: 2
  probe_score: 2
  regressions: 2
  triggering_sample_ids:
  - 024e5c4760ca03ad0215c516
  - 031f4556ea1fe707a94f58bb
  - 03e018e5065829295de0817f
  - 04572e0972a7993db0621881
  update_cycle: 0
tags: []
version: 3
---

## When to use
You must apply this skill whenever the user question is looking for a **date** (e.g., it contains phrases like "when did", "when was", "last", "first", "since", "on", "date of", "date") **and does not explicitly request a time** (no words like "at", "hour", "minute", "seconds", "time" or a ':' character). In such cases the data source may return an ISO‑datetime string (e.g., `2024-05-20T14:33:00`).

## Procedure
1. Retrieve the original user question as the variable `question` (lower‑case it for matching).
2. Determine if the question is date‑only:
   - Set `date_keywords = ["when did", "when was", "last", "first", "since", "on", "date of", "date"]`.
   - Set `time_keywords = ["at", "hour", "minute", "seconds", "time", ":"]`.
   - If any keyword from `date_keywords` appears in `question` **and** none of the `time_keywords` appear, treat the query as date‑only.
3. Examine the provisional answer stored in the variable `answer`:
   - If `answer` is a string and matches the regex `^\d{4}-\d{2}-\d{2}T` (ISO‑datetime), split it at the first `'T'` and keep the left part (the date).
   - Replace `answer` with this date‑only string.
4. Pass the (potentially modified) `answer` forward to the next skill or final output.

## Checks
- Ensure `answer` is a string before applying the regex.
- Confirm the regex matched (i.e., a `'T'` separator is present).
- After stripping, verify the result matches `^\d{4}-\d{2}-\d{2}$`.
- Do **not** modify the answer if the question was identified as time‑specific in step 2.

## Avoid
- Removing the time component when the question explicitly asks for a timestamp (e.g., "at what time", "what time", contains a colon, or includes time‑related keywords).
- Changing answers that are already date‑only or that are not ISO‑datetime strings.
- Applying the skill to non‑date queries such as numeric, boolean, or free‑text answers.
