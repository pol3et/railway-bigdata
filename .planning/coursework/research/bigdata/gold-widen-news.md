# GAP-040 Gold Widen News Aggregation

Date: 2026-06-25

## Research Routing

- Skill: `research-orchestrator`
- MCP providers used:
  - Context7 for pandas aggregation APIs.
  - Ref attempted for pandas, ISO 639, and GDELT docs; provider returned "Not enough credits", so it could not be used.
  - Firecrawl agent/extract for ISO 639 and GDELT source discovery/extraction.
- Supplemental web search was used only after the routed Ref provider failed, to confirm public source URLs.

## External Sources

- pandas groupby, named aggregation, pivot_table fill_value, explode: https://pandas.pydata.org/docs/user_guide/groupby.html and https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.pivot_table.html via Context7.
- ISO 639 language codes and Set 1 two-letter identifiers: https://www.iso.org/iso-639-language-code.
- Library of Congress ISO 639 overview/code lists: https://www.loc.gov/standards/iso639-2/langhome.html and https://www.loc.gov/standards/iso639-2/php/code_list.php.
- GDELT data overview and GKG documentation hub: https://www.gdeltproject.org/data.html.
- GDELT Global Knowledge Graph codebook v2.1: https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf.

## Local Evidence

- `src/railway_lakehouse/gold/build.py` currently aggregates news only at `(country, year)` and drops language, confidence, rail_lines, and GKG fields.
- `src/railway_lakehouse/silver/schema.py` is newer than the drafted task: `NewsFeature` has 43 fields, not 15, and includes persisted `gkg_*` columns.
- `src/railway_lakehouse/silver/persist.py` preserves the full 43-field NewsFeature schema in Parquet, including GKG passthrough fields.
- `src/railway_lakehouse/silver/news/extract.py` has `gdelt_passthrough_cached(...)` and the extraction pipeline routes source=`gdelt` rows with `gkg_*` fields through it.
- Baseline evidence before implementation:
  - `python -m pytest -q tests/test_gold_characterization.py` -> `5 passed`.
  - `python -m pytest -q -m integration tests/test_gold_load_from_silver.py` -> `1 passed`.
  - Aggregate baseline printed `False` for raw `language`, `confidence`, and `rail_lines` column presence in Gold output.

## Spec Refinements

The subagent draft is directionally correct but stale in three places:

1. The Silver NewsFeature contract is now 43 fields, not 15.
2. GKG fields are already schema/persistence-ready. GAP-040 should not parse new Bronze GKG files or enrich Silver, but Gold can deterministically aggregate already-present `gkg_*` fields.
3. The canonical Czech language code must be `cs`, not `cz`, because ISO 639-1 uses `cs` for Czech. `cz` is not an ISO 639-1 language code.

No scope widening: this implementation stays inside deterministic pandas Gold aggregation, docs, tests, and dashboard sync. It does not introduce LLM calls, network collectors, Docker, MinIO dependencies, new Silver parsing, or report claims.

## Approved Implementation Plan

Self-approved for implementation after local-code and external-doc sanity check.

1. Add failing tests first:
   - Unit tests in `tests/test_gold_characterization.py` for language, confidence, rail_lines, year-month granularity, deterministic schemas, optional-row defaults, and existing event/operator behavior.
   - Integration coverage in `tests/test_gold_load_from_silver.py` proving persisted Silver NewsFeature rows reload into widened Gold columns.
2. Implement deterministic Gold helpers in `src/railway_lakehouse/gold/build.py`:
   - Validate `granularity in {"year", "year-month"}`.
   - Parse dates with pandas mixed-format parsing to cover ISO, compact GDELT, and RFC-822/RSS strings.
   - Reindex event/operator pivots to canonical vocabularies.
   - Define deterministic `CANONICAL_LANGUAGES` using ISO 639-1 codes: `hu`, `de`, `en`, `fr`, `es`, `it`, `pl`, `ro`, `sk`, `cs`.
   - Emit `news_language_<code>`, `news_language_primary`, and `news_language_entropy`.
   - Emit confidence mean/std/min/max and low/medium/high bins.
   - Emit rail-line aggregate columns, not free-text pivots: `news_n_rail_lines_unique` and `news_rail_lines_list`.
   - Emit bounded GKG rollups from already-present Silver fields only: `news_gkg_tone_*`, unique counts, and sorted token lists. Defer canonical theme pivots to GAP-031/v2 because no theme vocabulary is owned by Gold.
   - Preserve default `(geo, year)` output and add optional `(geo, year, month)` output.
3. Keep `build_gold(...)` default-compatible and pass the new granularity parameter to `aggregate_news(...)`.
4. Update count/text/stat zero-fill logic so merged stats-only rows get zeroes for count-like news columns, empty strings for list/primary string columns, and NaN for sentiment/confidence/tone ratio/stat columns.
5. Update docs:
   - `docs/DATA_CONTRACTS.md` Gold section.
   - `docs/TASKS.md`, `docs/GAP_REGISTER.md`, and `docs/index.html`.
   - Append handoff entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.
6. Verify:
   - Red tests fail before source implementation.
   - `python -m pytest -q -m unit tests/test_gold_characterization.py`
   - `python -m pytest -q -m integration tests/test_gold_load_from_silver.py`
   - `python -m pytest -q -m unit`
   - `python -m pytest -q`
   - `python -m compileall -q src tests`
   - `git diff --check`
7. Commit, push `impl/gap-040`, open a PR to `main`, and confirm GitHub reports it mergeable.

## Verification Results

- Red phase:
  - `python -m pytest -q -m unit tests/test_gold_characterization.py` -> 4 failed, 5 passed before implementation. Failures covered missing `granularity`, non-deterministic event/operator columns, and optional dict-field `KeyError`.
  - `python -m pytest -q -m integration tests/test_gold_load_from_silver.py` -> 1 failed, 1 passed before implementation. Failure covered missing widened news columns after persisted Silver reload.
- Green focused checks:
  - `python -m pytest -q -m unit tests/test_gold_characterization.py` -> 9 passed.
  - `python -m pytest -q -m integration tests/test_gold_load_from_silver.py` -> 2 passed.
- Green suite checks:
  - `python -m pytest -q -m unit` -> 175 passed, 31 deselected.
  - `python -m pytest -q -m integration` -> 24 passed, 182 deselected.
  - `python -m pytest -q` -> 200 passed, 6 skipped.
  - `python -m compileall -q src tests` -> passed.
  - `git diff --check` -> passed with line-ending warnings only.
