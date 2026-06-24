# PR #25 broad stats pipeline review - 2026-06-24

## Scope

Review PR #25 (`feat/bigdata-stats-pipeline`) against the current course-project
goal: collect larger railway-adjacent stats data with an automatic-update path,
normalize it deterministically into Silver, build useful Gold features, and keep
dashboard/task evidence honest.

No Linear context was used. Repository code and docs were the source of truth.

## Local research first

Read/checked:
- `README.md`, `TASK.md`, `docs/TASKS.md`, `docs/GAP_REGISTER.md`,
  `docs/PROGRESS_LOG.md`, `docs/index.html`
- `src/railway_lakehouse/bronze/sources/eurostat.py`
- `src/railway_lakehouse/bronze/sources/worldbank.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/gold/build.py`
- Existing unit/integration tests for Bronze live checks, Bronze source
  characterization, Silver stats mapping, Gold output, and pipeline s3 read-back.

## External docs

Used official API docs only for live-source/API shape assumptions:
- Eurostat SDMX 2.1 data query docs:
  `https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-detailed-guidelines/sdmx2-1/data-query`
- World Bank API basic call structures:
  `https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures`
- World Bank indicator API queries:
  `https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries`

## Review findings

- Production Bronze ingestion drifted from bounded live-check evidence. Eurostat
  and World Bank now share selector helpers between production ingestion and
  `bronze.live_check`.
- World Bank's broad indicator set could contaminate rail features through
  fallback English labels. Unknown World Bank IDs now become
  `worldbank_unmapped:<id>` and cannot map through generic substring rules.
- World Bank mapped `SP.URB.TOTL.IN.ZS` to `urban_population_pct`, but that
  canonical feature was absent from `CANONICAL_FEATURES`.
- Remote catalogue IDs were accepted directly into Bronze paths. Eurostat dataset
  IDs and World Bank indicator IDs now pass conservative path-safe regex checks.
- Eurostat broad collection needed practical bounds. Collection is capped by
  `EUROSTAT_MAX_DATASETS`, dataset responses are byte-capped by
  `EUROSTAT_MAX_DATASET_BYTES`, and dataset fetches use bounded streaming where
  the session supports it.
- `scripts/bronze_volume.py` assumed a present Bronze root and unbounded file
  reads. It now returns a zero report for missing roots and has artifact/file/
  decompressed/JSON limits plus skipped-artifact accounting.
- During conflict resolution with current `main`, `pipeline.py` and
  `tests/test_pipeline_live_stats_worldbank.py` had unresolved markers. They
  were resolved by preserving the current live World Bank s3 read-back behavior,
  zero-WB warning, and empty-Eurostat-frame filtering.
- CLI verification initially imported an older editable worktree. The package
  was reinstalled editable from the PR #25 worktree before final CLI/live
  evidence.
- Bounded live Gold exposed that World Bank aggregate geo codes such as `1A`,
  `1W`, and `EU` were classified as `region`. `gold.build._geo_level` now keeps
  NUTS-like codes as `region` and classifies non-country aggregate codes as
  `aggregate`.

## Evidence

- Focused review suites:
  `python -m pytest -q tests/test_eurostat_hardening.py tests/test_silver_eu_stats_features.py tests/test_bronze_volume.py tests/test_pipeline_live_stats_worldbank.py tests/test_silver_stats_ksh.py tests/test_env_versions.py`
  -> 42 passed.
  `python -m pytest -q tests/test_bronze_characterization.py tests/test_bronze_live_check.py tests/test_bronze_scheduler.py`
  -> 45 passed.
- Bounded live source run after editable reinstall:
  `python -m railway_lakehouse.bronze.live_check --sources eurostat,worldbank --out output/evidence/pr25-bigdata-live-check-v2 --max-artifacts 6 --timeout-seconds 120`
  -> Eurostat passed, World Bank passed, 14 artifacts, 31,711,348 bytes, 0 failures.
- Bronze volume count:
  `python scripts/bronze_volume.py output/evidence/pr25-bigdata-live-check-v2/bronze --out output/evidence/pr25-bigdata-live-check-v2/bronze_volume.json`
  -> 14 datasets/artifacts, 112,084 data rows, 152,054 observations, 0 skipped artifacts.
- Stats-only Bronze-to-Gold smoke from that live Bronze tree:
  `python -m railway_lakehouse.pipeline --bronze-root output/evidence/pr25-bigdata-live-check-v2/bronze --skip-news-extraction --news 0 --out output/evidence/pr25-bigdata-live-gold/railway_ml.parquet --crosswalk-path output/evidence/pr25-bigdata-live-gold/crosswalk_cache.json --counts-out output/evidence/pr25-bigdata-live-gold/counts.json`
  -> 3,550 rows x 11 columns, 157 geos, 1962-2025, AT/HU present, geo levels `country=3168`, `aggregate=382`.

Final full-suite, compile, whitespace, MinIO, and merge evidence are recorded in
`docs/PROGRESS_LOG.md` for the session.
