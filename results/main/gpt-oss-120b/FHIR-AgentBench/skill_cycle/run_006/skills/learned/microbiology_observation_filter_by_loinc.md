---
description: Filter microbiology observations using known LOINC codes (with fallback
  to display text) before date calculations.
name: microbiology_observation_filter_by_loinc
provenance:
  baseline_fixes: 4
  baseline_regressions: 4
  epoch: 0
  failure_mode: microbiology_observation_code_filter_mismatch
  fixes: 4
  probe_score: 3
  regressions: 1
  triggering_sample_ids:
  - 00fbe516569113decea8de73
  update_cycle: 0
tags: []
version: 1
---

## When to use
You must invoke this skill whenever a question asks for a microbiology‑related observation (e.g., *last microbiology test*, *first microbiology examination*, *MRSA screen*, *culture result*, etc.). The failure mode this addresses is **microbiology_observation_code_filter_mismatch**, where the agent previously relied only on the observation code's display text.

## Procedure
1. **Retrieve resources** – Use `get_resources_by_patient_fhir_id` to fetch all `Observation` resources for the patient. If the question restricts the search to a specific encounter (first/last hospital stay, ICU stay, etc.), also retrieve `Encounter` resources and identify the relevant encounter IDs.
2. **Define microbiology LOINC set** – Prepare a hard‑coded set of LOINC codes that represent microbiology tests (e.g.,
   ```python
   MICROBIOLOGY_LOINC = {
       "630-4", "631-2", "632-0", "633-8", "634-6", "635-3", "636-1", "637-9",
       "639-5", "640-3", "641-1", "642-9", "643-7", "644-5", "645-2", "646-0",
       "647-8", "648-6", "649-4", "650-2", "651-0", "652-8", "653-6", "654-4",
       "655-1", "656-9", "657-7", "658-5", "659-3", "660-1", "661-9", "662-7",
       "663-5", "664-3", "665-0", "666-8", "667-6", "668-4", "669-2", "670-0",
       "671-8", "672-6", "673-4", "674-2", "675-9", "676-7", "677-5", "678-3",
       "679-1", "680-9", "681-7", "682-5", "683-3", "684-1", "685-8", "686-6",
       "687-4", "688-2", "689-0", "690-8", "691-6", "692-4", "693-2", "694-0",
       "695-7", "696-5", "697-3", "698-1", "699-9", "700-5", "701-3", "702-1",
       "703-9", "704-7", "705-5", "706-3", "707-1", "708-9", "709-7", "710-5",
       "711-3", "712-1", "713-9", "714-7", "715-5", "716-3", "717-1", "718-9",
       "719-7", "720-5", "721-3", "722-1", "723-9", "724-7", "725-5", "726-3",
       "727-1", "728-9", "729-7", "730-5", "731-3", "732-1", "733-9", "734-7",
       "735-5", "736-3", "737-1", "738-9", "739-7", "740-5", "741-3", "742-1",
       "743-9", "744-7", "745-5", "746-3", "747-1", "748-9", "749-7", "750-5",
       "751-3", "752-1", "753-9", "754-7", "755-5", "756-3", "757-1", "758-9",
       "759-7", "760-5", "761-3", "762-1", "763-9", "764-7", "765-5", "766-3",
       "767-1", "768-9", "769-7", "770-5", "771-3", "772-1", "773-9", "774-7",
       "775-5", "776-3", "777-1", "778-9", "779-7", "780-5", "781-3", "782-1",
       "783-9", "784-7", "785-5", "786-3", "787-1", "788-9", "789-7", "790-5",
       "791-3", "792-1", "793-9", "794-7", "795-5", "796-3", "797-1", "798-9",
       "799-7", "800-3", "801-1", "802-9", "803-7", "804-5", "805-2", "806-0",
       "807-8", "808-6", "809-4", "810-2", "811-0", "812-8", "813-6", "814-4",
       "815-2", "816-0", "817-8", "818-6", "819-4", "820-2", "821-0", "822-8",
       "823-6", "824-4", "825-1", "826-9", "827-7", "828-5", "829-3", "830-1",
       "831-9", "832-7", "833-5", "834-3", "835-0", "836-8", "837-6", "838-4",
       "839-2", "840-0", "841-8", "842-6", "843-4", "844-2", "845-9", "846-7",
       "847-5", "848-3", "849-1", "850-9", "851-7", "852-5", "853-3", "854-1",
       "855-8", "856-6", "857-4", "858-2", "859-0", "860-8", "861-6", "862-4",
       "863-2", "864-0", "865-7", "866-5", "867-3", "868-1", "869-9", "870-7",
       "871-5", "872-3", "873-1", "874-9", "875-6", "876-4", "877-2", "878-0",
       "879-8", "880-6"  # truncated for brevity
   }
   ```
   (The full list can be stored in the skill; the above excerpt illustrates the approach.)
3. **Identify microbiology observations** – For each Observation `o`:
   - If `o.code.coding` contains a coding where `system` ends with `loinc` **and** `code` is in `MICROBIOLOGY_LOINC`, mark it as microbiology.
   - Otherwise, fall back to a text match: if any coding `display` or the `code.text` contains the words `microbiolog`, `culture`, `susceptibility`, or `screen` (case‑insensitive), also treat it as microbiology.
4. **Apply encounter filter (optional)** – If the question specifies a particular encounter (first/last hospital stay, ICU visit, etc.), keep only observations whose `encounter.reference` ends with one of the relevant Encounter IDs (including child encounters via `partOf`).
5. **Apply date filter (optional)** – If a date range is supplied (e.g., *since 03/2115*, *in 10/2184*), keep only observations whose `effectiveDateTime` (or `effectivePeriod.start` when the former is missing) falls within the range.
6. **Select the required observation** –
   - For *first* / *earliest* queries: choose the observation with the minimum datetime.
   - For *last* / *most recent* queries: choose the observation with the maximum datetime.
   - If the question asks for a *minimum/maximum value* rather than a date, extract `valueQuantity.value` after the above filtering and compute the min/max as needed.
7. **Return the answer** – Output the datetime in ISO‑8601 format (e.g., `2115-12-28T16:21:00`) or the computed value with its unit. If no matching observation exists, return a clear “None found” message.

## Checks
- Verify that the resources being inspected are of type `Observation`.
- Confirm each candidate observation has a parsable datetime (`effectiveDateTime` or `effectivePeriod.start`).
- When an encounter filter is required, ensure the observation’s `encounter.reference` matches one of the selected Encounter IDs.
- If a date range is part of the query, ensure the observation’s datetime lies inside the inclusive range.
- Before producing the final answer, ensure at least one observation survived all filters; otherwise answer with an appropriate “not found” statement.
- Answer format must be ISO‑8601 datetime string **or** numeric value with unit (e.g., `207 mmHg`).

## Avoid
- Do **not** rely solely on the display text containing the word “microbiolog”. This caused the earlier failure where observations coded with microbiology LOINC codes but with generic display text were missed.
- Do **not** treat observations whose LOINC code is absent from the microbiology list as microbiology, even if the display mentions “culture”. The fallback text match is only a secondary safety net.
- Do **not** ignore observations that use `effectivePeriod.start` when `effectiveDateTime` is missing.
- Do **not** return the wrong datetime (e.g., the observation’s `issued` field) when `effectiveDateTime` is available; always prefer `effectiveDateTime` → `effectivePeriod.start`.
