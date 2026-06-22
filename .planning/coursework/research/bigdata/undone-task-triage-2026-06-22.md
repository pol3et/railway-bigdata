# Undone Task Triage

Date: 2026-06-22

Task: answer which parser/downstream tasks are missing, which should be taken
next, and which can run in parallel sessions.

## Local Research First

Files reviewed:

- `README.md`
- `TASK.md`
- `docs/PROGRESS_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/WORKSTREAMS.md`
- `docs/TEST_FIRST_INTEGRATION_PLAN.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/bronze/run.py`
- `src/railway_lakehouse/bronze/sources/gdelt.py`
- `src/railway_lakehouse/bronze/sources/past_recordings.py`
- `src/railway_lakehouse/bronze/sources/rss_media.py`
- `src/railway_lakehouse/bronze/sources/statistik_austria.py`
- `src/railway_lakehouse/bronze/sources/uic.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/gold/build.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`

## External Primary-Source Checks

- GDELT DOC 2.0 is the official full-text search API and supports JSON/JSONP
  output; GDELT also documents that hosted APIs have quotas and can return
  HTTP 429 when quota is exceeded.
  Sources:
  - https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
  - https://blog.gdeltproject.org/behind-the-scenes-api-quotas-the-impact-of-a-fraction-of-a-qps/
- Statistik Austria Open.data confirms machine-readable open datasets at
  `data.statistik.gv.at`, with CSV format details. The current catalog exposes
  `OGD_watlas23_WATLAS_23` for `Wirtschaftsatlas: Verkehr ... ab 2021`, with
  CSV resources and transport/rail fields including rail freight volume and
  passengers on rail.
  Sources:
  - https://www.statistik.at/services/tools/datenzugang/opendata
  - https://data.statistik.gv.at/web/catalog.jsp
  - https://data.statistik.gv.at/web/?page=formats
  - https://data.statistik.gv.at/ogd/json?dataset=OGD_watlas23_WATLAS_23
- UIC RAILISA is the official statistics surface. The public site says RAILISA
  has many railway indicators and a REST API, but download access can require
  annual subscription. The resources page also exposes a free Railway
  Statistics Synopsis PDF for the 2025 edition.
  Sources:
  - https://uic.org/support-activities/statistics/
  - https://uic-stats.uic.org/about/
  - https://uic-stats.uic.org/list/
  - https://uic-stats.uic.org/resources/
  - https://uic-stats.uic.org/resources/help_resource/?id=14

## Findings

- The user's list covers the main parser backlog, but it misses several
  integration blockers already tracked by gap IDs: GAP-004 fixture-backed
  Bronze reads, GAP-005 scheduler wiring, GAP-006 Silver persistence/parser
  outputs, GAP-007 Gold storage loading, GAP-009 Spark evidence, and GAP-011
  report/presentation.
- `live_check.py` currently supports only `rss` and `ksh`; any "bounded live
  check" for GDELT, Statistik Austria, UIC, Eurostat, or World Bank also needs
  a live-check collector or a separate documented command path.
- `past_recordings.py` still defaults to a large historical target and a broad
  time range. It needs safe defaults, dry-run, and explicit bounds before
  classmates run it.
- For fastest course progress, do not wait for GDELT, UIC, or Statistik
  Austria before building a first Gold dataset. Use proven sources first:
  RSS, KSH, Eurostat, and World Bank.
- Statistik Austria has a likely current candidate seed:
  `OGD_watlas23_WATLAS_23`, but this is only source research until the project
  code lands a real JSON/CSV artifact and records evidence.
- UIC should probably split into two decisions: free public PDF/synopsis
  artifact versus subscribed RAILISA CSV/Excel/API access. Do not keep chasing
  stale XLS URLs without recording the access boundary.

## Recommended Priority

1. Close the vertical slice blockers: GAP-004, minimal GAP-006, GAP-007, and
   then GAP-009. This creates the first evidence-backed Gold Parquet and Spark
   output.
2. In parallel, run Bronze parser hardening for RSS, GDELT, Statistik Austria,
   and UIC.
3. Keep GDELT history disabled by default until safe flags and retry tests
   exist.

## Parallelization

- Safe in parallel:
  - `parser/gdelt-rate-limit`
  - `parser/rss-feed-health`
  - `parser/statistik-austria-refresh`
  - `parser/uic-refresh`
  - `silver/stats-parsers` for proven Bronze fixtures only
  - `silver/news-parsers` using RSS fixtures
  - `spark/evidence-job` scaffold behind fixture Gold Parquet
- Merge order constraints:
  - Source parser PRs that touch `tests/test_bronze_characterization.py`,
    `tests/test_bronze_live_check.py`, `docs/PARSER_WORK_LOG.md`, or
    `docs/GAP_REGISTER.md` will conflict if merged blindly. Keep each PR small
    and rebase after every parser merge.
  - `gold/feature-matrix` needs at least fixture Silver rows.
  - `spark/evidence-job` needs a real or fixture Gold Parquet input before its
    evidence claim is valid.

## Evidence

- This was a planning/status pass only.
- No source code, tests, live collectors, Spark jobs, MinIO, or historical
  backfills were run.
- External checks used primary official sources listed above.
