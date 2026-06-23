# Railway Big Data Course Project

This directory is being shaped into a standalone course-project repo for railway data collection, lakehouse processing, feature engineering, and final analysis/reporting.

The assignment prompt is in `task.png`. It requires web-based data gathering with automatic updates, a Big Data technology implementation, processing and analysis of stored data, and report/presentation outputs.

## Live Status Dashboard

[Visual progress dashboard](https://pol3et.github.io/railway-bigdata/) (GitHub Pages, served from `docs/`) — pipeline status, data inventory, and the fan-out/fan-in execution stages. Auto-updates on every push to `main` (allow up to ~10 min). Source: `docs/index.html`; task slugs match `docs/TASKS.md`.

## Quickstart

Use Python 3.12 or newer from this directory:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

Current verification result for this scaffold:

- `python -m pip install --no-cache-dir -e ".[test]"` passed.
- `python -m pytest -q` passed with 77 tests after adding the local stats Bronze -> Gold evidence path.
- `python -m compileall src tests` passed.
- GAP-004 fixture evidence was written to `output/evidence/fixture-e2e/railway_ml.parquet`.

## Current Status

The project now has one installable source tree:

- `src/railway_lakehouse/bronze/` contains raw ingestion, landing, scheduler, and source adapters.
- `src/railway_lakehouse/silver/` contains stats/news normalization and validation logic. Eurostat TSV + World Bank JSON fixtures now become `StatFact` rows; RSS XML + GDELT ArtList fixtures now become `ArticleRecord` rows.
- `src/railway_lakehouse/gold/` contains deterministic feature matrix builders and Parquet writing.
- `src/railway_lakehouse/pipeline.py` can read deterministic local Bronze stats/news fixtures via `--bronze-root`, including RSS XML, and can reproduce a bounded local stats-only Gold result from rerun Eurostat/World Bank raw Bronze artifacts. Live MinIO/Ollama/Spark runs are still unproven.
- `tests/` contains deterministic characterization and integration tests, including the GAP-004 fixture E2E path.

## Start Here

- `AGENTS.md` - agent routing and hard rules.
- `TASK.md` - assignment requirements and local acceptance criteria.
- `docs/INDEX.md` - documentation index.
- `docs/CODEMAP.md` - current file/module responsibilities.
- `docs/WORKSTREAMS.md` - how multiple contributors can work in parallel.
- `docs/GAP_REGISTER.md` - owner-ready gaps and test failure mapping.
- `docs/PROGRESS_LOG.md` - persistent findings and session log.

## Intended Architecture

```text
web sources
  -> Bronze raw landing
  -> Silver normalization and feature extraction
  -> Gold feature matrix
  -> Spark/lakehouse jobs and analysis outputs
  -> report + presentation
```

Current implementation uses Python, MinIO/S3-style paths, pandas transformations, Ollama for bounded JSON extraction, and a planned Spark/lakehouse integration track. The default local Ollama model is `qwen3.5:9b-q8_0`; use `OLLAMA_MODEL=qwen3.5:9b-q4_K_M` when memory is tighter.

## Development Rule

Do not claim live end-to-end MinIO/Ollama/Spark behavior until the exact command output is captured under `output/evidence/`. The current proven paths are deterministic fixture Bronze -> Silver -> Gold and a bounded local stats-only Bronze -> Gold reproduction from Eurostat/World Bank raw artifacts; the committed Gold feature in that real run is World Bank `rail_network_length_km`.
