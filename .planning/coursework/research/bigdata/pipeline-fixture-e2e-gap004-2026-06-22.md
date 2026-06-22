# Pipeline Fixture E2E GAP-004 Research - 2026-06-22

## Scope

Close `pipeline/fixture-e2e-gap004` using repo code and docs only. No Linear,
live collectors, MinIO, Ollama service, Spark, or long backfills were used.

## Local Research

- `AGENTS.md` requires `research-orchestrator`, local-file research first, a
  task research note, and progress-log updates.
- `docs/GAP_REGISTER.md` defined GAP-004 closure as tested implementations of
  `_read_bronze_eurostat` and `_read_bronze_news`.
- `docs/VERIFICATION.md` required a deterministic integration fixture E2E that
  reads Bronze, builds Silver, writes Gold, and records evidence under
  `output/evidence/fixture-e2e/`.
- `docs/NEXT_SESSION_HANDOFF.md` specified tiny local fixtures and mocked
  Ollama output, not live services.
- `src/railway_lakehouse/pipeline.py` had explicit `NotImplementedError`
  stubs before this session.
- `src/railway_lakehouse/bronze/lander.py` defines the Bronze path contract:
  `bronze/<domain>/<source>/<dataset_id>/ingest_date=YYYY-MM-DD/<file>`.
- `src/railway_lakehouse/silver/stats/merge.py`,
  `src/railway_lakehouse/silver/news/extract.py`, and
  `src/railway_lakehouse/gold/build.py` already had pure transformation logic
  suitable for fixture-driven integration.

## Implementation Notes

- Added a local `--bronze-root` mode to `railway_lakehouse.pipeline`.
- In local mode, the pipeline reads existing Bronze fixture files and skips
  live Bronze ingestion.
- `_read_bronze_eurostat` reads TSV/TSV.GZ files from
  `stats/eurostat/<dataset_id>/ingest_date=*`.
- `_read_bronze_news` reads JSON article pages from `news/*/<dataset_id>/`.
  The fixture covers the GDELT-style `{"articles": [...]}` shape.
- Added `--skip-news-extraction` so service-free CLI evidence can avoid Ollama
  while tests still cover mocked news extraction.
- Added `--crosswalk-path` in PR review follow-up so the committed fixture
  crosswalk cache is reproducible from the documented command.
- Added `tests/fixtures/bronze/**` as the stable repo-local fixture input.
- Independent read-only review found one low-risk `limit=0` news-reader edge
  case, fixed with `test_pipeline_news_reader_honors_zero_limit`.

## Evidence

- RED test run before implementation:
  `python -m pytest -q tests\test_pipeline_gaps.py` failed with
  `NotImplementedError` from `_read_bronze_eurostat` and `TypeError` because
  `main()` did not accept an argv list.
- Targeted test after implementation and review fix:
  `python -m pytest -q tests\test_pipeline_gaps.py` passed: 3 passed.
- GAP closure command:
  `python -m pytest -q -m integration` passed: 4 passed, 52 deselected.
- Fixture evidence command:
  `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction`
  passed and wrote `output/evidence/fixture-e2e/railway_ml.parquet` plus
  `output/evidence/fixture-e2e/crosswalk_cache.json`.
- Parquet readback:
  `(4, 3)` with rows for `AT/HU` in `2020/2021` and `rail_passengers`.
- Full verification:
  `python -m pytest -q` passed: 56 passed.
- Compile check:
  `python -m compileall src tests` passed.
- Whitespace check:
  `git diff --check` exited 0.

## Boundaries

- GAP-004 is closed for deterministic fixture-backed Bronze reads.
- This does not prove live MinIO, live collectors, a running Ollama service,
  Spark, Silver persistence, Gold storage loading, report, or presentation
  outputs.
