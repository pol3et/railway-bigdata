# Gap Register

Date: 2026-06-22

Source: `docs/MERGE_STRATEGY.md`, `docs/TEST_FIRST_INTEGRATION_PLAN.md`, and characterization-test results.

Status values:

- `open`: known gap, not fixed yet.
- `in_progress`: file changes exist but verification is not complete.
- `closed`: verification command passed and evidence is recorded.

## Gaps

| ID | Status | Owner | Sync Point | Evidence | Expected Behavior | Closure Criteria | Verification Command |
|---|---|---|---|---|---|---|---|
| GAP-001 | closed | Workstream A - DevEx / Repo Owner | S1 package/import contract | No dependency manifest existed under `bigdata/course_proj`; earlier imports failed on missing `pandas` and `s3fs`. | Classmates can install runtime and test dependencies from the project root. | Closed 2026-06-21: `pyproject.toml` exists and editable install passed. | `python -m pip install -e ".[test]"` |
| GAP-002 | closed | Workstream A - DevEx / Repo Owner | S1 package/import contract | Current code used competing import roots: `bronze`, `silver`, `gold`, and intended `railway_lakehouse`. | One stable import root exists after migration: `railway_lakehouse`. | Closed 2026-06-21: code moved to `src/railway_lakehouse` and package imports passed. | `python -c "import railway_lakehouse; import railway_lakehouse.pipeline"` |
| GAP-003 | closed | Workstream C - Bronze Owner | S1 package/import contract | Operational Bronze code was under `bronze/bronze`; new source adapters were under `railway_lakehouse/bronze/sources`. | One Bronze package owns raw landing and all source adapters. | Closed 2026-06-21: Bronze files and source adapters live under `src/railway_lakehouse/bronze`. | `python -m pytest -q -m unit` |
| GAP-004 | open | Workstream H - Live Ops / Real Data Owner | S3 local fixture E2E | `src/railway_lakehouse/pipeline.py` raises `NotImplementedError` for Bronze reads. | Pipeline can read deterministic Bronze fixtures before live collectors run. | `_read_bronze_eurostat` and `_read_bronze_news` have tested fixture-backed implementations. | `python -m pytest -q -m integration` |
| GAP-005 | open | Workstream C - Bronze Owner | S2 data contracts | `src/railway_lakehouse/bronze/run.py` schedules Eurostat, World Bank, GDELT, and RSS only. `parser/ksh-stadat` and `parser/uic-refresh` Bronze source work is done and live-validated, but KSH and UIC are still not scheduled. | KSH, Statistik Austria, UIC, and historical GDELT adapters are wired without changing raw landing semantics. | Scheduler imports and runs every configured source through the same `RawLander` contract. | `python -m pytest -q -m unit` |
| GAP-006 | open | Workstream D - Silver Stats Owner / Workstream E - Silver News Owner | S3 local fixture E2E | `silver/run.py` expects supplied frames/articles and notes storage reads must be wired. KSH XLSX -> `StatFact` parsing and Silver parser tests are not implemented yet. | Silver reads Bronze fixtures/storage and writes auditable Silver outputs. KSH STADAT Bronze XLSX files become validated `StatFact` rows without LLM numeric rewriting. | Stats and news fixture inputs produce persisted Silver rows with unmapped labels/extraction failures visible; KSH XLSX fixture tests pass. | `python -m pytest -q -m integration` |
| GAP-007 | open | Workstream F - Gold Owner | S3 local fixture E2E | `gold/run.py` says Silver loads must be wired. | Gold can load Silver outputs and write analysis-ready Parquet. | Fixture Silver inputs produce Gold Parquet and recorded row/column counts. | `python -m pytest -q -m integration` |
| GAP-008 | closed | Workstream B - QA / Gap Register Owner | S1 package/import contract | No `tests/` directory existed under `bigdata/course_proj`. | Deterministic tests cover current Bronze/Silver/Gold behavior and live checks are opt-in. | Closed 2026-06-21: unit tests exist, markers are registered, and expected failure references GAP-004. | `python -m pytest -q` |
| GAP-009 | open | Workstream G - Spark / Big Data Owner | S5 Spark evidence | No current Spark job entrypoint exists under `bigdata/course_proj`. | Spark job reads Gold/Silver data and writes evidence outputs. | Spark command records version, row counts, generated files, and warnings/failures. | `python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/live/railway_ml.parquet --out output/evidence/spark/` |
| GAP-010 | in_progress | Workstream H - Live Ops / Real Data Owner | S4 live Bronze/Silver/Gold run | Bounded RSS Bronze evidence exists at `output/evidence/live-bronze/manifest.json`; current KSH evidence exists at `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`; UIC public PDF evidence exists at `output/evidence/uic-live-check-2026-06-22/manifest.json`; parser PR verification added bounded Eurostat and World Bank live probes. Full Bronze/Silver/Gold live evidence is not complete. | Bounded fixture and live runs generate evidence under `output/evidence/`. | Commands, logs, row counts, and generated paths are recorded. | `python -m pytest -q -m integration` |
| GAP-011 | open | Workstream I - Report / Presentation Owner | S5 Spark evidence | Report/presentation deliverables have not started beyond organization notes. | Report and presentation use only verified outputs and documented gaps. | Drafts link every data claim to evidence artifacts. | Manual review of `output/report/` and `output/presentation/` |

