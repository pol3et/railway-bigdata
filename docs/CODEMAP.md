# Code Map

Last mapped: 2026-06-21

Scope: current filesystem under `bigdata/course_proj`.

## Top Level

| Path | Responsibility | Notes |
|---|---|---|
| `task.png` | Assignment prompt image. | Requires web collection, automatic updates, Big Data technology, analysis/report/presentation. |
| `AGENTS.md` | Project-local agent router. | Start here for future agents. |
| `README.md` | Project overview, quickstart, and current status. | Includes install and pytest commands. |
| `TASK.md` | Course requirements mapped to local deliverables. | Use for acceptance checks. |
| `pyproject.toml` | Packaging, dependencies, extras, and pytest markers. | Editable install target. |
| `CONTRIBUTING.md` | Contributor workflow, gap IDs, evidence rules. | Root-level GitHub contributor guidance. |
| `.gitignore` | Repo-local ignore rules. | Keeps runtime/cache artifacts out of commits. |
| `WIRING.md` | Remaining source-scheduling note. | Now focused on GAP-005, not file copying. |
| `docs/` | Durable documentation set. | Code map, architecture, contracts, verification, progress, gaps. |
| `tests/` | Pytest characterization suite. | Deterministic tests plus strict expected failure for GAP-004. |
| `output/` | Student-facing evidence and notes. | Runtime scratch belongs under `output/runtime/`. |

## Source Package

Path: `src/railway_lakehouse/`

| File | Responsibility |
|---|---|
| `__init__.py` | Package marker for editable installs. |
| `pipeline.py` | End-to-end Bronze -> Silver -> Gold orchestration skeleton; Bronze read stubs remain GAP-004. |

## Bronze

Path: `src/railway_lakehouse/bronze/`

| File | Responsibility |
|---|---|
| `config.py` | Environment-driven MinIO settings, country scope, multilingual rail terms, RSS feed registries. |
| `lander.py` | `RawLander` and `RawArtifact`; writes raw bytes plus metadata sidecars to Bronze MinIO paths. |
| `run.py` | Bronze orchestrator with `stats`, `news`, `all`, and `schedule` modes. |
| `sources/eurostat.py` | Discovers rail datasets from Eurostat TOC and lands raw compressed TSV data. |
| `sources/worldbank.py` | Discovers rail indicators and lands raw World Bank JSON time series. |
| `sources/gdelt.py` | Pulls recent GDELT DOC API article lists for scoped railway queries. |
| `sources/rss_media.py` | Lands full RSS feeds for configured media and official operator sources. |
| `sources/ksh.py` | Curated Hungarian KSH STADAT rail table fetcher; validates XLSX workbook containers and lands six live-confirmed raw files through `RawArtifact`. |
| `sources/statistik_austria.py` | Austrian statistics fetcher seeds; lands JSON/CSV raw files through `RawArtifact`. |
| `sources/uic.py` | UIC RAILISA public statistical publication fetcher; validates and lands raw PDF files, with subscribed CSV/Excel/API access documented as a boundary. |
| `sources/past_recordings.py` | One-off historical GDELT backfill with DOC API and GKG v1 modes. |

Current status: Bronze code is consolidated under one package. `parser/ksh-stadat` Bronze source work is complete and live-validated, and `parser/uic-refresh` now lands current public UIC publication PDFs with bounded live evidence. GAP-005 remains because KSH, UIC, and the other new national/historical source adapters are present but not scheduled by `bronze/run.py`.

## Silver

Path: `src/railway_lakehouse/silver/`

| File | Responsibility |
|---|---|
| `config.py` | Ollama settings, MinIO settings, canonical stats features, news taxonomy. |
| `schema.py` | Dataclass schemas for `StatFact` and `NewsFeature`, plus news validation. |
| `ollama_client.py` | JSON-mode Ollama client with retries and loose JSON parsing. |
| `run.py` | Silver orchestration helpers for stats and news; storage I/O remains unwired. |
| `stats/merge.py` | Deterministic readers, cached crosswalk, and long-format stats merge. |
| `news/extract.py` | Article-to-`NewsFeature` extraction via Ollama plus GDELT passthrough. |

Current status: transformation logic is characterized by unit tests. Bronze/Silver storage integration remains GAP-006, including the open KSH XLSX -> `StatFact` parser/tests follow-up.

## Gold

Path: `src/railway_lakehouse/gold/`

| File | Responsibility |
|---|---|
| `build.py` | Resolves stats conflicts, pivots stats wide, aggregates news, joins Gold table, writes Parquet. |
| `run.py` | Importable `build_from_silver` and CLI placeholder for future Silver reads. |

Current status: deterministic Gold logic is characterized by unit tests. Silver-to-Gold storage loading remains GAP-007.

## Tests

| File | Responsibility |
|---|---|
| `tests/test_bronze_characterization.py` | Bronze metadata, discovery, and GDELT query behavior. |
| `tests/test_bronze_live_check.py` | Local Bronze live-check manifest, source-result, RSS, and KSH collector behavior with mocked HTTP. |
| `tests/test_bronze_live_check_integration.py` | Deterministic integration fixture for KSH live-check manifest, raw Bronze file, and metadata writing. |
| `tests/test_silver_characterization.py` | Silver stats melt/crosswalk/merge and news validation/extraction behavior. |
| `tests/test_gold_characterization.py` | Gold conflict resolution, pivot, news aggregation, zero fill, Parquet write. |
| `tests/test_pipeline_gaps.py` | Strict expected failure for GAP-004 pipeline Bronze read stubs. |

## Missing Or Not Yet Implemented

- No Spark job exists under `src/railway_lakehouse/spark_jobs/` yet.
- No deterministic fixture E2E exists yet; current tests are unit-level plus one expected pipeline failure.
- No live MinIO/Ollama/Spark evidence has been generated in this session.
- Report and presentation outputs are not started beyond organization notes.
