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

- `python -m pip install --dry-run -e ".[test]" -c constraints.txt` confirmed pandas 3.0.3, pyarrow 24.0.0, and openpyxl 3.1.5 under the committed constraints.
- `python -m pytest -q` passed with 216 tests after adding the parser correctness audit; six Spark guards skipped because `JAVA_HOME`/Windows Spark prerequisites are absent.
- `python -m compileall -q src tests` passed.
- `python -m pytest -q` passed with 197 tests after adding GAP-045 macro-indicator coverage; 6 Spark tests skipped on this Windows worktree because JDK/Hadoop native prerequisites are absent.
- `python -m compileall -q src tests` passed after GAP-045.
- GAP-004 fixture evidence was written to `output/evidence/fixture-e2e/railway_ml.parquet`.
- GAP-009 Spark evidence was written to `output/evidence/spark/manifest.json` and `output/evidence/spark/coverage_by_geo_year/`.
- KSH live Bronze evidence was written to `output/evidence/pr24-ksh-live-check-after-fix/manifest.json` and parsed into Silver `StatFact` rows.
- GAP-045 macro-indicator evidence was written to `output/evidence/macro-indicators-gap045/`: World Bank `PA.NUS.PPP` reaches Gold for AT/HU, while `IS.VEH.PCAR.P3` is wired but currently has zero AT/HU non-null rows in the live API response.

## Current Status

The project now has one installable source tree:

- `src/railway_lakehouse/bronze/` contains raw ingestion, landing, scheduler, and source adapters.
- `src/railway_lakehouse/silver/` contains stats/news normalization, validation logic, and local Parquet persistence. Eurostat TSV, World Bank JSON, and KSH XLSX fixtures now become `StatFact` rows; World Bank macro ids map deterministically to `ppp_conversion_factor` and `cars_per_1000`; RSS XML + GDELT ArtList fixtures now become `ArticleRecord` rows.
- `src/railway_lakehouse/gold/` contains deterministic feature matrix builders and Parquet writing.
- `src/railway_lakehouse/pipeline.py` can read deterministic local Bronze stats/news fixtures via `--bronze-root`, including RSS XML, and can reproduce a bounded local stats-only Gold result from rerun Eurostat/World Bank raw Bronze artifacts. Local Spark evidence over real Gold is proven; full live MinIO/Ollama/news/Spark E2E remains unproven.
- `tests/` contains deterministic characterization and integration tests, including the GAP-004 fixture E2E path.

## Start Here

- `AGENTS.md` - agent routing and hard rules.
- `TASK.md` - assignment requirements and local acceptance criteria.
- `docs/INDEX.md` - documentation index.
- `docs/CODEMAP.md` - current file/module responsibilities.
- `docs/WORKSTREAMS.md` - how multiple contributors can work in parallel.
- `docs/GAP_REGISTER.md` - owner-ready gaps and test failure mapping.
- `docs/PROGRESS_LOG.md` - persistent findings and session log.
- `docs/PARSER_FIELD_COVERAGE.md` - per-source parser field coverage matrix.

## Intended Architecture

```text
web sources
  -> Bronze raw landing
  -> Silver normalization and feature extraction
  -> Gold feature matrix
  -> Spark/lakehouse jobs and analysis outputs
  -> report + presentation
```

Current implementation uses Python, MinIO/S3-style paths, pandas transformations, Ollama for bounded JSON extraction, optional sentence-transformers embeddings for Silver news dedup, and a planned Spark/lakehouse integration track. The default local Ollama model is `qwen3:4b`; override it with `OLLAMA_MODEL=...` only after recording the model/config change in evidence.

## Development Rule

Do not claim live end-to-end MinIO/Ollama/Spark behavior until the exact command output is captured under `output/evidence/`. The current proven paths are deterministic fixture Bronze -> Silver -> Gold, local Silver Parquet persistence, bounded local stats-only Bronze -> Gold reproductions from Eurostat/World Bank raw artifacts, the GAP-045 World Bank macro run at `output/evidence/macro-indicators-gap045/`, and a Spark coverage job over the real Gold Parquet at `output/evidence/inventory-live-2026-06-23/railway_ml.parquet`.

## News Feature Extraction

Silver news rows use a wide article-grain `NewsFeature` contract. The first 15 fields remain the legacy production surface consumed by current Gold (`article_id`, source/date fields, LLM gate/classification, operators/lines, money, summary, sentiment, confidence). GAP-039 adds reserved columns for deterministic language detection, XLM-R sentiment, GDELT GKG passthrough, per-field confidences, embeddings, dedup/cluster IDs, and extraction audit metadata. GAP-036 wires optional `intfloat/multilingual-e5-base` sentence embeddings into `text_embedding`; production Silver news extraction then assigns deterministic local near-duplicate markers in `cross_lingual_dedup_id` / `is_duplicate` whenever embeddings are present.
Silver news rows use a wide article-grain `NewsFeature` contract. The first 15 fields remain the legacy production surface consumed by current Gold (`article_id`, source/date fields, deterministic language ID, LLM gate/classification, operators/lines, money, summary, sentiment, confidence). GAP-039 adds reserved columns for XLM-R sentiment, GDELT GKG passthrough, per-field confidences, embeddings, dedup/cluster IDs, and extraction audit metadata.

