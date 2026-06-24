# GAP-007 Gold Load From Silver Research

Date: 2026-06-24

## Local Research

- `gold.run` currently exposes `build_from_silver(stats_long, news_rows, out_path, year_min=None, year_max=None)` and warns when the built Gold table is empty, but `main()` only parses `--out`, `--year-min`, and `--year-max` before logging placeholder text. Evidence: `src/railway_lakehouse/gold/run.py:23-43`.
- Silver persisted-output readers already exist. `persist.load_stats(root, ingest_date=None)` and `persist.load_news(root, ingest_date=None)` read an explicit partition or the latest `ingest_date=*` partition, returning schema-shaped empty DataFrames if the Parquet file is absent. Evidence: `src/railway_lakehouse/silver/persist.py:170-185`.
- The local Silver path contract is frozen as `silver/stats/stat_fact/ingest_date=YYYY-MM-DD/stat_fact.parquet` and `silver/news/news_feature/ingest_date=YYYY-MM-DD/news_feature.parquet`; empty news writes still preserve schema. Evidence: `docs/DATA_CONTRACTS.md:70-98`.
- The existing counts JSON shape includes `path`, `rows`, `columns`, `column_names`, `geos_count`, `contains_AT`, `contains_HU`, `year_min`, `year_max`, `at_rows`, and `hu_rows` when source columns are present. Evidence: `src/railway_lakehouse/pipeline.py:193-222`.
- The current library-only integration pattern persists fixture-derived Silver, reloads it, and feeds reloaded stats/news into `build_from_silver`, asserting `rail_passenger_km` reaches Gold. Evidence: `tests/test_silver_persist_integration.py:26-50`.
- Dashboard sync is required for this gap because it advances pipeline state. Evidence: `AGENTS.md` Hard Rules and `docs/index.html` GAP-007 entries.

## External Research

No external research was needed. GAP-007 is repository-local CLI wiring around existing pandas/pyarrow code and documented project contracts.

## Implementation Decision

Move `write_gold_counts` into `gold/build.py` so Gold can call it directly without importing `pipeline.py`. Then have `pipeline.py` import the same helper to preserve the GAP-010 counts shape and avoid a `gold.run` <-> `pipeline` import cycle.

## Verification

- RED check: `python -m pytest -q tests/test_gold_load_from_silver.py` failed before implementation with `TypeError: main() takes 0 positional arguments but 1 was given`.
- Targeted GREEN check: `python -m pytest -q tests/test_gold_load_from_silver.py tests/test_pipeline_gaps.py::test_pipeline_fixture_e2e_reads_bronze_and_writes_gold` -> 2 passed.
- Marker suites: `python -m pytest -q -m unit` -> 89 passed, 14 deselected; `python -m pytest -q -m integration` -> 14 passed, 89 deselected.
- Full suite: `python -m pytest -q` -> 103 passed.
- Syntax/import sweep: `python -m compileall -q src tests` -> passed.
- CLI smoke: seeded Silver under `output/runtime/gap-007-cli-smoke/silver`, then ran `python -m railway_lakehouse.gold.run --silver-root output/runtime/gap-007-cli-smoke/silver --out output/runtime/gap-007-cli-smoke/gold/railway_ml.parquet --counts-out output/runtime/gap-007-cli-smoke/gold/counts.json --ingest-date 2026-06-23` -> Gold 4 rows x 4 columns; counts include `contains_AT=true`, `contains_HU=true`, `year_min=2020`, `year_max=2021`, and `rail_passenger_km`.
- Verification environment note: pytest config now sets `pythonpath = ["src"]` so exact `python -m pytest ...` commands collect this checkout's source even if a different worktree is globally installed editable.
