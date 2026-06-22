# Railway Big Data Course Project

This directory is being shaped into a standalone course-project repo for railway data collection, lakehouse processing, feature engineering, and final analysis/reporting.

The assignment prompt is in `task.png`. It requires web-based data gathering with automatic updates, a Big Data technology implementation, processing and analysis of stored data, and report/presentation outputs.

## Quickstart

Use Python 3.12 or newer from this directory:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

Current verification result for this scaffold:

- `python -m pip install --no-cache-dir -e ".[test]"` passed.
- `python -m pytest -q` passed with 56 tests.
- `python -m compileall src tests` passed.
- GAP-004 fixture evidence was written to `output/evidence/fixture-e2e/railway_ml.parquet`.

## Current Status

The project now has one installable source tree:

- `src/railway_lakehouse/bronze/` contains raw ingestion, landing, scheduler, and source adapters.
- `src/railway_lakehouse/silver/` contains stats/news normalization and validation logic.
- `src/railway_lakehouse/gold/` contains deterministic feature matrix builders and Parquet writing.
- `src/railway_lakehouse/pipeline.py` can read deterministic local Bronze fixtures via `--bronze-root`; live MinIO runs are still unproven.
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

Do not claim live end-to-end MinIO/Ollama/Spark behavior until the exact command output is captured under `output/evidence/`. The current proven path is deterministic fixture Bronze -> Silver -> Gold only.
