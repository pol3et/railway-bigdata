# GAP-007 Gold Load From Silver Implementation Plan

**Goal:** Wire `railway_lakehouse.gold.run` to load persisted Silver Parquet, write Gold Parquet under `output/`, and record reproducible counts.

**Scope:** GAP-007 only. No MinIO, Ollama, Spark, parser, unit-normalization, or news-schema changes.

**Contract Evidence Reviewed:**
- `src/railway_lakehouse/gold/run.py:23-43` has the importable `build_from_silver` entry point and stub CLI.
- `src/railway_lakehouse/silver/persist.py:170-185` loads latest or explicit `ingest_date` partitions and returns schema-shaped empty frames when missing.
- `src/railway_lakehouse/pipeline.py:193-222` defines the current counts JSON shape.
- `tests/test_silver_persist_integration.py:26-50` proves persisted Silver can feed Gold as a library call.
- `docs/DATA_CONTRACTS.md:70-98` freezes the local Silver Parquet path contract.

## Tasks

- [x] Write failing integration coverage in `tests/test_gold_load_from_silver.py`:
  - Use `pytest.mark.integration`.
  - Build deterministic Silver stats from `tests/fixtures/bronze` with `use_llm=False`.
  - Monkeypatch `stats_merge.CROSSWALK_PATH` into `tmp_path`.
  - Persist stats plus empty news to `tmp_path / "silver"` with `ingest_date="2026-06-23"`.
  - Invoke `gold.run.main([...])` with explicit `--silver-root`, `--out`, `--counts-out`, and `--ingest-date`.
  - Assert returned path, Gold parquet, counts rows/columns, `contains_AT`, `contains_HU`, and `rail_passenger_km`.
- [x] Verify RED with a targeted pytest command.
- [x] Move `write_gold_counts` to `src/railway_lakehouse/gold/build.py` using the same JSON keys and pandas behavior.
- [x] Update `src/railway_lakehouse/pipeline.py` to import `write_gold_counts` from `gold.build` and remove the duplicate local helper/imports that become unused.
- [x] Rewrite `src/railway_lakehouse/gold/run.py`:
  - Update docstring to the real persisted-Silver command.
  - Parse `main(argv=None)`.
  - Add `--silver-root` required, `--out` default `output/evidence/gold/railway_ml.parquet`, `--ingest-date`, `--year-min`, `--year-max`, and `--counts-out` default `output/evidence/gold/counts.json`.
  - Load stats/news via `silver.persist.load_stats/load_news`.
  - Convert news DataFrame to `to_dict("records")`.
  - Call `build_from_silver`, then `write_gold_counts` when a counts path is supplied.
  - Return the output path string and keep the existing empty-Gold warning.
- [x] Verify GREEN with targeted integration tests and the pipeline counts test.
- [x] Add `pythonpath = ["src"]` to pytest config after verification exposed a global editable-install pointer to another worktree; this keeps exact pytest commands bound to this checkout.
- [x] Update docs and dashboard:
  - `docs/GAP_REGISTER.md` GAP-007 row plus Test Failure Mapping.
  - `docs/CODEMAP.md` Gold status.
  - `docs/STATE_AND_ROADMAP.md` status and roadmap rows.
  - `docs/TASKS.md` active path and wave status.
  - `docs/index.html` matching dashboard items.
  - `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md` handoff entries.
- [x] Run required verification:
  - `python -m pytest -q -m integration`
  - `python -m pytest -q`
  - `python -m compileall -q src tests`
  - live CLI smoke against a tmp Silver tree, bounded and local only.
- [x] Commit, push `impl/gap-007`, open PR against `main`, and confirm mergeability.

## Self-Review

- Spec coverage: every requested CLI arg, persisted Silver load, counts artifact, test assertions, docs, and verification command is mapped to a task above.
- Scope check: no code path touches Bronze mutability, LLM extraction, MinIO, Spark, parser gaps, or unit-normalization/news-schema follow-up gaps.
- Placeholder scan: no TBD placeholders; all implementation targets and commands are explicit.

Status: approved for implementation on 2026-06-24.
