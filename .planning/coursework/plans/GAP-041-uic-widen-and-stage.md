# GAP-041 UIC Widen And Stage Implementation Plan

Status: approved
Date: 2026-06-25

Goal: widen UIC PDF geo recognition beyond AT/HU, preserve all extracted UIC table rows and text chunks in a Silver staging contract, and keep the existing stats path deterministic.

Scope in:
- `src/railway_lakehouse/silver/stats/load.py`: ISO code mapping, golden/staging split, text chunk staging, optional staging collection from Bronze files.
- `src/railway_lakehouse/silver/persist.py`: `uic_staging` Parquet schema, writer, reader, and canonical path constants.
- `tests/test_silver_stats_uic_pdf.py`: four new deterministic tests using in-memory tables/PDF bytes/tmp_path only.
- `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/index.html`, progress logs, and the research log.

Scope out:
- Bronze PDF bytes, landing paths, live collector behavior, Gold aggregation from staging, Spark filters, and news-staging schemas.
- New dependency on `pycountry`; the current constrained environment does not include it.

Approved refinements:
- Add 4 tests to the current 6-test UIC file; do not claim "16 tests" unless that count exists after implementation.
- Keep `load_uic_frame(raw, dataset_id)` returning the existing golden stats frame. Add separate staging helpers instead of changing the return type.
- Persist staging only through explicit helper calls or an optional `uic_staging_root` argument; avoid unexpected writes during ordinary fixture tests.

Tasks:

1. Test-first UIC staging API.
   - Add `test_uic_rows_from_tables_staging_captures_unmapped_geos()` against a compact table containing AT, HU, CZ, and FR.
   - Add `test_uic_rows_from_tables_staging_preserves_unparseable_values()` for malformed year/value cells and raw audit columns.
   - Expected RED: `_uic_rows_from_tables_staging` does not exist.

2. Implement UIC table staging and golden split.
   - Replace AT/HU-only constants with a deterministic code/name mapping covering EU plus known UIC neighboring/publication countries.
   - Add `_uic_rows_from_tables_golden()` with the old stats output shape and keep `_uic_rows_from_tables()` as a compatibility alias.
   - Add `_uic_rows_from_tables_staging()` with `dataset_id`, `table_id`, `table_idx`, `row_type`, `row_idx`, `parse_status`, `geo`, `year`, `source_dataset`, `source_system`, `raw_geo_cell`, `raw_year_cell`, `raw_value_cells`, `text_chunk`, and `created_at`.

3. Test-first traffic-trends text staging.
   - Add `test_load_uic_frame_extracts_traffic_trends_text_chunks()` using a text-only minimal PDF and monkeypatched table extraction if needed.
   - Expected RED: text chunk staging helper does not exist.

4. Implement text chunk staging.
   - Split extracted text on non-empty lines into deterministic `text_chunk` rows with `row_type="text_chunk"`, `table_idx=-1`, and `parse_status="text_only"`.
   - Keep `load_uic_frame()` returning an empty golden stats frame for text-only PDFs.

5. Test-first staging persistence.
   - Add `test_uic_staging_roundtrip_persists_and_reloads()` using `tmp_path`, mixed table/text staging rows, and Parquet round-trip.
   - Expected RED: `persist_uic_staging` / `load_uic_staging` do not exist.

6. Implement persistence contract.
   - Add `UIC_STAGING_COLUMNS`, Arrow schema, `persist_uic_staging()`, `load_uic_staging()`, and `collect_uic_staging_from_bronze()`.
   - Add optional `uic_staging_root` / `ingest_date` parameters to `build_silver_stats()` so callers can persist staging without altering default behavior.

7. Docs and dashboard sync.
   - Document Silver UIC staging in `docs/DATA_CONTRACTS.md`.
   - Add the GAP-041 task row and clarify current UIC reader status in `docs/TASKS.md`.
   - Add a dashboard open-gap item for GAP-041 in `docs/index.html`.
   - Append handoff entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

8. Verification and PR.
   - Run targeted RED/GREEN tests during implementation.
   - Final commands: `python -m pytest -q tests/test_silver_stats_uic_pdf.py`, `python -m pytest -q`, `python -m compileall -q src tests`, `python -m html.parser docs/index.html`, and bounded UIC live check if reachable.
   - Commit, push `impl/gap-041`, open PR against `main`, and verify mergeability.

Self-review:
- Spec coverage: all GAP-041 requested behaviors are covered without moving Bronze or Gold behavior.
- Placeholder scan: no TBD/TODO placeholders remain in this plan.
- Type consistency: staging helper and persistence function names are defined before use and match the planned tests.
- Scope check: no unrelated parser hardening, scheduler wiring, Spark, Gold, or news-staging work is included.
