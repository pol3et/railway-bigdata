# Architecture

## Course-Facing Story

The project presents a railway lakehouse:

```text
Web APIs and RSS feeds
  -> Bronze raw landing
  -> Silver preprocessing and feature extraction
  -> Gold analytical feature matrix
  -> Spark / Big Data jobs
  -> report and presentation evidence
```

## Package Layout

```text
src/railway_lakehouse/
  bronze/
    config.py
    lander.py
    run.py
    sources/
  silver/
    config.py
    schema.py
    ollama_client.py
    run.py
    stats/
    news/
  gold/
    build.py
    run.py
  pipeline.py
```

## Layers

### Bronze: Raw Collection

Purpose: collect source bytes and provenance without transforming the data.

Current files:

- `src/railway_lakehouse/bronze/lander.py`
- `src/railway_lakehouse/bronze/run.py`
- `src/railway_lakehouse/bronze/sources/*.py`

Boundary: source fetchers produce `RawArtifact`; `RawLander` is the only writer to Bronze paths.

### Silver: Preprocessing And Feature Extraction

Purpose: convert raw stats and raw news into validated structured records.

Current files:

- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/ollama_client.py`

Boundary: deterministic code handles numeric tables. Ollama may extract unstructured article facts or propose label mappings, but all output is validated.

Model default: local Ollama uses `qwen3.5:9b-q8_0` unless `OLLAMA_MODEL`
overrides it. The default is quality-first for multilingual HU/DE/EN extraction
and uses Ollama's 9B Q8_0 tag. Use `OLLAMA_MODEL=qwen3.5:9b-q4_K_M` when the
11 GB Q8_0 model is too large for the machine. The client calls `/api/chat`,
passes JSON schema through `format`, sets deterministic output options, and
sets top-level `think: false` by default so reasoning traces do not consume the
JSON response budget.

### Gold: Analytical Dataset

Purpose: build a wide feature matrix at `(geo, year)` grain for analysis and modeling.

Current files:

- `src/railway_lakehouse/gold/build.py`
- `src/railway_lakehouse/gold/run.py`

Boundary: Gold consumes Silver tables, resolves source conflicts, aggregates news, and writes Parquet.

### Spark / Big Data Integration

Purpose: satisfy the Big Data technology requirement with distributed processing evidence.

Current status: no Spark module exists yet. Future work should add `src/railway_lakehouse/spark_jobs/` that consumes Gold/Silver Parquet and writes documented outputs.

## Current Main Gap

`src/railway_lakehouse/pipeline.py` now has deterministic fixture-backed Bronze reads for GAP-004:

- `_read_bronze_eurostat(...)`
- `_read_bronze_news(...)`

The proven path is local fixture Bronze -> Silver transforms -> Gold Parquet under `output/evidence/fixture-e2e/`.

Remaining architecture gaps are live MinIO/service execution, Silver persistence, Gold storage loading, Spark jobs, and report/presentation evidence.
