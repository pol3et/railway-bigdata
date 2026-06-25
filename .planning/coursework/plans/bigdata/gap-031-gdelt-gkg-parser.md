# GAP-031 GDELT GKG Parser Implementation Plan

Status: approved
Date: 2026-06-25

## Goal

Build the missing deterministic Silver parser for raw GDELT GKG `.csv.zip` Bronze files and wire explicit GKG records into the existing GAP-039/GAP-050 `NewsFeature` passthrough path without adding a persisted GKG table or new live collection.

## Scope Refinement

The Claude draft is stale in these places:

- `NewsFeature` already has the GKG passthrough columns from GAP-039.
- `gdelt_passthrough_cached()` and `run_extraction_pipeline()` already avoid Ollama when a GDELT article dict carries `gkg_*` fields.
- GKG 2.1 is not a 7-15 column CSV. It is a 27-column tab-delimited format; GKG 1.0 daily files have a different tab-delimited layout.
- GKG themes are text theme tokens, not numeric CAMEO event codes. Numeric examples like `036`, `180`, and `330` are not accepted as authoritative mappings.
- Full automatic GKG-to-DOC URL cross-linking remains out of scope. GAP-031 supports explicit caller-provided `GKGRecord` data and simple URL/article-id lookup only.

## Files

- Modify `src/railway_lakehouse/silver/schema.py`: add transient `GKGRecord`.
- Create `src/railway_lakehouse/silver/news/gkg_parser.py`: parse GKG CSV text and ZIP bytes.
- Modify `src/railway_lakehouse/silver/news/extract.py`: accept `GKGRecord`, map themes/operators, and let `article_records_to_news_features()` accept explicit GKG records.
- Create `tests/test_silver_gkg_parser.py`: unit and integration-marked fixture coverage without network.
- Modify `docs/SILVER_DESIGN.md`, `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, and `docs/index.html`: sync feature state.
- Update `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md` before stopping.

## Work Plan

1. Add tests first:
   - Parser tests for valid 2.1 rows, valid 1.0 rows, UTF-8 text, malformed row skipping, ZIP extraction, stable fallback IDs, and URL matching.
   - Passthrough tests for tone->sentiment, HU/AT country extraction including GDELT FIPS `AU`, theme->event_type, operator extraction, old bare-field `gdelt_passthrough()` compatibility, and `GKGRecord` input.
   - Integration-marked test for `article_records_to_news_features(records, gkg_records=[...])` proving a matching GDELT article uses passthrough and does not call the LLM.

2. Run the new tests before implementation and confirm RED failures are due to missing `GKGRecord`/`gkg_parser`/new signatures.

3. Add `GKGRecord`:
   - Fields: `gkg_id`, `gkg_date`, `document_identifier`, `source_common_name`, `gkg_themes`, `gkg_tone`, `gkg_persons`, `gkg_organizations`, `gkg_locations`, `gkg_emotions`.
   - `to_row()` returns `asdict(self)`.

4. Implement `gkg_parser.py`:
   - Parse tab-delimited rows with Python `csv.reader(delimiter="\t")`.
   - Detect 2.x rows when column count is at least 16 and column 1 looks like a 14-digit date.
   - Detect 1.0 rows for known 21-column daily rows and map date/tone/themes/locations/persons/orgs/source URLs.
   - Extract tone as the first comma-delimited number.
   - Normalize enhanced `theme,offset` / `name,offset` fields to plain semicolon-delimited values.
   - `parse_gkg_csv_zip(zip_bytes, date_str)` opens the first `.csv` member, decodes UTF-8, and returns parsed records; bad ZIPs log and return `[]`.
   - `gkg_record_id(row)` returns `GKGRECORDID`/`gkg_id` when present, otherwise SHA-256 over stable key fields.
   - `match_gkg_to_article(record, article_url)` normalizes URL strings and checks exact URL membership in `document_identifier`.

5. Extend passthrough:
   - Keep old `gdelt_passthrough(gkg_tone=..., gkg_themes=..., gkg_locations=...)` calls working by making those args optional.
   - Add `gkg_record: GKGRecord | None`.
   - Convert `GKGRecord` to the existing dict shape and delegate to `gdelt_passthrough_cached()`.
   - Add deterministic helpers for country, themes, and operators. Unknown themes map to `other`.

6. Wire explicit GKG lookup:
   - Add `gkg_records: Optional[list[GKGRecord]] = None` to `article_records_to_news_features()`.
   - Match GDELT records by `article_id`, `url`, or `match_gkg_to_article()`.
   - Merge matching GKG fields into the article dict and pass through `extract_batch()`, preserving the existing manifest/count behavior for lower-level callers.

7. Update docs and dashboard:
   - Document GKG as transient Silver input in `DATA_CONTRACTS.md`.
   - Document hybrid GKG extraction in `SILVER_DESIGN.md`.
   - Mark `silver/gdelt-gkg-parser` done in `docs/TASKS.md`.
   - Update `docs/index.html` source row, parser card, open-gap list, and Wave 6 chip.

8. Verification:
   - `python -m pytest -q tests/test_silver_gkg_parser.py`
   - `python -m pytest -q -m integration`
   - `python -m pytest -q`
   - `python -m compileall -q src tests`
   - `git diff --check`

9. Ship:
   - Commit on `impl/gap-031`.
   - Push to origin.
   - Open PR against `main`.
   - Check PR mergeability with `gh pr view`.

## Self-Review

- Spec coverage: parser, transient schema, passthrough signature, deterministic mappings, explicit pipeline routing, docs, dashboard sync, and verification are covered.
- Scope guard: no Bronze mutation, no new persisted GKG table, no live GDELT download, no Spark job parsing, no automatic URL cross-linking claim.
- Type consistency: `GKGRecord` is the only new domain object; parser and extraction functions use that exact type.
- Test discipline: tests are written before production code and use inline/tmp fixtures only.

Approved for implementation by the orchestrator on 2026-06-25.
