# Workstreams

This project is split so multiple people can work without stepping on each other.

## 1. Project Organization / DevEx

Owns:

- `pyproject.toml`
- `.gitignore`
- `CONTRIBUTING.md`
- docs index
- pytest markers and test command
- package/import layout

Done now:

- Editable install works.
- Unit tests run.
- Code is under `src/railway_lakehouse`.

## 2. Bronze Core

Owns:

- `src/railway_lakehouse/bronze/config.py`
- `src/railway_lakehouse/bronze/lander.py`
- `src/railway_lakehouse/bronze/run.py`
- `src/railway_lakehouse/bronze/sources/`

Remaining:

- GAP-005: schedule KSH, Statistik Austria, UIC, and historical GDELT without changing raw landing semantics.
- `parser/ksh-stadat` Bronze source work is complete; KSH itself still needs
  scheduler wiring before it runs in the normal Bronze job.

## 3. Silver Stats Preprocessing

Owns:

- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/schema.py`

Remaining:

- GAP-006: read Bronze fixtures/storage and write auditable Silver outputs.
- Active branch `silver/stats-worldbank-eurostat`: GAP-006 Silver Stats slice
  for Eurostat TSV and World Bank JSON fixtures/storage.
- KSH-specific follow-up: implement KSH XLSX -> `StatFact` parsing and Silver
  parser tests against the six live-confirmed STADAT tables.

## 4. Silver News / Feature Audit

Owns:

- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/config.py`

Remaining:

- GAP-006: persist Silver news outputs and count extraction failures.
- Active branch `silver/news-rss-article-records`: GAP-006 Silver News slice
  for RSS XML/article-record fixtures and validated news output accounting.

## 5. Gold And Analysis

Owns:

- `src/railway_lakehouse/gold/build.py`
- `src/railway_lakehouse/gold/run.py`

Remaining:

- GAP-007: load Silver outputs and produce fixture-backed Gold Parquet evidence.
- The two active Silver branches are inputs to GAP-007 but do not close it
  unless they also wire Gold loading and record Gold row/column evidence.

## 6. Spark / Big Data Jobs

Owns:

- future `src/railway_lakehouse/spark_jobs/`
- Spark session/job entrypoints
- distributed reads and writes
- job evidence

Remaining:

- GAP-009: add a Spark job with row counts and generated outputs.

## 7. Live Ops / Real Data

Owns:

- `.env.example`
- service startup docs
- bounded live runs
- evidence under `output/evidence/`

Remaining:

- GAP-010: expand from fixture evidence to bounded live Bronze/Silver/Gold evidence.

## 8. Report And Presentation

Owns:

- future `output/report/`
- future `output/presentation/`
- charts/tables
- evidence-backed course narrative

Rule: report claims must point to generated artifacts.