Language detection runs before the LLM with pinned `lingua-language-detector==2.2.0`, restricted to EN/DE/HU for the current news pipeline. Expensive extraction is cached locally. `extract_cache_key()` hashes article identity plus title/body/url/date, and `model_digest_key()` hashes the current Ollama model name, prompt/schema, language-id identity, and config values. `FileSystemCache` stores JSON entries under `silver/.news_extraction_cache/<model_digest>/`; delete that directory to force a local re-extraction. The cache is git-ignored and is not a lakehouse table.

Known limitations:

- XLM-R sentiment is reserved but not wired yet (GAP-034).
- Operators/rail-line NER is reserved but not wired yet (GAP-038).
- Embedding storage and production local dedup markers are wired (GAP-036), but Spark-scale count enforcement remains GAP-037/GAP-040.
- Deterministic monetary parsing is reserved but not wired yet (GAP-036/GAP-050 follow-up).
- Translation/summarization quality work is not wired yet (GAP-050/GAP-033).
- `extraction_model_digest` is a prompt/config/model-name digest, not a hash of Qwen weights.
- Extraction failures are collected and can be written as a JSON sidecar; no failure Parquet table is claimed yet.

Install the optional news embedding stack only on machines that should compute
embeddings:

```bash
python -m pip install -e ".[news]"
```

The sentence-transformers model weights are downloaded by Hugging Face on first
use and cached outside the repo. Do not commit model weight files.

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

## Bronze scheduler runbook

One-line runbook: start automatic Bronze updates with `docker compose up -d minio createbuckets scheduler`, then inspect `docker compose logs -f scheduler` and `output/evidence/scheduler/*.json` for `status: "ok"` or `status: "degraded"`.

The `scheduler` service runs `python -m railway_lakehouse.bronze.run schedule` with `restart: unless-stopped` and writes local run-evidence manifests under `output/evidence/scheduler/`. If MinIO is down at boot or a batch raises a storage connection error, the batch degrades by logging a warning and writing a `status: "degraded"` manifest instead of killing the loop.

Native hosts can use a systemd timer or cron instead of the long-running Compose scheduler. The restart-safe native pattern is to run the one-off command `python -m railway_lakehouse.bronze.run all` from a host timer; systemd timers with `Persistent=true` can catch up one missed calendar activation after downtime. See `docs/OPERATIONS.md` for unit examples.

## Spark / Big Data engine setup

GAP-017 pins the optional Spark stack to the Python 3.14-compatible line:

```bash
python -m pip install -e ".[spark]"
```

That resolves only Python packages: PySpark 4.1.x and `delta-spark` 4.1.x. Spark runtime execution also requires a JDK 17 or 21 install with `JAVA_HOME` set; the Java 8 runtime is not sufficient for Spark 4.x. For Delta sessions use the matching Spark 4.1 Maven coordinate `io.delta:delta-spark_4.1_2.13:4.1.0`; for `s3a://` MinIO paths set `spark.jars.packages` to `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6` (also recorded as `SPARK_S3A_PACKAGES` in `.env.example` and `railway_lakehouse.spark_config`). The `hadoop-aws` Maven version must match Spark 4.x's bundled Hadoop 3.4.1 generation.

Spark 4.x runs with ANSI SQL behavior enabled by default. Prefer `try_cast()` for dirty source fields; use `spark.sql.ansi.enabled=false` only as a last resort and record that choice in evidence. PySpark writes Parquet as a directory containing part files and `_SUCCESS`, not as a single `.parquet` file.

On native Windows, `winutils.exe` and `hadoop.dll` must match Hadoop 3.4.x. WSL2 or Dockerized Spark avoids the native Hadoop DLL path.

Run the local Spark evidence job after installing the optional extra and setting
`JAVA_HOME` to JDK 17 or 21. On native Windows also set `HADOOP_HOME` to a Hadoop
3.4.x helper directory containing `bin/winutils.exe` and `bin/hadoop.dll`.

```bash
python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/inventory-live-2026-06-23/railway_ml.parquet --out output/evidence/spark/
```

Committed evidence: `output/evidence/spark/manifest.json` records Spark 4.1.2,
JDK 21.0.11, input Gold shape 2,968 rows x 4 columns, output coverage shape
2,968 rows x 5 columns, one Spark part-file, `_SUCCESS`, and the Spark-written
directory `output/evidence/spark/coverage_by_geo_year/`.
