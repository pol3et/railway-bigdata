# GAP-005 Scheduler Decision

Date: 2026-06-22

Task: decide whether the primary owner should also take GAP-005 after taking
GAP-004, and whether GAP-005 blocks classmates.

## Local Research First

Files and commands reviewed:

- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `src/railway_lakehouse/bronze/run.py`
- `.planning/coursework/research/bigdata/current-state-next-plan-2026-06-22.md`
- Local search: `rg -n "GAP-005|scheduler|run.py|KSH|Statistik Austria|UIC|historical GDELT|past_recordings|bronze.run" docs src tests .planning`

## Decision

Defer GAP-005 from the primary owner path. The primary owner should work on
GAP-004 first: deterministic no-network Bronze fixture -> Silver -> Gold
Parquet.

GAP-005 is useful, but it is not the current course-score bottleneck. Scheduled
Bronze jobs do not prove analysis value until GAP-004/GAP-006/GAP-007 produce
Silver/Gold outputs and row/column evidence.

## Parallel Work

GAP-005 can be done in parallel by another classmate as a small Bronze-only PR,
provided it stays scoped:

- wire KSH, Statistik Austria, and UIC public PDF sources into the stats batch;
- keep historical GDELT out of automatic scheduler runs;
- keep long backfill one-off and opt-in only;
- do not run live scheduler or long collectors in tests;
- add mocked unit tests that prove `run_stats()` calls the configured source
  adapters through the existing `RawLander` contract.

## Non-Goals For GAP-005

- Do not claim live scheduled runs without executed manifest/log evidence.
- Do not make GAP-005 responsible for parsing KSH/Statistik Austria/UIC into
  `StatFact`; that is GAP-006.
- Do not schedule historical GDELT backfill by default.
- Do not block `silver/news-rss-article-records` or
  `silver/stats-worldbank-eurostat` on this work.

## Evidence

- This was a planning/status decision only.
- No source code, tests, live collectors, scheduler, MinIO, Ollama, Spark jobs,
  or historical backfills were run.
