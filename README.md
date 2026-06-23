# Railway Big Data Course Project

This directory is being shaped into a standalone course-project repo for railway data collection, lakehouse processing, feature engineering, and final analysis/reporting.

The assignment prompt is in `task.png`. It requires web-based data gathering with automatic updates, a Big Data technology implementation, processing and analysis of stored data, and report/presentation outputs.

## Live Status Dashboard

[Visual progress dashboard](https://pol3et.github.io/railway-bigdata/) (GitHub Pages, served from `docs/`) — pipeline status, data inventory, and the fan-out/fan-in execution stages. Auto-updates on every push to `main` (allow up to ~10 min). Source: `docs/index.html`; task slugs match `docs/TASKS.md`.

## Quickstart

Use Python 3.12 through 3.14 from this directory:

```bash
python -m pip install -e ".[test]" -c constraints.txt
python -m pytest -q
```

The `-c constraints.txt` flag reproduces the graded Python 3.14 runtime/test stack. Omitting it lets the resolver drift to newer dependency majors; `tests/test_env_versions.py` catches unsupported pandas/pyarrow majors.

Current verification result for this scaffold:

- `python -m pip install --dry-run -e ".[test]" -c constraints.txt` confirmed pandas 3.0.3 and pyarrow 24.0.0 under the committed constraints.
- `python -m pytest -q` passed with 92 tests after adding Silver persistence, the local stats Bronze -> Gold evidence path, the MinIO infra guard, and the environment-version guard.
- `python -m compileall -q src tests` passed.
- GAP-004 fixture evidence was written to `output/evidence/fixture-e2e/railway_ml.parquet`.

## Current Status

The project now has one installable source tree:

- `src/railway_lakehouse/bronze/` contains raw ingestion, landing, scheduler, and source adapters.
- `src/railway_lakehouse/silver/` contains stats/news normalization, validation logic, and local Parquet persistence. Eurostat TSV + World Bank JSON fixtures now become `StatFact` rows; RSS XML + GDELT ArtList fixtures now become `ArticleRecord` rows.
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

Do not claim live end-to-end MinIO/Ollama/Spark behavior until the exact command output is captured under `output/evidence/`. The current proven paths are deterministic fixture Bronze -> Silver -> Gold, local Silver Parquet persistence, and a bounded local stats-only Bronze -> Gold reproduction from Eurostat/World Bank raw artifacts; the committed Gold feature in that real run is World Bank `rail_network_length_km`.

## Local lakehouse (MinIO)

A local S3-compatible object store is provided for the live Bronze/Silver/Gold lakehouse path (GAP-010). Defaults match `bronze/config.py` and `silver/config.py`, so the stack works without changing project code.

```bash
cp .env.example .env
docker compose up -d
python scripts/minio_smoke.py
```

Expected smoke evidence:

```text
output/evidence/minio-smoke/manifest.json
```

The Docker stack exposes:

- MinIO S3 API: `http://localhost:9000`
- MinIO console: `http://localhost:9001`
- default login: `admin` / `password123`

The `createbuckets` service creates `bronze`, `silver`, and `gold` buckets idempotently. Stop the stack with:

```bash
docker compose down
```

Use `docker compose down -v` only when you intentionally want to delete the local MinIO volume.

## Spark / Big Data engine setup

GAP-017 pins the optional Spark stack to the Python 3.14-compatible line:

```bash
python -m pip install -e ".[spark]"
```

That resolves PySpark 4.1.x and `delta-spark` 4.1.x. Spark runtime execution also requires a JDK 17 or 21 install with `JAVA_HOME` set; the Java 8 runtime is not sufficient for Spark 4.x. For Delta sessions use the matching Spark 4.1 Maven coordinate `io.delta:delta-spark_4.1_2.13`; for `s3a://` MinIO paths use `org.apache.hadoop:hadoop-aws:3.4.1` plus the AWS SDK v2 `software.amazon.awssdk:bundle` artifact. The `hadoop-aws` version must match Spark 4.x's bundled Hadoop 3.4.1 generation.

Spark 4.x runs with ANSI SQL behavior enabled by default. Prefer `try_cast()` for dirty source fields; use `spark.sql.ansi.enabled=false` only as a last resort and record that choice in evidence. PySpark writes Parquet as a directory containing part files and `_SUCCESS`, not as a single `.parquet` file.

On native Windows, `winutils.exe` and `hadoop.dll` must match Hadoop 3.4.x, not 3.3.x. WSL2 or Dockerized Spark avoids the native Hadoop DLL path.