## Test Failure Mapping

Update this section after each test run.

| Test / Command | Result | Gap ID | Notes |
|---|---|---|---|
| `python -m pip install --no-cache-dir -e ".[test]"` | passed | GAP-001 | First attempt failed due `[Errno 28] No space left on device`; pip cache was purged and final install passed with pinned S3 dependencies. |
| `python -m pytest -q -m unit` | passed: 15 passed, 1 deselected | GAP-008 | Bronze, Silver, and Gold characterization tests passed after migration. |
| `python -m pytest -q` | passed: 15 passed, 1 xfailed | GAP-004 | `test_pipeline_storage_read_stubs_are_not_wired` is a strict expected failure for the Bronze read stubs. |
| `python -c "import railway_lakehouse; import railway_lakehouse.pipeline"` | passed | GAP-002 | Package import root works after `src/railway_lakehouse` migration. |
| `python -m pip check` | passed | GAP-001 | No broken requirements found after dependency pinning. |
| Bounded live parser probe, manifest at `output/evidence/parser-live-check-2026-06-21/manifest.json` | partial | GAP-005 / GAP-010 | RSS and KSH landed raw artifacts; Eurostat/World Bank catalogues landed but need parser validation; GDELT hit 429; Statistics Austria seed was empty; UIC seed returned 404. |
| `python -m pytest -q tests\test_bronze_live_check.py` | passed: 3 passed | GAP-010 | Local Bronze lander, manifest writer, and bounded runner behavior are unit-tested without network or MinIO. |
| `python -m pytest -q` | passed: 18 passed, 1 xfailed | GAP-004 / GAP-010 | Full suite passed; existing `test_pipeline_storage_read_stubs_are_not_wired` remains the expected GAP-004 xfail. |
| `python -m railway_lakehouse.bronze.live_check --sources rss,ksh --out output/evidence/live-bronze --max-artifacts 5` | passed | GAP-010 | Manifest `output/evidence/live-bronze/manifest.json`; RSS passed with 5 artifacts, KSH passed with 3 artifacts, 264,670 total bytes, no source failures. |
| `python -m pytest -q tests\test_bronze_live_check.py` | passed: 8 passed | GAP-010 | PR #1 follow-up added rerun-safe output, preflight validation, collector response, and failure-exit coverage. |
| `python -m pytest -q tests\test_bronze_characterization.py` | passed: 11 passed | GAP-005 / GAP-010 | Eurostat quoted-code parsing and World Bank indicator validation are covered after PR #2 and PR #3. |
| Eurostat direct probe for `enpe_rail_go` | passed: HTTP 200, 552 bytes | GAP-010 | Bounded probe used `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/enpe_rail_go/?format=TSV&compressed=true`. |
| World Bank bounded direct probe | passed | GAP-010 | Accepted `IS.RRS.TOTL.KM`, `IS.RRS.GOOD.MT.K6`, and `IS.RRS.PASG.KM`; rejected `BM.GSR.TRAN.CD` as an API error envelope. |
| `python -m pytest -q` | passed: 29 passed, 1 xfailed | GAP-004 / GAP-010 | Final suite after merging PR #1, PR #2, and PR #3; the only expected failure is `test_pipeline_storage_read_stubs_are_not_wired` for GAP-004. |
| `python -m compileall .` | passed | GAP-001 / GAP-002 | Final syntax/import-bytecode sweep after all PR merges passed. |
| `python -m pytest -q tests\test_bronze_characterization.py` | passed: 15 passed | GAP-005 / GAP-010 | KSH curated seed regression tests and XLSX response validation now pass with existing Eurostat/World Bank Bronze characterization. |
| `python -m pytest -q tests\test_bronze_live_check.py` | passed: 8 passed | GAP-010 | Local KSH live-check collector handles `KshTable` seeds and rejects empty, malformed, or non-XLSX HTTP-200 bodies. |
| `python -m pytest -q tests\test_bronze_live_check_integration.py` | passed: 1 passed | GAP-010 | Integration fixture exercises `run_live_check`, the KSH collector, manifest writing, raw Bronze file writing, and metadata writing without network. |
| `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/ksh-live-check-2026-06-22-current --max-artifacts 6 --timeout-seconds 30` | passed | GAP-010 | Current implementation landed 6 KSH artifacts, 92,509 bytes, 0 failures; committed manifest is `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`. |
| `python -m pytest -q tests\test_bronze_live_check.py` | passed: 9 passed | GAP-010 | Local live-check tests now include UIC PDF response validation and manifest collection behavior. |
| UIC bounded direct probe | passed | GAP-010 | Current public UIC resource endpoints `help_resource/?id=12` and `help_resource/?id=14` returned HTTP 200 PDF bytes; stale `https://uic.org/IMG/xls/uic_railway_statistics_synopsis.xls` returned HTTP 404. |
| `python -m pytest -q tests\test_bronze_characterization.py::test_uic_public_resources_use_current_free_pdf_endpoints tests\test_bronze_characterization.py::test_uic_pdf_validation_rejects_html_empty_and_non_200 tests\test_bronze_characterization.py::test_uic_ingest_lands_valid_public_pdfs_and_skips_html_or_404 tests\test_bronze_live_check.py::test_collect_uic_lands_successes_and_records_failures` | passed: 4 passed | GAP-005 / GAP-010 | UIC source tests cover current public resource ids, PDF validation, ingest metadata, and live-check collection. |
| `python -m railway_lakehouse.bronze.live_check --sources uic --out output/evidence/uic-live-check-2026-06-22 --max-artifacts 2 --timeout-seconds 30` | passed | GAP-010 | Current implementation landed 2 UIC public PDF artifacts, 2,109,240 bytes, 0 failures; manifest is `output/evidence/uic-live-check-2026-06-22/manifest.json`. |
| `python -m pytest -q` | passed: 43 passed, 1 xfailed | GAP-004 / GAP-010 | Full suite passed after UIC refresh and concurrent GDELT history safety work; the only expected failure remains `test_pipeline_storage_read_stubs_are_not_wired` for GAP-004. |
| `python -m pytest -q tests\test_bronze_characterization.py -k "gdelt or past_recordings"` | passed: 6 passed, 17 deselected | GAP-010 | GDELT recent/history mocked 429 retry handling, `Retry-After`, 200-record DOC bound, and history `--dry-run` / `--max-pages` controls pass. |
| `python -m pytest -q tests\test_bronze_characterization.py` | passed: 23 passed | GAP-005 / GAP-010 | Bronze characterization now includes GDELT rate-limit tests plus existing Eurostat, World Bank, KSH, and UIC coverage. |
| Bounded GDELT recent live retry probe, manifest at `output/evidence/gdelt-live-check-2026-06-22/manifest.json` | partial | GAP-010 | One-day, `max_records=25`, `max_retries=1` probe landed HU after HTTP statuses `[429, 200]`; AT failed with a remote disconnect. |
| `python -m pytest -q` | passed: 43 passed, 1 xfailed | GAP-004 / GAP-010 | Full suite passes; the only expected failure remains `test_pipeline_storage_read_stubs_are_not_wired` for GAP-004. |
| `python -m compileall src tests` | passed | GAP-001 / GAP-002 | Syntax/import-bytecode sweep over current source and tests passed. |
| `git diff --check` | passed | repo hygiene | No whitespace errors in the current working-tree diff. |
