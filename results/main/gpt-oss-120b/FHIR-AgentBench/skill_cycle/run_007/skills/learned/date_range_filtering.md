---
description: Parse month/year, relative and offset date specifications and apply them
  as FHIR query filters
name: date_range_filtering
provenance:
  baseline_fixes: 3
  baseline_regressions: 3
  epoch: 13
  failure_mode: date_filter_global_incorrect
  fixes: 2
  probe_score: 2
  regressions: 0
  triggering_sample_ids:
  - 02a069698a803a8419fa294c
  - 0577ee51b3ad3c9fcf8fbbae
  - 05a9aa5bb494b962444ac354
  - 06c9202911fa52427beba085
  - 072f960a91e48e6fe38d81a1
  - 0d012e621517a4059d3caf10
  - 0d22269bdd7bfa8481b101b5
  update_cycle: 1
tags: []
version: 1
---

## When to use
Trigger this skill whenever a user question contains a temporal constraint that is expressed as a month/year (e.g., "04/2022", "04/this year", "04/last year"), a specific date range (e.g., "since 08/2142", "between 01/05/2180 and 15/05/2180"), a relative offset (e.g., "since 86 days ago", "in the last 2 months"), or any phrasing that requires limiting resources to a time window.

## Procedure
1. **Extract date expressions** from the question using regex patterns for:
   - `MM/YY` or `MM/YYYY`
   - `MM/this year` / `MM/last year`
   - `since X days ago`
   - `since DD/MM/YYYY`
   - `in the last N months`
   - explicit ranges like `between DD/MM/YYYY and DD/MM/YYYY`
2. **Normalize each expression**:
   - **Month‑only** (`MM/YY` or `MM/YYYY`):
     - `start = first day of month at 00:00:00`
     - `end   = last day of month at 23:59:59`
   - **Month with "this year"**: use the simulated current year.
   - **Month with "last year"**: use `current_year - 1`.
   - **"since X days ago"**: `start = current_simulated_date - X days`, `end = current_simulated_date`.
   - **Exact date with "since"**: `start = given date at 00:00:00`, `end = current_simulated_date`.
   - **"in the last N months"**: subtract N months from the current month, set `start` to the first day of that month, `end = current_simulated_date`.
   - **Explicit range**: parse both dates, set as `start` and `end` (time defaults to 00:00:00 for start, 23:59:59 for end).
3. Convert all dates to **timezone‑naive UTC** (strip any offset information).
4. **Attach the filter** to the FHIR query:
   - Identify the datetime field relevant to the resource type (`effectiveDateTime`, `authoredOn`, `period.start`, `period.end`, etc.).
   - Add `>= start` and `<= end` constraints.
   - If the resource contains multiple datetime fields, apply the filter to each until a non‑empty result set is obtained.
5. Execute the query and retrieve matching resources.

## Checks
- Ensure `start <= end`; if not, treat as an invalid request and return a clear error.
- Verify the chosen resource type actually has the datetime field being filtered; otherwise fall back to the next plausible field.
- After filtering, if no resources are found, answer with a standardized “No data” response.
- Preserve any required units, scalar formats, or answer‑type constraints defined by other skills (e.g., `answer_format_validation`).

## Avoid
- Mis‑interpreting the month component as a day (e.g., treating "04/2022" as April 2 2022).
- Ignoring the simulated current date when handling "this year", "last year", or relative offsets.
- Applying the date filter to non‑datetime fields such as identifiers or textual codes.
- Returning time components when the question explicitly asks for a date‑only answer; strip time after the filter is applied.
- Over‑filtering by adding both start and end when only a start bound is implied (e.g., "since 08/2142" should not impose an artificial end date beyond the current simulated time).
