# Gap Register

Date: 2026-06-21

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
| GAP-005 | open | Workstream C - Bronze Owner | S2 data contracts | `src/railway_lakehouse/bronze/run.py` schedules Eurostat, World Bank, GDELT, and RSS only. | KSH, Statistik Austria, UIC, and historical GDELT adapters are wired without changing raw landing semantics. | Scheduler imports and runs every configured source through the same `RawLander` contract. | `python -m pytest -q -m unit` |
| GAP-006 | open | Workstream D - Silver Stats Owner / Workstream E - Silver News Owner | S3 local fixture E2E | `silver/run.py` expects supplied frames/articles and notes storage reads must be wired. | Silver reads Bronze fixtures/storage and writes auditable Silver outputs. | Stats and news fixture inputs produce persisted Silver rows with unmapped labels/extraction failures visible. | `python -m pytest -q -m integration` |
| GAP-007 | open | Workstream F - Gold Owner | S3 local fixture E2E | `gold/run.py` says Silver loads must be wired. | Gold can load Silver outputs and write analysis-ready Parquet. | Fixture Silver inputs produce Gold Parquet and recorded row/column counts. | `python -m pytest -q -m integration` |
| GAP-008 | closed | Workstream B - QA / Gap Register Owner | S1 package/import contract | No `tests/` directory existed under `bigdata/course_proj`. | Deterministic tests cover current Bronze/Silver/Gold behavior and live checks are opt-in. | Closed 2026-06-21: unit tests exist, markers are registered, and expected failure references GAP-004. | `python -m pytest -q` |
| GAP-009 | open | Workstream G - Spark / Big Data Owner | S5 Spark evidence | No current Spark job entrypoint exists under `bigdata/course_proj`. | Spark job reads Gold/Silver data and writes evidence outputs. | Spark command records version, row counts, generated files, and warnings/failures. | `python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/live/railway_ml.parquet --out output/evidence/spark/` |
| GAP-010 | open | Workstream H - Live Ops / Real Data Owner | S4 live Bronze/Silver/Gold run | No generated dataset evidence existed before the documentation scaffold. | Bounded fixture and live runs generate evidence under `output/evidence/`. | Commands, logs, row counts, and generated paths are recorded. | `python -m pytest -q -m integration` |
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
