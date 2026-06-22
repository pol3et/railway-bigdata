# Current State And Next Plan

Date: 2026-06-22

Task: inspect current merged code state after PR #5, #6, and #7; evaluate the
classmate's staged plan; recommend what to do next and what can run in
parallel.

## Local Research First

Files and commands reviewed:

- `git status --short --branch`
- `git log --oneline --decorate -12`
- `README.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/WORKSTREAMS.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `pyproject.toml`
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/bronze/run.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/silver/run.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/gold/build.py`
- `src/railway_lakehouse/gold/run.py`
- `tests/test_silver_characterization.py`
- `tests/test_gold_characterization.py`
- `tests/test_pipeline_gaps.py`
- `tests/test_bronze_characterization.py`

## External Research

- Apache Spark's official Parquet docs confirm Spark SQL can read/write
  Parquet and preserve schema, which supports the planned Gold Parquet ->
  Spark evidence path.
  Source: https://spark.apache.org/docs/latest/sql-data-sources-parquet.html

## Current Code State

- Local `main` is at `2dc5091`, matching `origin/main`.
- PR #5, PR #6, and PR #7 are present in local history.
- Untracked local directories are present: `.serena/` and `.ship/`.
- Full deterministic verification currently passes:
  - `python -m pytest -q` -> `53 passed, 1 xfailed`.
  - The xfail is `tests/test_pipeline_gaps.py::test_pipeline_storage_read_stubs_are_not_wired`, mapped to GAP-004.
  - `python -m compileall src tests` passed.
- Bronze parser status is much better than before:
  - RSS feed health: partial live-ok, 9 artifacts, 1 stale `hu_origo`.
  - KSH: live-ok for six XLSX tables.
  - Statistik Austria: live-ok for five `.ods` artifacts, invalid HTTP-200 bodies rejected.
  - UIC: live-ok for two public PDFs; subscribed RAILISA exports remain access-limited.
  - Eurostat and World Bank have bounded live evidence and unit-tested Bronze validation.
  - GDELT has retry/safety tests, but latest bounded live probe still landed zero artifacts.
- Core project blockers remain:
  - GAP-004: `pipeline.py` Bronze read stubs.
  - GAP-006: Silver persistence and missing concrete parsers for RSS XML, KSH XLSX, Statistik Austria `.ods`, UIC PDF, and storage writes.
  - GAP-007: Gold storage loading/output evidence.
  - GAP-009: no Spark job module exists.
  - GAP-011: no report/presentation outputs exist.

## Evaluation Of Classmate Draft

Mostly correct:

- Silver/news and Silver/stats can start in parallel.
- GAP-004 fixture E2E is the highest-priority infrastructure task.
- Spark should wait until there is a Gold Parquet input.
- Report and presentation should wait for evidence, though outline work can start.

Corrections:

- World Bank JSON and Eurostat TSV readers already exist at a primitive level
  in `silver/stats/merge.py`; the missing work is validating them against
  Bronze-shaped JSON/TSV fixtures, adding source-system columns, and persisting
  Silver outputs.
- GAP-004 should not be owned separately from all Silver wiring. It should
  establish local Bronze fixture readers and a no-network Bronze -> Silver ->
  Gold smoke path.
- Gold feature matrix logic already exists and has unit tests. The next Gold
  task is storage/evidence integration, not inventing the pivot logic from
  scratch.
- KSH should move earlier if the stats owner has bandwidth because KSH has the
  strongest live national-source evidence. It is not required for the minimal
  first vertical slice if World Bank + Eurostat are faster.
- GDELT should not be part of immediate Silver work because there is no current
  live Bronze GDELT artifact.

## Recommended Next Work

Stage A, parallel:

1. Silver news: RSS XML -> article records, then deterministic/mockable
   article records -> `NewsFeature`.
2. Silver stats: World Bank JSON -> `StatFact`, Eurostat TSV -> `StatFact`,
   with KSH XLSX as the next source if time allows.
3. Fixture E2E/GAP-004: local Bronze fixture readers that feed existing Silver
   readers and Gold writer with no network, no MinIO, no Ollama.

Stage A is done when:

- RSS fixture XML produces article records.
- At least World Bank and Eurostat fixture inputs produce valid `StatFact`
  rows.
- A no-network integration test writes a Gold Parquet under `tmp_path` or
  documented `output/evidence/fixture-e2e/`.
- `python -m pytest -q -m integration` has no GAP-004 xfail.

Stage B, parallel:

1. Finish KSH XLSX -> `StatFact`; optionally Statistik Austria `.ods` if ODS
   parsing dependency is added deliberately.
2. Wire Silver persisted outputs and Gold storage loading under GAP-006/GAP-007.
3. Promote fixture E2E into a documented command that records row and column
   counts.

Stage C:

1. Spark evidence job reads Gold Parquet and writes row-count/aggregate outputs.
2. Report uses only generated evidence.
3. Presentation follows the same evidence.

## Parallelization Notes

- Safe parallel tracks now:
  - `silver/news-rss-article-records`
  - `silver/stats-worldbank-eurostat`
  - `pipeline/fixture-e2e-gap004`
  - `silver/stats-ksh-xlsx` after the stats owner creates shared `StatFact`
    conventions or in a branch that rebases often.
- Do not run these yet as evidence claims:
  - Spark job, until Gold Parquet exists.
  - Report/presentation claims, until output evidence exists.
  - GDELT Silver parser, until raw ArtList JSON exists.

## Evidence From This Session

- `python -m pytest -q` passed: 53 passed, 1 xfailed for GAP-004.
- `python -m compileall src tests` passed.
- No source code was changed.
- No live collectors, MinIO, Ollama, Spark jobs, or long historical backfills
  were run.
