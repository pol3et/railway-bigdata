# Project Progress And Findings Log

This is the single persistent log for `bigdata/course_proj`. Future agents should append here before stopping.

## 2026-06-25 - GAP-042 Statistik Austria ODS Reader

Status: done; ready for PR.

Changed:
- `pyproject.toml`
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `tests/test_silver_stats_stataustria.py`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/STATE_AND_ROADMAP.md`
- `.planning/coursework/research/bigdata/silver-stataustria-ods-reader.md`
- `.planning/coursework/plans/bigdata/gap-042-stataustria-ods-reader.md`

Findings:
- The original GAP-042 spec was right on `odfpy`/pandas ODS IO, but thin on real file layout: the freight ODS stores years as `Berichtsjahr YYYY` rows with totals under `Insgesamt`, while rolling-stock files use repeated year-column header blocks.
- `load_stataustria_frame` now reads ODS bytes deterministically, emits `geo=AT` `StatFact` rows, preserves German source labels, and registers `statistik_austria` in `_SOURCES`.
- Narrow German crosswalk rules map the emitted total freight and rolling-stock labels without LLM use; numeric values still come only from pandas coercion.

Evidence:
- TDD RED: `python -m pytest -q tests/test_silver_stats_stataustria.py` failed before implementation with missing `load_stataustria_frame` and missing `.ods` routing.
- `python -m pip install -e ".[test]"` passed and installed/confirmed `odfpy==1.4.1`.
- `python -m pytest -q tests/test_silver_stats_stataustria.py` -> 5 passed.
- `python -m pytest -q -m unit` -> 175 passed, 31 deselected.
- `python -m pytest -q` -> 200 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF normalization warnings only.
- Bounded runtime smoke over direct Statistik Austria ODS downloads under `output/runtime/gap-042-layout/` parsed all five current ODS files; raw downloads remain uncommitted runtime output.

Next:
- Commit, push `impl/gap-042`, open the PR against `main`, and confirm mergeability.

## 2026-06-24 - GAP-019 Deployable Bronze Scheduler

Status: closed — implemented by the Codex agent (its exec sandbox could not spawn `python`/`git`/`gh`, recorded honestly below); verified + shipped by the orchestrator: `python -m pytest -q -m unit tests/test_bronze_scheduler.py` → 4 passed; full `python -m pytest -q` (JAVA_HOME=jdk-21) → 127 passed, 1 skipped; `python -m compileall -q src tests` clean. Rebased on GAP-013 and merged via PR.

Changed:
- `src/railway_lakehouse/bronze/run.py`
- `tests/test_bronze_scheduler.py`
- `docker-compose.yml`
- `Dockerfile`
- `README.md`
- `docs/OPERATIONS.md`
- `docs/INDEX.md`
- `docs/CODEMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/gap019-deployable-scheduler-spec-2026-06-24.md`
- `.planning/coursework/plans/bigdata/gap-019-deployable-scheduler.md`

Findings:
- `RawLander` write semantics were not changed; GAP-019 edits are limited to scheduler orchestration, deploy host, docs, and deterministic tests.
- The scheduler now preflights MinIO with `s3fs.S3FileSystem.exists(BRONZE_BUCKET)`, writes `ok`/`degraded` JSON manifests under `output/evidence/scheduler/`, and wraps `schedule.run_pending()` in `_tick()` so one failing batch does not kill cadence.
- Compose now includes a `scheduler` service with `restart: unless-stopped`, `depends_on: minio`, internal `S3_ENDPOINT=http://minio:9000`, and host-mounted scheduler evidence.

Evidence:
- RED attempt: `python -m pytest -q -m unit tests/test_bronze_scheduler.py` could not start because the default shell runner failed spawning `python` with `windows sandbox: runner error: CreateProcessAsUserW failed: 5`.
- Retry through Serena shell execution was rejected before running, so no pytest, compileall, `git diff --check`, commit, push, or PR result is claimed.

Next:
- Run `python -m pytest -q -m unit tests/test_bronze_scheduler.py`, `python -m pytest -q`, `python -m compileall -q src tests`, and `git diff --check`; fix any failures, then commit, push `impl/gap-019`, and open the PR against `main`.

## 2026-06-24 - GAP-018 Dependency Bounds And Lockfile

Status: done for implementation and local verification; PR opened from `impl/gap-018`.

Changed:
- `pyproject.toml`
- `constraints.txt`
- `tests/test_env_versions.py`
- `README.md`
- `docs/VERIFICATION.md`
- `docs/GAP_REGISTER.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/gap-018-dependency-bounds-lockfile-2026-06-24.md`
- `.planning/coursework/plans/bigdata/gap-018-dependency-bounds-lockfile.md`

Findings:
- Active validated environment is Python 3.14.0 with pandas 3.0.3, pyarrow 24.0.0, requests 2.33.1, schedule 1.2.2, and the existing S3 pins (`s3fs`/`fsspec` 2024.6.1, `aiobotocore` 2.13.1, `botocore` 1.34.131).
- GAP-018 is ops-only: no Bronze/Silver/Gold data-path code changed, the four exact S3 pins stayed unchanged, and the `[spark]` extra stayed untouched for GAP-017.
- `constraints.txt` records the runtime + `[test]` closure from the active env and excludes editable self-references and unrelated IDE/build packages.

Evidence:
- RED: `python -m pytest -q tests/test_env_versions.py` failed before metadata/constraints edits with 2 failed, 3 passed (missing `requires-python` upper bound and missing `constraints.txt`).
- GREEN: `python -m pytest -q tests/test_env_versions.py` passed: 5 passed.
- `python -m pytest -q` passed: 92 passed.
- `python -m pytest -q -m unit` passed: 82 passed, 10 deselected.
- `python -m pytest -q -m integration` passed: 10 passed, 82 deselected.
- `python -m compileall -q src tests` exited 0.
- `python -m pip install --dry-run -e ".[test]" -c constraints.txt` exited 0 and reported pandas 3.0.3 for `pandas<4,>=2.2` and pyarrow 24.0.0 for `pyarrow<25,>=15`.
- `git diff --check` exited 0.

Next:
- Review and merge the GAP-018 PR after GitHub reports it mergeable.

## 2026-06-23 - State Snapshot, Inventory, And Spark Roadmap

Status: done for read-only analysis + documentation; no source code changed.

Changed:
- `docs/STATE_AND_ROADMAP.md` (new authoritative state + roadmap + engine decision)
- `docs/INDEX.md` (index row for the new doc)
- `docs/PROGRESS_LOG.md` (this entry)
- `.planning/coursework/research/bigdata/state-analysis-spark-roadmap-2026-06-23.md` (new research log)
- `.planning/COURSEWORK_PROGRESS.md` (session entry)

Findings:
- Project is at the end of the storage-boundary phase / start of the Spark phase.
  Bronze landing operational (4 scheduled; KSH/StatAustria/UIC live-proven but not
  scheduled, GAP-005). Silver normalizes World Bank + Eurostat stats and RSS +
  GDELT news in-memory only; no persisted Silver writer (GAP-006). Gold matrix
  builder works + writes Parquet but only from a 4-row fixture; `gold/run.py`
  storage-load is a stub (GAP-007).
- Only end-to-end artifact: `output/evidence/fixture-e2e/railway_ml.parquet`
  (4 rows x 3 cols, news skipped). Live evidence proves raw Bronze landing only.
- Task list 9-12: #9 stats-parsers 2/5 (Eurostat + World Bank done; KSH XLSX /
  Statistik Austria ODS / UIC PDF readers missing). #10 news-parsers 3/3 (LLM step
  mocked in tests). #11 gold feature-matrix done on fixture (GAP-007 storage-load
  open). #12 spark/evidence-job 0/3, not started (GAP-009).
- Stale-list corrections: UIC is PDF (not XLS); Statistik Austria is ODS (its OGD
  JSON/CSV has no rail dataset). `merge.read_tabular_long` and
  `extract.gdelt_passthrough` are written-but-uncalled stubs ready to wire.
- Engine recommendation: Apache Spark/PySpark (rubric-aligned), Delta Lake on
  Parquet, pinned Spark 3.5.x / Scala 2.12 / delta-spark 3.2.x / hadoop-aws 3.3.4
  / JDK 17 + winutils on Windows; DuckDB/Polars as EDA/benchmark sidecar; raise
  real volume via the existing `past_recordings` GDELT backfill.

Evidence:
- No source edits, tests, live collectors, MinIO, Ollama, or Spark runs were
  executed for this analysis. Research routed via `research-orchestrator`
  (Context7, Tavily, Exa, Ref); citations in the research log above.

Next:
- Critical path: GAP-006 (min Silver persist) -> GAP-007 (Gold<-Silver) ->
  GAP-009 (Spark evidence) -> GAP-011 (report). GAP-010 live + GDELT volume
  backfill run in parallel. Estimated ~2.5-4 days to first Spark evidence.

## 2026-06-23 - PR #9 And #10 Ship-PR Review

Status: done for read-only review; no PR comments posted and no PR branches changed.

Changed:
- `.ship/pr/9/report.md`
- `.ship/pr/9/mode.json`
- `.ship/pr/9/sources.json`
- `.ship/pr/10/report.md`
- `.ship/pr/10/mode.json`
- `.ship/pr/10/sources.json`
- `.planning/coursework/research/bigdata/pr9-pr10-review-2026-06-23.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- Open GitHub queue contained PR #9 and PR #10.
- PR #9 is the Silver News article-record slice; it adds RSS/GDELT parsers, but it is not mergeable with current `main` and has blank-URL article-id collisions.
- PR #10 is the Silver Stats World Bank/Eurostat slice; it is mergeable, but it normalizes World Bank `AUT` as `AU`, splitting Austria from project `AT` rows downstream.
- The two PRs are conceptually complementary for GAP-006 but conflict in shared test/docs surfaces, especially `tests/test_silver_characterization.py`.

Evidence:
- PR #9 report: `.ship/pr/9/report.md`.
- PR #10 report: `.ship/pr/10/report.md`.
- `python -m pytest -q tests\test_silver_characterization.py` passed in PR #9 worktree with `PYTHONPATH=src`: 8 passed.
- `python -m pytest -q` passed in PR #9 worktree with `PYTHONPATH=src`: 56 passed, 1 xfailed.
- `python -m pytest -q tests\test_silver_characterization.py tests\test_silver_stats_integration.py` passed in PR #10 worktree with `PYTHONPATH=src`: 11 passed.
- `python -m pytest -q` passed in PR #10 worktree with `PYTHONPATH=src`: 64 passed.
- `git merge-tree --write-tree origin/main origin/silver/news-parsers` reported a content conflict in `tests/test_silver_characterization.py`.
- `git merge-tree --write-tree origin/main origin/silver/stats-worldbank-eurostat` produced a clean merge tree.
- Refute-only review challenged four blocking/major findings and dropped none.

Next:
- Fix PR #10 `AUT -> AT` normalization and Austria test coverage before merge.
- Rebase/fix PR #9 after current main/PR #10 state is settled, preserving both Silver stats and news tests.

## 2026-06-21 - Documentation Scaffold And Intake Map

Status: done.

Research:

- Required coursework research log: `.planning/coursework/research/bigdata/course-project-organization.md`.
- External provider routed through `research-orchestrator`: Context7 for Apache Spark docs.

Files read:

- `task.png`
- `WIRING.md`
- `bronze/bronze/*.py`
- `bronze/bronze/sources/*.py`
- `railway_lakehouse/PIPELINE.md`
- `railway_lakehouse/SILVER_DESIGN.md`
- `railway_lakehouse/pipeline.py`
- `railway_lakehouse/bronze/sources/*.py`
- `railway_lakehouse/silver/**/*.py`
- `railway_lakehouse/gold/*.py`
- `bigdata/COURSE_TASKS.md`
- existing `.planning/codebase/*.md`

Findings:

- The current filesystem does not contain the older `bigdata/course_proj/parser` tree referenced by stale planning docs.
- The current project has two overlapping code locations:
  - `bronze/bronze/` is the implemented ingestion package.
  - `railway_lakehouse/` is the intended integrated project structure.
- `railway_lakehouse/pipeline.py` still has explicit MinIO read stubs.
- New national/historical Bronze source modules exist under `railway_lakehouse/bronze/sources/`, but are not wired into `bronze/bronze/run.py`.
- Silver stats/news logic and Gold feature-building logic exist, but no local tests or output evidence were found.
- No project-local `requirements.txt`, `pyproject.toml`, lockfile, Docker Compose file, or tests were found under `bigdata/course_proj`.

Files changed:

- `AGENTS.md`
- `README.md`
- `TASK.md`
- `docs/INDEX.md`
- `docs/CODEMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_CONTRACTS.md`
- `docs/WORKSTREAMS.md`
- `docs/AGENTIC_WORKFLOW.md`
- `docs/VERIFICATION.md`
- `docs/ORGANIZATION_PLAN.md`
- `docs/PROGRESS_LOG.md`

Evidence:

- `python -m compileall bigdata\course_proj` passed syntax compilation for current Python files.
- Secret-pattern scan over new docs and output notes found no matches.
- `Get-ChildItem -Recurse -Directory bigdata\course_proj -Filter __pycache__` found no remaining bytecode cache directories after cleanup.

Next:

- Add dependency manifest and tests for pure Silver/Gold logic.
- Decide final package layout before moving Bronze files.
- Wire `railway_lakehouse/pipeline.py` storage stubs only after a small fixture/smoke design is approved.

## 2026-06-21 - Merge Strategy Follow-Up

Status: done.

Research:

- Required workflow: `research-orchestrator`.
- Context7 source: Python Packaging User Guide for `pyproject.toml` and `src/` layout.
- Context7 source: GitHub Docs for repository `.gitignore` and contributing guidelines.

Evidence:

- `python -c "import sys; sys.path.insert(0, r'bigdata/course_proj'); import railway_lakehouse.pipeline"` failed with `ModuleNotFoundError: No module named 'pandas'`.
- `python -c "import sys; sys.path.insert(0, r'bigdata/course_proj/bronze'); import bronze.run"` failed with `ModuleNotFoundError: No module named 's3fs'`.
- `python -c "import sys; sys.path.insert(0, r'bigdata/course_proj/railway_lakehouse'); import silver.run, gold.run"` failed with `ModuleNotFoundError: No module named 'pandas'`.
- `rg -n "NotImplementedError|WIRE|TODO|placeholder|MISSING|not yet|not wired|stub" ...` found the expected pipeline/storage wiring gaps.

Files changed:

- `docs/MERGE_STRATEGY.md`
- `docs/INDEX.md`
- `docs/PROGRESS_LOG.md`

Finding:

- The code is aligned around one railway lakehouse goal, but it is not one working project yet. The cleanest merge path is to create one installable `railway_lakehouse` package, consolidate Bronze into it, then wire storage and Spark jobs.

## 2026-06-21 - Next-Session Handoff And Test-First Plan

Status: done.

Research:

- Required workflow: `research-orchestrator`.
- Context7 source: pytest docs for test discovery, `tmp_path`, and `monkeypatch`.

Files changed:

- `docs/NEXT_SESSION_HANDOFF.md`
- `docs/TEST_FIRST_INTEGRATION_PLAN.md`
- `docs/WORK_SPLIT.md`
- `docs/INDEX.md`
- `.planning/.continue-here.md`
- `.planning/HANDOFF.json`

Evidence:

- `.planning/HANDOFF.json` parsed successfully with `python -m json.tool`.
- Secret-pattern scan over handoff/planning docs found no matches.
- Documentation inventory confirmed the new handoff, plan, and work split files exist.

Finding:

- The next session should create repo hygiene and tests before moving code. It is acceptable for tests to fail initially if each failure is converted into a documented gap with an owner and verification command.

Next:

- Create `docs/GAP_REGISTER.md`.
- Add `pyproject.toml`, `.gitignore`, `CONTRIBUTING.md`, and pytest config.
- Add characterization tests around existing Bronze/Silver/Gold logic.
- Run tests and assign gaps before migrating code to `src/railway_lakehouse`.

## 2026-06-21 - Repo Hygiene, Tests, And Src Migration

Status: done for repo hygiene and initial migration; fixture E2E remains open.

Research:

- Required coursework research log: `.planning/coursework/research/bigdata/course-project-organization.md`.
- External provider routed through `research-orchestrator`: Context7 for pytest configuration, Python packaging, and GitHub repo hygiene.

Files changed:

- `pyproject.toml`
- `.gitignore`
- `CONTRIBUTING.md`
- `WIRING.md`
- `README.md`
- `TASK.md`
- `AGENTS.md`
- `docs/GAP_REGISTER.md`
- `docs/CODEMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/WORKSTREAMS.md`
- `docs/VERIFICATION.md`
- `docs/PIPELINE.md`
- `docs/NEXT_SESSION_HANDOFF.md`
- `src/railway_lakehouse/**`
- `tests/**`
- `output/project-organization/*.md`
- `.planning/.continue-here.md`
- `.planning/HANDOFF.json`

Findings:

- The project is now installable as `railway-lakehouse` with one source root: `src/railway_lakehouse`.
- Current unit tests characterize Bronze helper/discovery behavior, Silver stats/news behavior, and Gold matrix/Parquet behavior.
- `src/railway_lakehouse/pipeline.py` imports successfully, but Bronze reads remain explicit stubs tracked by GAP-004.
- KSH, Statistik Austria, UIC, and historical GDELT modules are co-located with Bronze sources, but scheduling remains GAP-005.
- No live collectors, MinIO, Ollama, Spark, or real data runs were launched.
- The first install attempt failed with `[Errno 28] No space left on device`; disposable pip cache was purged and install was rerun with `--no-cache-dir`.
- S3 dependency pins were tightened after resolver warnings, and `python -m pip check` later reported no broken requirements.

Evidence:

- `python -m pip install --no-cache-dir -e ".[test]"` passed.
- `python -m pytest -q -m unit` passed: 15 passed, 1 deselected.
- `python -m pytest -q` passed: 15 passed, 1 xfailed.
- Expected failure: `tests/test_pipeline_gaps.py::test_pipeline_storage_read_stubs_are_not_wired`, mapped to GAP-004.
- `python -c "import railway_lakehouse; import railway_lakehouse.pipeline; import railway_lakehouse.bronze.lander; import railway_lakehouse.silver.stats.merge; import railway_lakehouse.gold.build; print('src package imports ok')"` passed.
- `python -m pip check` passed.

Next:

- Implement GAP-004 as a deterministic fixture E2E before live collectors.
- Add integration tests with local fixtures and mocked Ollama output.
- Keep live MinIO/Ollama/Spark checks opt-in until fixture evidence exists.

## 2026-06-21 - Parser Inventory And Bounded Live Check

Status: done for parser documentation and bounded live evidence; parser fixes remain open.

Research:

- Required coursework research log: `.planning/coursework/research/bigdata/course-project-organization.md`.
- External providers routed through `research-orchestrator`: Tavily, Firecrawl, and Context7.
- Official references covered Eurostat API/catalogue docs, World Bank Indicators API docs, GDELT DOC/data docs, Statistics Austria open data, KSH STADAT, UIC RAILISA/statistics, feedparser, and Spark Parquet docs.

Files changed:

- `docs/PARSER_WORK_LOG.md`
- `docs/INDEX.md`
- `docs/PROGRESS_LOG.md`
- `output/evidence/parser-live-check-2026-06-21/manifest.json`
- `output/evidence/parser-live-check-2026-06-21/bronze/**`

Findings:

- A bounded live parser check was run without starting the scheduler, long historical backfill, MinIO, Ollama, or Spark.
- RSS landed two real feed artifacts: Telex and Index.
- KSH landed one real STADAT XLSX artifact: `ksh_rail_freight`.
- Eurostat landed the real catalogue TOC, but dataset fetches failed because discovered codes included quotes such as `"enpe_rail"`, causing 404 responses.
- World Bank landed the real indicator catalogue, but the first discovered indicator series returned an API error payload, so indicator discovery/validation needs tightening.
- GDELT recent and GDELT history probes returned HTTP 429.
- Statistik Austria configured seed returned HTTP 200 with 0 bytes.
- UIC configured seed returned HTTP 404.

Evidence:

- Manifest: `output/evidence/parser-live-check-2026-06-21/manifest.json`.
- Raw evidence root: `output/evidence/parser-live-check-2026-06-21/bronze/`.
- Artifact count after bounded probe: 6 raw artifacts plus sidecar metadata.

Next:

- Use `docs/PARSER_WORK_LOG.md` as the classmate split point for parser ownership.
- Start Wave 1 parser fixes: Eurostat code cleanup, World Bank indicator validation, GDELT 429 handling, RSS feed health, KSH seed confirmation, Statistik Austria seed refresh, and UIC URL/access refresh.
- Convert the ad hoc bounded live check into a documented repo command before claiming GitHub-ready live parser UX.

## 2026-06-21 - Bronze Local Live Check Command

Status: done for bounded local RSS/KSH Bronze command; wider live sources remain documented gaps.

Changed:

- `.planning/coursework/research/bigdata/live-check-command.md`
- `src/railway_lakehouse/bronze/live_check.py`
- `tests/test_bronze_live_check.py`
- `docs/PARSER_WORK_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `output/evidence/live-bronze/manifest.json`

Generated local evidence:

- `output/evidence/live-bronze/bronze/**` during the recorded command run; raw files remain local/ignored and are summarized by the committed manifest.

Findings:

- `python -m railway_lakehouse.bronze.live_check` writes local raw Bronze files and `.meta.json` sidecars without MinIO.
- The command is bounded by `--max-artifacts`, interpreted as the maximum URL attempts/artifacts per selected source.
- Reruns under an output root that already contains evidence write a run-specific subdirectory instead of overwriting earlier artifacts.
- The RSS/KSH live run landed 8 raw artifacts: 5 RSS feed XML files and 3 KSH XLSX files.
- The live manifest records source statuses, artifact paths, byte counts, HTTP statuses, failures, and run timestamp.
- Scheduler, MinIO, Ollama, Spark, and long historical GDELT backfill were not launched.

Evidence:

- `python -m pytest -q tests\test_bronze_live_check.py` passed: 3 passed.
- `python -m pytest -q` passed: 18 passed, 1 xfailed.
- `python -m railway_lakehouse.bronze.live_check --sources rss,ksh --out output/evidence/live-bronze --max-artifacts 5` passed and printed `artifact_count=8`, `byte_count=264670`, RSS `passed`, KSH `passed`.
- Manifest: `output/evidence/live-bronze/manifest.json`.
- Local raw evidence root generated by that run: `output/evidence/live-bronze/bronze/`.

Next:

- Add mocked HTTP tests inside source-owner work for RSS feed drift and KSH stale table handling.
- Decide whether to extend `live_check` to Eurostat after the quoted-code dataset URL bug is fixed.

## 2026-06-22 - PR Review And Parser Merges

Status: done.

Changed:

- `.planning/coursework/research/bigdata/pr-review-merge-2026-06-22.md`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/bronze/sources/eurostat.py`
- `src/railway_lakehouse/bronze/sources/worldbank.py`
- `tests/test_bronze_live_check.py`
- `tests/test_bronze_characterization.py`
- `docs/PARSER_WORK_LOG.md`
- `docs/GAP_REGISTER.md`

Findings:

- Reviewed all open GitHub PRs one by one: PR #1, PR #2, and PR #3.
- PR #1 needed fixes before merge: live-check preflight validation, rerun-safe output paths, nonzero failure exit code, additional collector tests, and clearer raw-evidence docs.
- PR #2 needed documentation reconciliation after PR #1 and broader quoted Eurostat code test coverage.
- PR #3 needed conflict resolution after PR #2 and final verification of the World Bank allowlist and API error-payload handling.
- All PRs were merged and the open PR list is empty.

Evidence:

- PR #1 merged at `226df6fb8e7a8482c8046bba3f499662e2a2ca13`.
- PR #2 merged at `4f0f17e337a25a7cd646203848e5f480e05a38d3`.
- PR #3 merged at `20c86e5521e26ff8ff978f4bc471ab9e9ce6f476`.
- `python -m pytest -q` passed after all merges: 29 passed, 1 xfailed.
- `python -m compileall .` passed after all merges.
- Bounded Eurostat direct probe returned HTTP 200 and 552 bytes for `enpe_rail_go`.
- Bounded World Bank direct probe accepted `IS.RRS.TOTL.KM`, `IS.RRS.GOOD.MT.K6`, and `IS.RRS.PASG.KM`; rejected the `BM.GSR.TRAN.CD` error envelope.

Next:

- GAP-004 remains the expected xfail until Bronze storage reads are wired in `src/railway_lakehouse/pipeline.py`.

## 2026-06-22 - Dataset Readiness Estimate

Status: done for planning/status answer; no source code changed.

Changed:

- `.planning/coursework/research/bigdata/dataset-readiness-2026-06-22.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:

- A first useful dataset does not need every parser; the fastest path is to use already proven Bronze sources: RSS, KSH, Eurostat, and World Bank.
- All-parser Bronze readiness still depends on GDELT 429 handling, Statistik Austria source refresh, UIC resource/access resolution, and historical GDELT safe bounds.
- Analysis-ready dataset output remains blocked by GAP-004, GAP-006, and GAP-007.
- Spark evidence remains blocked by GAP-009.
- `docs/PARSER_WORK_LOG.md` now records target milestones for MVP Bronze, first Gold Parquet, Spark evidence, and full parser hardening.

Evidence:

- Local status review used `docs/PARSER_WORK_LOG.md`, `docs/GAP_REGISTER.md`, `docs/TEST_FIRST_INTEGRATION_PLAN.md`, `README.md`, `TASK.md`, and source entrypoints.
- No live collectors or tests were run for this estimate.

Next:

- Prioritize a minimal Gold Parquet dataset from proven sources before waiting for every parser to be perfect.

## 2026-06-22 - KSH STADAT Seed Correction PR

Status: done for KSH Bronze seed correction; scheduler and Silver parsing remain open.

Changed:

- `.planning/coursework/research/bigdata/ksh-stadat-seeds-2026-06-22.md`
- `README.md`
- `WIRING.md`
- `docs/CODEMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/VERIFICATION.md`
- `output/evidence/ksh-live-check-2026-06-22/manifest.json`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/bronze/sources/ksh.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`

Findings:

- The supplied patch did not apply cleanly to current `main` because `docs/PARSER_WORK_LOG.md` and `tests/test_bronze_characterization.py` had newer Eurostat/World Bank context.
- The KSH intent was integrated against the current docs and code: retire non-rail/mislabelled seeds, use six curated STADAT rail or rail-bearing tables, and reject empty or non-XLSX HTTP-200 responses before Bronze landing.
- `src/railway_lakehouse/bronze/run.py` still does not schedule KSH, so GAP-005 remains open.
- KSH Silver XLSX parsing remains Wave 3 work.

Evidence:

- `python -m pytest -q tests\test_bronze_characterization.py` passed: 15 passed.
- `python -m pytest -q tests\test_bronze_live_check.py` passed: 8 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/runtime/ksh-live-check-validation --max-artifacts 6 --timeout-seconds 30` passed with `artifact_count=6`, `byte_count=92509`, KSH `passed`, and 0 failures.
- `python -m pytest -q` passed: 33 passed, 1 xfailed for documented GAP-004.
- `python -m compileall .` passed.
- `python -m json.tool output\evidence\ksh-live-check-2026-06-22\manifest.json` passed.

Next:

- Push the PR branch and run the requested read-only `ship-it:ship-pr` review.
- Keep GAP-005 open until KSH is scheduled through `src/railway_lakehouse/bronze/run.py`.

## 2026-06-22 - PR 4 Review Fixes

Status: done for PR review findings; merge pending push and GitHub green state.

Changed:

- `.planning/coursework/research/bigdata/pr4-review-fixes-2026-06-22.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/PROGRESS_LOG.md`
- `docs/VERIFICATION.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`
- `src/railway_lakehouse/bronze/sources/ksh.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`
- `tests/test_bronze_live_check_integration.py`

Findings:

- Historical `output/evidence/live-bronze/manifest.json` KSH rows came from the old seed set and are now explicitly superseded for current KSH claims.
- Current-code KSH live evidence is committed as `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`.
- KSH response validation now verifies the XLSX ZIP workbook container, not only the `PK` prefix.
- A deterministic integration fixture now exercises KSH live-check manifest, raw Bronze artifact, and metadata writing without network.

Evidence:

- `python -m pytest -q tests\test_bronze_characterization.py tests\test_bronze_live_check.py tests\test_bronze_live_check_integration.py` passed: 24 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/ksh-live-check-2026-06-22-current --max-artifacts 6 --timeout-seconds 30` passed with `artifact_count=6`, `byte_count=92509`, KSH `passed`, and 0 failures.
- `python -m pytest -q -m integration` passed: 1 passed, 33 deselected, 1 xfailed for documented GAP-004.
- `python -m pytest -q` passed: 34 passed, 1 xfailed for documented GAP-004.
- `python -m compileall src tests` passed.
- `python -m json.tool output\evidence\ksh-live-check-2026-06-22-current\manifest.json` passed.

Next:

- Push PR #4, mark it ready when branch checks are green, and merge.
- Keep GAP-005 open until KSH is scheduled through `src/railway_lakehouse/bronze/run.py`.

## 2026-06-22 - KSH STADAT Task Status Docs

Status: done for documentation; no source behavior changed.

Changed:

- `.planning/coursework/research/bigdata/ksh-stadat-doc-status-2026-06-22.md`
- `docs/CODEMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/PROGRESS_LOG.md`
- `docs/WORKSTREAMS.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:

- PR #4 was the `parser/ksh-stadat` task for the Bronze KSH STADAT source.
- The Bronze scope is complete: seeded IDs were checked, stale/mislabelled seeds were retired, mocked HTTP tests exist, and current live-check evidence is committed.
- KSH scheduler wiring remains GAP-005.
- KSH XLSX -> `StatFact` parsing and Silver parser tests remain GAP-006.

Evidence:

- Local status search used `rg` across `README.md`, `TASK.md`, `docs/`, `.planning/`, and `WIRING.md`.
- `git diff --check` passed.

Next:

- Implement KSH scheduler wiring under GAP-005.
- Implement KSH Silver XLSX parser/tests under GAP-006.

## 2026-06-22 - Undone Task Triage

Status: done for planning/status answer; no source behavior changed.

Changed:

- `.planning/coursework/research/bigdata/undone-task-triage-2026-06-22.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:

- The supplied parser list covers the main remaining Bronze parser work, but the course-ready path also needs GAP-004 fixture-backed Bronze reads, GAP-005 scheduler wiring, GAP-006 Silver persistence/parser outputs, GAP-007 Gold storage loading, GAP-009 Spark evidence, and GAP-011 report/presentation outputs.
- `src/railway_lakehouse/bronze/live_check.py` currently supports only RSS and KSH, so bounded live checks for GDELT, Statistik Austria, UIC, Eurostat, and World Bank need additional command support or separately documented probe commands.
- The fastest next path remains a minimal Gold/Spark vertical slice from proven sources: RSS, KSH, Eurostat, and World Bank. GDELT, Statistik Austria, and UIC can harden in parallel without blocking the first dataset.
- Official source review found a likely current Statistik Austria candidate dataset, `OGD_watlas23_WATLAS_23`, and confirmed UIC RAILISA has REST/public-resource surfaces but download access can be subscription-limited. These are source-research findings only until project code lands artifacts and records evidence.

Evidence:

- Local review used the project status docs, parser work log, gap register, live-check command, Bronze source modules, Silver/Gold modules, and Bronze tests.
- External source review used official GDELT, Statistik Austria, and UIC pages.
- No tests, live collectors, Spark jobs, MinIO, or historical backfills were run.

Next:

- Start with GAP-004/minimal GAP-006/GAP-007 to produce first fixture-backed Gold Parquet, while separate parser owners work on GDELT, RSS, Statistik Austria, and UIC.

## 2026-06-22 - GDELT Rate-Limit Handling

Status: done for mocked rate-limit/safety coverage; latest bounded recent GDELT live probe failed without artifacts.

Changed:

- `.planning/coursework/research/bigdata/gdelt-rate-limit-2026-06-22.md`
- `WIRING.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/PROGRESS_LOG.md`
- `docs/VERIFICATION.md`
- `src/railway_lakehouse/bronze/sources/gdelt.py`
- `src/railway_lakehouse/bronze/sources/gdelt_common.py`
- `src/railway_lakehouse/bronze/sources/past_recordings.py`
- `tests/test_bronze_characterization.py`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:

- Prior project evidence showed HTTP 429 for both recent GDELT and historical DOC probes.
- Official GDELT DOC parameter docs cap `MAXRECORDS` at 200; current code had requested 250.
- Recent GDELT ingestion now retries HTTP 429, respects `Retry-After`, and lands only successful raw JSON responses.
- Historical GDELT DOC/GKG collection now shares the same retry helper and has `--dry-run` plus `--max-pages`; CLI default is bounded to one page/file attempt unless an explicit value is supplied.
- A bounded one-day recent GDELT live probe did not land artifacts: HU returned HTTP 429 after configured retry handling, and AT failed with a remote disconnect.
- Decision: recent GDELT is marked not working for live Bronze collection now, but it does not block the Bronze MVP because RSS, KSH, UIC public PDFs, Eurostat, and World Bank have usable bounded evidence.
- GDELT is not a Silver blocker yet because there is no current Bronze GDELT artifact to parse. Start Silver GDELT parsing only after a future bounded probe lands raw ArtList JSON.
- No scheduler, MinIO, Spark job, or long historical backfill was run.

Evidence:

- `python -m pytest -q tests\test_bronze_characterization.py -k "gdelt or past_recordings"` passed: 6 passed, 17 deselected.
- `python -m pytest -q tests\test_bronze_characterization.py` passed: 23 passed.
- Bounded recent GDELT live retry probe wrote `output/evidence/gdelt-live-check-2026-06-22/manifest.json`: `status=failed`, `artifact_count=0`, `byte_count=0`, with failures for HU HTTP 429 and AT `RemoteDisconnected`.
- `python -m pytest -q` passed: 43 passed, 1 xfailed for documented GAP-004.
- `python -m compileall src tests` passed.
- `git diff --check` passed.

Next:

- Keep recent GDELT marked not live-ok and fix it only if time remains or the report specifically needs GDELT news coverage.
- Keep long historical GDELT backfills opt-in only, with an explicit evidence plan.

## 2026-06-22 - UIC Refresh Public Publications

Status: done for `parser/uic-refresh` public-publication Bronze scope; subscribed RAILISA CSV/Excel/API access remains blocked on credentials/subscription.

Changed:

- `.planning/coursework/research/bigdata/uic-refresh-2026-06-22.md`
- `src/railway_lakehouse/bronze/sources/uic.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`
- `output/evidence/uic-live-check-2026-06-22/manifest.json`
- `docs/CODEMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/VERIFICATION.md`
- `WIRING.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:

- The old UIC public XLS seed `https://uic.org/IMG/xls/uic_railway_statistics_synopsis.xls` still returned HTTP 404 in a bounded direct probe.
- Current public UIC RAILISA resource endpoints `https://uic-stats.uic.org/resources/help_resource/?id=12` and `https://uic-stats.uic.org/resources/help_resource/?id=14` returned HTTP 200 PDF bytes.
- RAILISA CSV/Excel download and REST API access is subscription/auth-bound, so the Bronze source now lands only current public free publication PDFs and records that boundary in artifact metadata.
- UIC is still not scheduled by `src/railway_lakehouse/bronze/run.py`, so GAP-005 remains open.
- Decision: UIC public PDF collection is complete for Bronze; extracting facts from those PDFs belongs to Silver parser work.

Evidence:

- Direct probe: `id=12` -> HTTP 200, 591,749 bytes, `application/pdf`; `id=14` -> HTTP 200, 1,517,491 bytes, `application/pdf`; stale XLS seed -> HTTP 404, HTML.
- `python -m pytest -q tests\test_bronze_live_check.py` passed: 9 passed.
- UIC-specific source/live-check tests passed: 4 passed.
- `python -m railway_lakehouse.bronze.live_check --sources uic --out output/evidence/uic-live-check-2026-06-22 --max-artifacts 2 --timeout-seconds 30` passed with `artifact_count=2`, `byte_count=2109240`, UIC `passed`, and 0 failures.
- `python -m compileall .` passed.
- `python -m pytest -q` passed: 43 passed, 1 xfailed for documented GAP-004.

Next:

- Wire UIC into the Bronze scheduler under GAP-005 only after the class wants public PDFs included in scheduled stats runs.
- Start a Silver parser decision for UIC public PDF extraction versus subscribed RAILISA CSV/Excel input.

## 2026-06-22 - PR #5-#7 Review, Fixes, And Merge

Status: done.

Changed:
- `.planning/coursework/research/bigdata/pr5-pr7-review-merge-2026-06-22.md`
- `src/railway_lakehouse/bronze/sources/past_recordings.py`
- `src/railway_lakehouse/bronze/sources/statistik_austria.py`
- `tests/test_gdelt_rate_limit.py`
- `tests/test_bronze_characterization.py`
- `docs/PARSER_WORK_LOG.md`
- merged PR evidence/docs/source/test files from PR #5, PR #6, and PR #7

Findings:
- Open GitHub queue contained PR #5, PR #6, and PR #7; no open GitHub issues were returned.
- PR #5 was reviewed with `ship-it:ship-pr`; PR #6 and PR #7 halted under strict `ship-pr` because fork PRs are out of scope in v1, then received fallback read-only subagent reviews per user instruction.
- Invited `alyonaprikhodko` and `Soomphik` as write collaborators on `pol3et/railway-bigdata`.
- Fixed PR #5 historical GDELT safety default and diff-check failure.
- Fixed PR #6 malformed RSS parser inventory row.
- Fixed PR #7 Statistik Austria validation so non-empty HTML/invalid HTTP-200 responses are not landed as real `.ods` artifacts.
- No clean merge order existed before conflict resolution; PR branches were updated/reconciled so parser docs and tests work together.
- All three PRs were merged and the open PR list is empty.

Evidence:
- PR #5 merged at `53287a11bf8b91160b2f1af36c9c5bb6c50e5792`.
- PR #6 merged at `3fa4c899247a3c0c058f133a3a1e80345d3fe18c`.
- PR #7 merged at `8f69200b151a2989c9f7f5d665e61f6eeb81deb7`.
- Final merged-main `python -m pytest -q` passed: 53 passed, 1 xfailed for documented GAP-004.
- Final merged-main `python -m compileall src tests` passed.
- Final merged-main evidence manifest JSON validation passed for GDELT, UIC, RSS, and Statistik Austria.
- Final merged-main `git diff --check` passed.

Next:
- Keep GAP-004 as the next vertical-slice priority: fixture-backed Bronze storage reads.
- Treat GDELT live collection as optional hardening unless a future bounded probe lands real artifacts.

## 2026-06-22 - Current State And Next Plan

Status: done for planning/status review; no source behavior changed.

Changed:
- `.planning/coursework/research/bigdata/current-state-next-plan-2026-06-22.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- Local `main` is at `2dc5091`, matching `origin/main`; PR #5, PR #6, and PR #7 are present in history.
- The classmate's plan is directionally right: run Silver news, Silver stats, and GAP-004 fixture E2E in parallel; delay Spark until Gold Parquet exists.
- Corrections: World Bank and Eurostat already have primitive Silver readers; Gold pivot/write logic already exists; the missing work is fixture-backed reading, concrete RSS/article records, source-specific `StatFact` fixtures, persistence, and evidence outputs.
- Current blockers remain GAP-004, GAP-006, GAP-007, GAP-009, and GAP-011. GDELT should stay non-blocking because the latest bounded live probe landed no artifacts.

Evidence:
- `python -m pytest -q` passed: 53 passed, 1 xfailed for GAP-004.
- `python -m compileall src tests` passed.
- External source check used Apache Spark's official Parquet documentation for the planned Gold Parquet -> Spark path.
- No live collectors, MinIO, Ollama, Spark jobs, or long historical backfills were run.

Next:
- Split Stage A into three branches: `silver/news-rss-article-records`, `silver/stats-worldbank-eurostat`, and `pipeline/fixture-e2e-gap004`.
- Treat `silver/stats-ksh-xlsx` as the next stats parser after shared `StatFact` conventions are stable.

## 2026-06-22 - Owner Recommendation Follow-Up

Status: done for planning clarification; no source behavior changed.

Findings:
- Highest-priority owner task is `pipeline/fixture-e2e-gap004`: close the strict pipeline xfail with a deterministic no-network Bronze fixture -> Silver -> Gold Parquet path.
- This blocks final Gold/Spark/report evidence, but it does not block classmates from starting isolated Silver parser branches.
- Safe parallel branches are `silver/news-rss-article-records` and `silver/stats-worldbank-eurostat`; both should use fixtures and avoid changing `pipeline.py` until the GAP-004 branch defines the integration contract.

Evidence:
- Local status review used `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, `.planning/coursework/research/bigdata/current-state-next-plan-2026-06-22.md`, and `rg` over docs/source/tests.
- No tests, source edits, live collectors, MinIO, Ollama, Spark jobs, or historical backfills were run for this clarification.

Next:
- User should take `pipeline/fixture-e2e-gap004`.
- Classmates can start RSS news and World Bank/Eurostat stats parser fixture work in parallel.

## 2026-06-22 - GAP-005 Scheduler Decision

Status: done for planning clarification; no source behavior changed.

Changed:
- `.planning/coursework/research/bigdata/gap005-scheduler-decision-2026-06-22.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- GAP-005 should be deferred from the primary owner path. The primary owner should finish GAP-004 first because fixture-backed Bronze -> Silver -> Gold is the course-score bottleneck.
- GAP-005 can be taken by a classmate in parallel as a small Bronze-only PR if it wires KSH, Statistik Austria, and UIC public PDF sources into the stats batch without changing raw landing semantics.
- Historical GDELT must stay out of automatic scheduler runs; long backfill remains opt-in only.
- GAP-005 does not block `silver/news-rss-article-records` or `silver/stats-worldbank-eurostat`.

Evidence:
- Local status review used `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, `src/railway_lakehouse/bronze/run.py`, and local `rg` searches.
- No source code, tests, live collectors, scheduler, MinIO, Ollama, Spark jobs, or historical backfills were run.

Next:
- Keep user focused on `pipeline/fixture-e2e-gap004`.
- Offer GAP-005 to another classmate only if they keep it bounded and mocked-test-only.

## 2026-06-22 - GAP-004 Fixture Pipeline E2E

Status: done.

Changed:
- `.planning/coursework/research/bigdata/pipeline-fixture-e2e-gap004-2026-06-22.md`
- `src/railway_lakehouse/pipeline.py`
- `tests/test_pipeline_gaps.py`
- `tests/fixtures/bronze/**`
- `output/evidence/fixture-e2e/railway_ml.parquet`
- `output/evidence/fixture-e2e/crosswalk_cache.json`
- `docs/GAP_REGISTER.md`
- `docs/VERIFICATION.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- GAP-004 is closed for deterministic fixture-backed Bronze reads: `_read_bronze_eurostat` reads local/S3-style Eurostat TSV artifacts, and `_read_bronze_news` reads local/S3-style JSON article artifacts.
- `railway_lakehouse.pipeline` now accepts `--bronze-root` for no-network fixture runs and skips live Bronze ingestion in that mode.
- The integration test covers Bronze fixture readers plus Bronze -> Silver -> Gold Parquet with mocked Ollama JSON output.
- The recorded CLI evidence run used `--skip-news-extraction` to avoid a live Ollama dependency; therefore the evidence Parquet contains fixture stats only.
- Independent read-only review found one low-risk `--news 0` limit edge case; it was fixed with a regression test.
- This does not prove live MinIO, live collectors, a running Ollama service, Spark, Silver persistence, Gold storage loading, report, or presentation outputs.

Evidence:
- RED before implementation: `python -m pytest -q tests\test_pipeline_gaps.py` failed with `NotImplementedError` from `_read_bronze_eurostat` and `TypeError` because `main()` did not accept argv.
- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 3 passed.
- `python -m pytest -q -m integration` passed: 4 passed, 52 deselected.
- `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction` passed and wrote Gold Parquet plus the crosswalk cache.
- Parquet readback passed: `(4, 3)` with rows `AT/HU` for `2020/2021` and `rail_passengers`.
- `python -m pytest -q` passed: 56 passed.
- `python -m compileall src tests` passed.
- `git diff --check` exited 0.

Next:
- Start minimal GAP-006/GAP-007 persistence work only after deciding the Silver/Gold artifact contract.
- Keep Spark work blocked until the class agrees on the Gold Parquet input path and evidence command.

## 2026-06-22 - Active Silver Branch Gap Mapping

Status: done for documentation; no source behavior changed.

Changed:
- `.planning/coursework/research/bigdata/active-silver-branch-gap-map-2026-06-22.md`
- `docs/GAP_REGISTER.md`
- `docs/WORKSTREAMS.md`
- `docs/WORK_SPLIT.md`
- `docs/NEXT_SESSION_HANDOFF.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- `silver/news-rss-article-records` maps to GAP-006, specifically the Silver News/RSS article-record slice.
- `silver/stats-worldbank-eurostat` maps to GAP-006, specifically the Silver Stats World Bank/Eurostat slice.
- Either branch can contribute to GAP-010 if it records bounded live evidence.
- Neither branch closes GAP-007 unless it also wires Gold loading from persisted Silver outputs and records Gold row/column evidence.

Evidence:
- Local research used `docs/GAP_REGISTER.md`, `docs/WORKSTREAMS.md`, `docs/WORK_SPLIT.md`, `docs/NEXT_SESSION_HANDOFF.md`, and `docs/DATA_CONTRACTS.md`.
- No live collectors, MinIO, Ollama, Spark jobs, or additional dataset runs were used for this mapping.

Next:
- Review teammate PRs against the GAP-006 closure criteria before marking GAP-006 closed.
- Keep GAP-007 separate until Gold can load the persisted Silver outputs.

## 2026-06-22 - Ollama Model Selection

Status: superseded by the later Qwen 3.5 runtime-config decision below; no live Ollama run was launched.

Changed:
- `.planning/coursework/research/bigdata/ollama-model-selection-2026-06-22.md`
- `src/railway_lakehouse/silver/config.py`
- `docs/SILVER_DESIGN.md`
- `docs/ARCHITECTURE.md`
- `docs/WORK_SPLIT.md`
- `docs/NEXT_SESSION_HANDOFF.md`
- `README.md`

Findings:
- The previous `llama3.1:8b` default was a conservative placeholder, not a course-specific model choice.
- Official Ollama metadata checked on 2026-06-22 puts `llama3.1:8b` at 4.9 GB and `qwen3:8b` at 5.2 GB, so `qwen3:8b` keeps the same local-memory class.
- The project default is now `qwen3:8b` because the LLM tasks are multilingual HU/DE/EN label mapping and article extraction.
- `OLLAMA_MODEL=qwen3.5:9b` is documented as the higher-quality local override when the 6.6 GB model fits the machine.
- Gemma remains an explicit experiment or lower-memory alternative, not the default, because current Gemma 4 local models are larger for this validated JSON-extraction use case.
- This does not prove a live Ollama service, model download, or live extraction quality.

Evidence:
- Local research used `src/railway_lakehouse/silver/config.py`, `src/railway_lakehouse/silver/ollama_client.py`, `src/railway_lakehouse/silver/stats/merge.py`, `src/railway_lakehouse/silver/news/extract.py`, `src/railway_lakehouse/pipeline.py`, `docs/SILVER_DESIGN.md`, `docs/ARCHITECTURE.md`, and `docs/WORK_SPLIT.md`.
- External research used official Ollama model pages for `llama3.1:8b`, `qwen3:8b`, `qwen3.5`, `gemma3`, and `gemma4`.
- `python -m pytest -q tests\test_silver_characterization.py tests\test_pipeline_gaps.py` passed: 8 passed.
- `python -m pytest -q` passed: 56 passed.
- `python -m compileall src tests` passed.
- `git diff --check` exited 0.

Next:
- Keep live Ollama checks opt-in and record model pull/run evidence under `output/evidence/` before claiming live extraction quality.

## 2026-06-22 - Qwen 3.5 Ollama Runtime Config

Status: done for MCP-backed model/runtime selection; no live Ollama run was launched.

Changed:
- `.planning/coursework/research/bigdata/qwen35-ollama-runtime-config-2026-06-22.md`
- `.planning/coursework/research/bigdata/ollama-model-selection-2026-06-22.md`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/ollama_client.py`
- `tests/test_silver_characterization.py`
- `docs/SILVER_DESIGN.md`
- `docs/ARCHITECTURE.md`
- `docs/WORK_SPLIT.md`
- `docs/NEXT_SESSION_HANDOFF.md`
- `README.md`

Findings:
- MCP-backed research selected `qwen3.5:9b-q8_0` as the quality-first default and `qwen3.5:9b-q4_K_M` as the lower-memory fallback.
- Ollama lists `qwen3.5:9b-q8_0` as 11 GB and `qwen3.5:9b-q4_K_M` as 6.6 GB, both with 256K context windows.
- Qwen quantization docs list Q8_0, Q5_K_M, and Q4_K_M as common GGUF/llama.cpp presets and warn lower-bit quantization can reduce accuracy.
- Ollama docs support JSON schema through `format`, recommend low temperature for deterministic structured output, and define `think` as a top-level field.
- The Silver Ollama client now uses `/api/chat`, top-level `think: false`, bounded `num_ctx` and `num_predict`, and exact-tag model health checks.
- vLLM stays out of the default runtime because this project needs simple validated local extraction, not high-throughput serving yet.

Evidence:
- MCP providers used: Tavily, Exa, and Firecrawl. Ref was attempted but credit-blocked.
- Sources checked: official Ollama Qwen 3.5 tags/API/structured-output/thinking docs, Qwen quantization and vLLM docs, vLLM structured-output docs, and related Ollama/vLLM issues.
- `python -m pytest -q tests\test_silver_characterization.py` passed: 7 passed.
- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 3 passed.
- `python -m pytest -q` passed: 58 passed.
- `python -m compileall src tests` passed.
- `git diff --check` exited 0.

Next:
- Before claiming live model readiness, run an opt-in evidence command that pulls/runs `qwen3.5:9b-q8_0` or the documented `qwen3.5:9b-q4_K_M` fallback and writes output under `output/evidence/`.

## 2026-06-22 - PR #8 Review Follow-Up

Status: done; actionable automated-review nits applied.

Changed:
- `.planning/coursework/research/bigdata/pr8-review-followup-2026-06-22.md`
- `.planning/coursework/research/bigdata/pipeline-fixture-e2e-gap004-2026-06-22.md`
- `src/railway_lakehouse/pipeline.py`
- `tests/test_pipeline_gaps.py`
- `docs/VERIFICATION.md`
- `docs/PIPELINE.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- PR #8 review had 0 blockers and 0 major findings; actionable minor nits were local to pipeline hardening, evidence reproducibility, and wording.
- Added `--crosswalk-path` so `output/evidence/fixture-e2e/crosswalk_cache.json` is generated by the documented evidence command.
- Bronze path parsing now raises contextual `ValueError`s for malformed paths.
- Missing article bodies no longer reuse the title as body text; fallback article IDs are normalized to forward slashes; flexible dates go through pandas parsing.
- Live MinIO read-back remains unproven and is worded as intended live mode, not completed evidence.

Evidence:
- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 5 passed.
- `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction` passed.
- Parquet readback passed: `(4, 3)` with rows `AT/HU` for `2020/2021` and `rail_passengers`.
- `output/evidence/fixture-e2e/crosswalk_cache.json` contains `Rail passengers total -> rail_passengers`.
- `python -m pytest -q` passed: 60 passed.
- `python -m pytest -q -m integration` passed: 6 passed, 54 deselected.
- `python -m compileall src tests` passed.

Next:
- Run final whitespace/staged checks, push, mark PR #8 ready, and merge.

## 2026-06-23 - PR #9 / PR #10 Rebase Fixes

Status: done; both PR branches pushed and mergeable.

Changed:
- `../Halo-Skills-pr-10/src/railway_lakehouse/silver/stats/merge.py`
- `../Halo-Skills-pr-10/tests/test_silver_characterization.py`
- `../Halo-Skills-pr-10/tests/test_silver_stats_integration.py`
- `../Halo-Skills-pr-9/docs/SILVER_DESIGN.md`
- `../Halo-Skills-pr-9/src/railway_lakehouse/pipeline.py`
- `../Halo-Skills-pr-9/src/railway_lakehouse/silver/news/extract.py`
- `../Halo-Skills-pr-9/src/railway_lakehouse/silver/news/gdelt.py`
- `../Halo-Skills-pr-9/src/railway_lakehouse/silver/news/records.py`
- `../Halo-Skills-pr-9/src/railway_lakehouse/silver/news/rss.py`
- `../Halo-Skills-pr-9/tests/test_pipeline_gaps.py`
- `../Halo-Skills-pr-9/tests/test_silver_news_parsers.py`
- `../Halo-Skills-pr-9/tests/fixtures/bronze/news/rss/hu_telex/ingest_date=2026-06-22/hu_telex.xml`
- `.planning/coursework/research/bigdata/pr9-pr10-rebase-fixes-2026-06-23.md`

Findings:
- PR #10 local commit `a6e3f8272665f8dbddc2a412f1fa69537c5b660a` fixes the World Bank `AUT -> AU` bug by mapping project ISO-3 codes before falling back to World Bank `country.id`.
- PR #9 local commit `d674cbaea034560bd64200cba3a3dd67ff03910c` completes the news parser slice by adding stable article IDs, a generic `ArticleRecord` extraction bridge, RSS full-content preference, and RSS XML fixture wiring into `_read_bronze_news()`.
- PR #9's rebase moved news parser tests into `tests/test_silver_news_parsers.py`, avoiding conflict with PR #10's stats characterization tests.
- Both branches are locally rebased on `origin/main` `4e7a1e6da71abe0da0f9453839cdcf3bc0da30cf`.
- Initial remote update was blocked from `cul8err`, but switching GitHub CLI to `pol3et` allowed the push. The active GitHub CLI account was switched back to `cul8err` afterward.

Evidence:
- PR #10 targeted tests passed: 3 passed.
- PR #10 full suite passed: 66 passed.
- PR #10 `python -m compileall -q src tests` passed and `git diff --check origin/main...HEAD` exited 0.
- PR #9 focused parser/pipeline tests first failed for the intended gaps, then passed: 8 passed.
- PR #9 full suite passed: 68 passed.
- PR #9 `python -m compileall -q src tests` passed and `git diff --check origin/main...HEAD` exited 0.
- PR #10 pushed to `origin/silver/stats-worldbank-eurostat`; remote head now matches `a6e3f8272665f8dbddc2a412f1fa69537c5b660a`.
- PR #9 pushed with `--force-with-lease` to `origin/silver/news-parsers`; remote head now matches `d674cbaea034560bd64200cba3a3dd67ff03910c`.
- GitHub reports PR #10 as `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`.
- GitHub reports PR #9 as `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`.

Next:
- Merge PR #10 and PR #9 when ready, watching normal repository checks if branch protection requires them.

## 2026-06-23 - Main Sync And Documentation Refresh For PR #9 / PR #10

Status: done; `main` pushed and PR #9 / PR #10 are marked merged by GitHub.

Changed:
- `README.md`
- `docs/CODEMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/NEXT_SESSION_HANDOFF.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/PROGRESS_LOG.md`
- `docs/VERIFICATION.md`
- `docs/WORK_SPLIT.md`
- `docs/WORKSTREAMS.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `.planning/coursework/research/bigdata/main-doc-sync-pr9-pr10-2026-06-23.md`

Findings:
- Local `main` now contains merged PR #10 (`silver/stats-worldbank-eurostat`) and PR #9 (`silver/news-parsers`).
- Docs now track the merged state: Silver Stats World Bank/Eurostat fixture parsing is done, Silver News RSS/GDELT article-record parsing is done, and remaining GAP-006 work is narrowed to KSH XLSX, Statistik Austria `.ods`, UIC PDF/subscribed export parsing, and persisted Silver news output/extraction-failure accounting.
- GAP-007 remains open because Gold still needs to load persisted Silver outputs and record Gold evidence.
- Remote `origin/main` now matches local `main` at `09bb9df3d75b7049d11bc051565bf1c15c1b32b7`; GitHub reports PR #9 and PR #10 as `MERGED`.
- No live MinIO, Ollama, Spark, report, or presentation evidence was generated in this docs sync.

Evidence:
- `python -m pytest -q` passed: 74 passed.
- `python -m compileall -q src tests` passed.
- `git diff --check` exited 0.

Next:
- Continue with remaining GAP-006 parsers/persistence or GAP-007 Gold loading from persisted Silver outputs.

## 2026-06-23 - MinIO Local Lakehouse Storage Smoke

Status: done for `infra/minio-storage`; GAP-010 remains in progress for full persisted Bronze->Silver->Gold through MinIO.

Changed:
- Added `.env.example` with local S3/MinIO defaults aligned with Bronze and Silver config.
- Added `docker-compose.yml` for MinIO plus bucket bootstrap for `bronze`, `silver`, and `gold`.
- Added `scripts/minio_smoke.py` to verify a bounded `s3fs` write/read/delete round-trip.
- Added `tests/test_infra_minio.py` as a deterministic guard that does not require Docker.
- Added README instructions for the local MinIO lakehouse path.
- Recorded smoke evidence at `output/evidence/minio-smoke/manifest.json`.

Evidence:
- `python -m pytest -q tests/test_infra_minio.py` passed: 4 passed.
- `python -m pytest -q` passed: 87 passed.
- `docker compose up -d` started `railway-minio`.
- `python scripts/minio_smoke.py` passed.
- `output/evidence/minio-smoke/manifest.json` recorded `status=passed`, `roundtrip_ok=true`, buckets `bronze`, `silver`, and `gold`, `bytes_written=32`, and `bytes_read=32`.

Boundary:
- This verifies local MinIO object storage for `infra/minio-storage`.
- It does not claim full persisted Bronze->Silver->Gold through MinIO; that remains for `silver/persist-outputs` and `gold/load-from-silver`.

Next:
- Continue with persisted Silver outputs and Gold loading from persisted storage.

## 2026-06-23 - All PR Ship-PR Review

Status: done for read-only review; no GitHub comments posted and no PR branches changed.

Changed:
- `.ship/pr/8/report.md`
- `.ship/pr/8/mode.json`
- `.ship/pr/8/sources.json`
- `.ship/pr/11/report.md`
- `.ship/pr/11/mode.json`
- `.ship/pr/11/sources.json`
- `.ship/pr/12/report.md`
- `.ship/pr/12/mode.json`
- `.ship/pr/12/sources.json`
- `.planning/coursework/research/bigdata/all-pr-ship-pr-review-2026-06-23.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- User corrected the review scope to no Linear. Final intent assessment used only repo-local evidence: PR metadata/body, docs, tests, existing ship-pr reports, and command output.
- PR #8 now has a local ship-pr report and passes review: GAP-004 fixture-backed Bronze reads are correctly scoped and verified.
- PR #11 fails review. Blocking issue: the new path test fails on Windows. Major issues: same-day Silver reruns overwrite despite "accumulate history" wording, news extraction failures are not persisted/accounted for, MinIO/S3 wording is not implemented by the local `Path` writer, and empty news Parquet physical types are all `double`.
- PR #12 fails review. The live Bronze-to-Gold path is reproducible and tests pass, but evidence/docs overclaim or under-specify the result: Gold output is only `rail_network_length_km`, counts generation is undocumented, the raw Bronze root is ignored/untracked although the pipeline command depends on it, and roadmap/README wording conflicts about live Silver/Gold evidence.
- Cross-repo PRs #2, #3, #6, and #7 hit the `ship-pr` v1 same-repo halt rule.

Evidence:
- PR #11: targeted persistence tests failed with 1 failed, 5 passed; full suite failed with 1 failed, 79 passed; integration marker suite passed with 9 passed, 71 deselected; compileall and diff-check passed.
- PR #12: focused tests passed with 30 passed; full suite passed with 77 passed; integration marker suite passed with 9 passed, 68 deselected; compileall and diff-check passed; temp live reproduction landed 4 Bronze artifacts / 14,996,995 bytes and regenerated a 2,139 x 3 Gold Parquet with AT/HU present.
- PR #8: pipeline tests passed with 5 passed; full suite passed with 60 passed; compileall and diff-check passed.
- GitHub reported no submitted reviews, no review threads, and no status checks for PR #8, #11, or #12.

Next:
- Fix PR #11 before merge: Windows path test, same-day rerun contract, news failure accounting, local-vs-MinIO docs, and empty Parquet schema types.
- Fix PR #12 before marking tasks done: document/generate counts, make the raw Bronze reproduction path explicit, clarify World Bank-only Gold feature coverage, and reconcile roadmap/README claims.

## 2026-06-23 - Open PR Fix, Dashboard Rebase, And Merge

Status: done; all open PRs merged.

Changed:
- PR #11 branch `silver/persist-outputs`
- PR #12 branch `bronze/local-stats-landing`
- `.planning/coursework/research/bigdata/all-pr-ship-pr-review-2026-06-23.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- No Linear context was used for the final fix/merge work.
- PR #11 implemented local Silver Parquet persistence but needed Windows-safe path tests, explicit empty-file Parquet schemas, narrower local-only persistence docs, and dashboard sync.
- PR #12 implemented bounded local Eurostat/World Bank Bronze landing and first real stats-only Gold evidence, but needed reproducible counts generation, clean-checkout raw Bronze instructions, World Bank-only Gold wording, and dashboard sync.
- Main had new dashboard rules; both PR branches were rebased on updated `origin/main`, and #12 was rebased again after #11 merged.
- GitHub reports no open PRs after merging #11 and #12.

Evidence:
- PR #11 after fixes: `python -m pytest -q` passed with 80 passed; focused Silver persistence tests passed with 6 passed; compileall and diff-check passed; dashboard reminder check passed.
- PR #12 after rebasing on merged #11: `python -m pytest -q` passed with 83 passed; `python -m pytest -q -m integration` passed with 10 passed, 73 deselected; compileall and diff-check passed; committed evidence JSON validated.
- Bounded temp reproduction for #12 under `output/runtime/pr12-reverify/` landed 4 Eurostat/World Bank artifacts / 14,996,995 bytes and regenerated 2,139 x 3 Gold counts with AT/HU present.
- PR #11 merged at `9489aa737412474ffcc377bec0d48ebb0c916595`.
- PR #12 merged at `4ae2984f5807b87a07fa994c5dfdedfada2638a0`.

Next:
- Continue with GAP-007: wire `gold/run.py` to load persisted Silver and record Gold counts.
- Then move to Spark evidence (GAP-009) and report/presentation evidence.

## 2026-06-23 - PR #13 Rebase, Dashboard Sync, And Merge

Status: done; PR #13 is fixed, rebased, pushed, and merged.

Changed:
- `.ship/pr/13/report.md`
- `.ship/pr/13/mode.json`
- `.ship/pr/13/sources.json`
- `.planning/coursework/research/bigdata/pr13-minio-storage-review-2026-06-23.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- No Linear context was used.
- "Integration blocked" split into two issues: deterministic pytest integration was not blocked and passed locally; live Docker/MinIO smoke was blocked by the local Docker Desktop backend.
- PR #13 adds local MinIO/S3 defaults, Docker Compose MinIO plus bucket bootstrap, a bounded `s3fs` smoke script, deterministic infra guard tests, and committed smoke evidence.
- PR #13 was rebased from stale base `c64bd02` onto current `origin/main`, preserving merged Silver persistence and local stats Gold evidence.
- Fixed `.env` handling so `scripts/minio_smoke.py` loads `.env` before importing Bronze/Silver config constants.
- Updated `docs/index.html`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/VERIFICATION.md`, `README.md`, and roadmap/progress docs so MinIO state matches current main and the dashboard rule.
- Docker Desktop could not start its Linux engine in this shell: `backend.error.json` reports `Access is denied` opening `\\.\pipe\dockerBackendApiServer`, which Docker says usually means another Windows user/session already started Docker Desktop.

Evidence:
- PR #13 rebased branch commit: `3548abbc4379f1535d45e76361b05ad840fa878c`.
- `$env:PYTHONPATH='src'; python -m pytest -q tests\test_infra_minio.py` passed: 4 passed.
- `$env:PYTHONPATH='src'; python -m pytest -q -m integration` passed: 10 passed, 77 deselected.
- `$env:PYTHONPATH='src'; python -m pytest -q` passed: 87 passed.
- `$env:PYTHONPATH='src'; python -m compileall -q src tests` exited 0.
- `git diff --check origin/main...HEAD` exited 0 before push.
- `gh pr checks 13` showed `remind` passed after push.
- GitHub reported PR #13 `MERGEABLE` / `CLEAN` at head `3548abbc4379f1535d45e76361b05ad840fa878c`.
- PR #13 merged at `ad45a4ffc8689da159f67c533fd4eea8d093c082`.
- Post-merge local `main` verification: full suite passed with 87 passed; integration marker suite passed with 10 passed, 77 deselected; compileall exited 0; local `HEAD` equals `origin/main` at `ad45a4ffc8689da159f67c533fd4eea8d093c082`; `gh pr list --state open` returned `[]`.
- Fresh Docker check still failed: `com.docker.service` stayed `Stopped`, `docker info` could not find `//./pipe/dockerDesktopLinuxEngine`, and Docker Desktop's backend error file reports access denied on `\\.\pipe\dockerBackendApiServer`.
- Docker live smoke could not be rerun locally after bounded recovery attempts; no new live MinIO claim was added beyond the committed smoke manifest.

Next:
- Continue with GAP-007 Gold loading from persisted Silver, then Spark evidence.
- Rerun `docker compose up -d` and `python scripts/minio_smoke.py` from a Windows session that owns Docker Desktop if new live MinIO evidence is required.

## 2026-06-24 - Live re-audit, tests, data inventory, and undocumented-gap hunt

Status: done (analysis + dashboard + docs); commit/push of docs.

Changed:
- `docs/index.html` (new "Data inventory · live samples" section + "Open risks" section; refreshed metrics/signals)
- `docs/STATE_AND_ROADMAP.md` (2026-06-24 re-audit update; gap summary GAP-012..030)
- `docs/GAP_REGISTER.md` (19 new gaps GAP-012..030; GAP-010 live note; 8 new test-mapping rows)
- `docs/TASKS.md` (gold/first-real-result + infra/minio-storage notes; new-gaps section)
- `.planning/coursework/research/bigdata/state-reaudit-tests-inventory-2026-06-23.md` (research log)
- `output/evidence/inventory-live-2026-06-23/` (live WB Bronze, Gold parquet, counts, Silver parquet, inventory_samples.json)
- `output/evidence/minio-smoke/manifest.json` (live smoke rerun)

Findings:
- All 8 load-bearing claims independently confirmed by an adversarial workflow. Full deterministic suite: 87 passed (77 unit + 10 integration) on Python 3.14.0 / pandas 3.0.3 / pyarrow 24.0.0. `-m live`/`-m spark` select 0 (no such pytest tests).
- Docker recovered: the prior session could not start the Linux engine; this session `docker compose up -d` + `scripts/minio_smoke.py` passed a live 32 B s3fs round-trip (createbuckets bootstrapped bronze/silver/gold). First live MinIO evidence.
- Live World Bank Bronze->Silver->Gold reproduced: Gold 2,968 rows x 4 cols [geo, year, rail_freight_tonne_km, rail_network_length_km], 151 geos, 1995-2021, AT/HU 27 rows each (richer than the committed 2,139x3). Eurostat flaked live (transient RemoteDisconnected).
- Silver StatFact (35,112 rows) persisted + reloaded identically; uploaded to the MinIO silver bucket as a manual demo.
- Ollama not installed: the (fully coded) NewsFeature LLM extractor has never run live; only mocked in tests.
- 19 undocumented gaps found + verified (GAP-012..030). High: GAP-012 (documented regen recipe builds empty Gold). Medium incl. GAP-013 (live MinIO drops World Bank), GAP-015 (units never normalized), GAP-016 (non-deterministic Gold news schema), GAP-017 (pyspark->4.x), GAP-019 (in-memory scheduler), GAP-020 (s3 read-back untested).

Evidence:
- `python -m pytest -q` -> 87 passed; `-m unit` 77, `-m integration` 10; `compileall -q src tests` ok.
- `docker compose up -d` -> railway-minio up 9000/9001; `python scripts/minio_smoke.py` -> roundtrip_ok=true (output/evidence/minio-smoke/manifest.json).
- `bronze.live_check --sources eurostat,worldbank` -> WB 3 artifacts ~17MB; Eurostat failed (RemoteDisconnected).
- `pipeline --bronze-root output/evidence/inventory-live-2026-06-23/bronze --skip-news-extraction --news 0 --counts-out …/counts.json` -> 2,968x4 (output/evidence/inventory-live-2026-06-23/counts.json).
- Workflows: railway-state-audit (21 agents), undocumented-gap-hunt (38 candidates -> 19 gaps; resumed after a mid-run session-limit failure).

Next:
- Fix GAP-012 (regen recipe) and GAP-013 (live MinIO World Bank) before relying on the live path.
- Then GAP-007 (Gold reads persisted Silver), GAP-009 Spark (Spark 4.1 stack + JDK 17/21 per GAP-017), report.
- Live MinIO stack left up; `docker compose down` to stop.

## 2026-06-24 - GAP-012 Regen Recipe Guard

Status: done.

Changed:
- `src/railway_lakehouse/pipeline.py`
- `tests/test_pipeline_gaps.py`
- `docs/VERIFICATION.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/gap-012-bronze-gold-regen-recipe.md`
- `.planning/coursework/plans/bigdata/gap-012-bronze-gold-regen-recipe.md`

Findings:
- Red-state reproduction in `output/runtime/gap-012-red/` confirmed the clean-checkout trap: a root containing only `manifest.json` made `live_check` write raw Bronze under `<out>/<run_id>/bronze`, while the old hardcoded `<out>/bronze` pipeline path exited 0 and wrote `rows=0`, `columns=0`.
- GAP-012 fix keeps raw Bronze landing semantics unchanged and preserves the existing run-id nesting contract.
- The documented recipe now uses fresh `output/evidence/local-stats-bronze-regen`, and `pipeline.run_pipeline()` validates local `--bronze-root` before any Gold output write.
- Missing local Bronze roots now raise `FileNotFoundError`; existing local roots that yield zero stats frames and zero news articles raise `ValueError`.

Evidence:
- RED: old scratch pipeline command against `output/runtime/gap-012-red/local-stats-bronze/bronze` exited 0 and wrote `output/runtime/gap-012-red/empty-gold/counts.json` with `rows=0`, `columns=0`.
- `python -m railway_lakehouse.bronze.live_check --sources eurostat,worldbank --out output/evidence/local-stats-bronze-regen --max-artifacts 1 --timeout-seconds 60` passed: 4 artifacts, 14,996,995 bytes.
- `python -m railway_lakehouse.pipeline --bronze-root output/evidence/local-stats-bronze-regen/bronze --skip-news-extraction --news 0 --out output/evidence/local-stats-bronze-regen/railway_ml.parquet --crosswalk-path output/evidence/local-stats-bronze-regen/crosswalk_cache.json --counts-out output/evidence/local-stats-bronze-regen/counts.json` passed: 2,139 rows x 3 columns, `rail_network_length_km`, AT/HU present, 1995-2021.
- Negative check `python -m railway_lakehouse.pipeline --bronze-root output/evidence/does-not-exist/bronze --skip-news-extraction --news 0 --out output/runtime/gap-012-negative/empty.parquet` exited non-zero with a path-specific `FileNotFoundError`; the output parquet was not created.
- `python -m pytest -q -m integration` passed: 13 passed, 77 deselected.
- `python -m pytest -q -m unit` passed: 77 passed, 13 deselected.
- `python -m pytest -q` passed: 90 passed.
- `python -m pytest -q tests/test_bronze_live_check.py::test_run_live_check_uses_run_subdirectory_when_output_already_has_evidence` passed: 1 passed.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.

Next:
- Open the GAP-012 PR and proceed with the remaining Wave 1 items after review/merge: GAP-017/018 Spark stack pins and GAP-020 s3 read-back tests.
## 2026-06-24 - GAP-020 s3 Bronze Read-Back Tests

Status: done

Changed:
- `src/railway_lakehouse/pipeline.py`
- `tests/test_pipeline_s3_readback.py`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/gap-020-s3-readback-tests-2026-06-24.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- The s3/non-Path Bronze read-back branch is now covered deterministically with an injected fsspec `memory://` filesystem: glob/filtering, no-backend `ValueError`, gzip TSV read-back, TSV local/s3 parity, news article parity, and UTF-8 text parity.
- The old s3 `_read_text` text-mode branch was reproduced as a RED failure with a UTF-8 payload containing accents and typographic quotes; the failure was `UnicodeDecodeError` on byte `0x98` through a cp1251 text-mode wrapper.
- `_read_text` now opens s3 objects in binary mode and decodes UTF-8 explicitly. No numeric stats are rewritten, no LLM is used, and `tests/fixtures/bronze/**` stayed read-only.
- No Docker, MinIO, Ollama, Spark, live collectors, or network data collection was run for this gap.

Evidence:
- `python -m pytest -q tests/test_pipeline_s3_readback.py` before fix -> failed as expected: 5 passed, 1 failed.
- `python -m pytest -q -m unit tests/test_pipeline_s3_readback.py` -> 6 passed.
- `python -m pytest -q -m unit` -> 83 passed, 10 deselected.
- `python -m pytest -q` -> 93 passed.
- `python -m compileall -q src tests` -> passed.

Next:
- Open the GAP-020 PR; remaining active-path gaps include GAP-012, GAP-013, GAP-017/018, Spark evidence, persisted-Silver Gold loading, and report work.

## 2026-06-24 - GAP-017 Spark 4.1 Stack Pin

Status: done for dependency/docs/test guard; no live Spark run was executed.

Changed:
- `pyproject.toml`
- `tests/test_spark_stack_pins.py`
- `README.md`
- `.env.example`
- `docs/STATE_AND_ROADMAP.md`
- `docs/index.html`
- `docs/TASKS.md`
- `docs/GAP_REGISTER.md`
- `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`

Findings:
- Live environment re-confirmed: Python 3.14.0, pandas 3.0.3, pyarrow 24.0.0, numpy 2.4.4; Java is 1.8.0_491 and `JAVA_HOME` is unset.
- Stack A is not viable for this repo's Python 3.14/pandas 3.0/pyarrow 24 runtime, so GAP-017 adopted the Spark 4.1 stack: `pyspark==4.1.*`, `delta-spark==4.1.*`, S3A Maven packages `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6`, and JDK 17/21.
- `hadoop-aws` is a JVM/Maven connector, not a PyPI package; the Python dry-run resolves PySpark/Delta and docs record the S3A Maven/AWS SDK v2 requirement for GAP-009.

Evidence:
- `python --version` -> Python 3.14.0.
- `python -c "import pandas,pyarrow,numpy;print(pandas.__version__,pyarrow.__version__,numpy.__version__)"` -> `3.0.3 24.0.0 2.4.4`.
- `java -version` -> `1.8.0_491`; `JAVA_HOME` unset.
- `python -m pip install --dry-run ".[spark]"` -> would install `pyspark-4.1.2`, `delta-spark-4.1.0`, `py4j-0.10.9.9`.
- `python -m pytest -q tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pytest -q -m unit tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pytest -q` -> 88 passed.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed (line-ending warnings only).

Next:
- GAP-009 `spark/evidence-job`: install JDK 17 or 21, set `JAVA_HOME`, then build and run the bounded Spark evidence job. Do not claim a live Spark run until its output is under `output/evidence/`.

## 2026-06-24 - GAP-017 PR Review Fix: Maven S3A Split

Status: done for request_changes follow-up; no live Spark run was executed.

Changed:
- `pyproject.toml`
- `src/railway_lakehouse/spark_config.py`
- `tests/test_spark_stack_pins.py`
- `README.md`
- `.env.example`
- `docs/GAP_TASKS.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/index.html`
- `docs/TASKS.md`
- `docs/GAP_REGISTER.md`
- `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`

Findings:
- Review P1 was valid: `hadoop-aws` is not a PyPI package, so it was removed from `[spark]`; the extra now contains only `pyspark==4.1.*` and `delta-spark==4.1.*`.
- S3A is now recorded where GAP-009 can consume it: `railway_lakehouse.spark_config.SPARK_S3A_PACKAGES=org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6`, with matching README/.env/docs text.
- Review P2 was valid: `docs/GAP_TASKS.md` still had Stack-A GAP-009/GAP-017 task text; those contracts now point to Spark 4.1, Delta 4.1, JDK 17/21, and Maven S3A packages.

Evidence:
- Context7 Hadoop docs plus Maven Central POMs were recorded in `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`; Ref search was attempted but unavailable due credits.
- `python -m pytest -q tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pytest -q -m unit tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pip install --dry-run ".[spark]"` -> would install `pyspark-4.1.2`, `delta-spark-4.1.0`, `py4j-0.10.9.9`; no `hadoop-aws` pip dependency.
- `python -m pytest -q` -> 88 passed.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed (line-ending warnings only).

Next:
- Keep PR #15 on `impl/gap-017` mergeable; GAP-009 can consume `SPARK_S3A_PACKAGES` when implementing the Spark evidence job.

## 2026-06-24 - GAP-009 Spark Evidence Job

Status: done

Changed:
- `src/railway_lakehouse/spark_jobs/__init__.py`, `src/railway_lakehouse/spark_jobs/coverage.py`
- `tests/test_spark_coverage.py`, `tests/test_spark_stack_pins.py`
- `output/evidence/spark/manifest.json`, `output/evidence/spark/coverage_by_geo_year/`
- `README.md`, `docs/VERIFICATION.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`, `docs/GAP_REGISTER.md`, `docs/index.html`

Findings:
- `railway_lakehouse.spark_jobs.coverage` reads a real Gold Parquet with a SparkSession, computes a per-(geo,year) coverage aggregation, and writes a Spark output directory + an evidence manifest. Spark imports are deferred so the module imports without PySpark (CI-safe).
- Live run used the real inventory-live Gold (2,968×4); manifest records Spark 4.1.2, JDK 21.0.11, output 2,968×5, one part-file + `_SUCCESS`, duration, UTC timestamps, `status=passed`.
- Missing input raises `FileNotFoundError`; 0-row input raises `ValueError` (no silent-empty output).
- The spark write-path test skips cleanly when `HADOOP_HOME`/winutils is absent (mirrors `importorskip`).

Evidence:
- `python -m pytest -q -m "not spark"` -> 104 passed, 2 deselected (CI-safe; spark file `importorskip`-skips without PySpark).
- `python -m pytest -q -m spark` -> 2 passed (with PySpark 4.1.2 + JDK 21 + `HADOOP_HOME`).
- `python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/inventory-live-2026-06-23/railway_ml.parquet --out output/evidence/spark/` -> `status=passed`; manifest at `output/evidence/spark/manifest.json`.
- Orchestrator Contract-B re-run independently reproduced 2,968×4 → 2,968×5 (`output/evidence/orch/contract-b/`).

Next:
- GAP-011 drafts the report from `output/evidence/spark/manifest.json` + the real Gold counts.

## 2026-06-24 - GAP-007 Gold Load From Persisted Silver

Status: done

Changed:
- `src/railway_lakehouse/gold/run.py`
- `src/railway_lakehouse/gold/build.py`
- `src/railway_lakehouse/pipeline.py`
- `tests/test_gold_load_from_silver.py`
- `docs/GAP_REGISTER.md`
- `docs/CODEMAP.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/TASKS.md`
- `docs/index.html`
- `pyproject.toml`
- `.planning/coursework/plans/bigdata/gap-007-gold-load-from-silver.md`
- `.planning/coursework/research/bigdata/gap-007-gold-load-from-silver.md`

Findings:
- `gold.run` now reads local persisted Silver Parquet through `persist.load_stats/load_news`, converts loaded news to dict rows, writes Gold Parquet, and records counts through the shared `gold.build.write_gold_counts`.
- The counts writer was moved out of `pipeline.py` without changing the existing GAP-010 counts shape; the pipeline counts integration guard still passes.
- Pytest now adds local `src/` during test collection, so `python -m pytest ...` verifies the checkout under test even when another editable worktree is installed globally.
- The CLI path is deterministic and local: no network, MinIO, Ollama, Spark, or `coursework/` data was used.

Evidence:
- RED: `python -m pytest -q tests/test_gold_load_from_silver.py` failed with the old `main()` signature before implementation.
- `python -m pytest -q tests/test_gold_load_from_silver.py tests/test_pipeline_gaps.py::test_pipeline_fixture_e2e_reads_bronze_and_writes_gold` -> 2 passed.
- `python -m pytest -q -m unit` -> 89 passed, 14 deselected.
- `python -m pytest -q -m integration` -> 14 passed, 89 deselected.
- `python -m pytest -q` -> 103 passed.
- `python -m compileall -q src tests` -> passed.
- `python -m railway_lakehouse.gold.run --silver-root output/runtime/gap-007-cli-smoke/silver --out output/runtime/gap-007-cli-smoke/gold/railway_ml.parquet --counts-out output/runtime/gap-007-cli-smoke/gold/counts.json --ingest-date 2026-06-23` -> Gold 4 rows x 4 columns; counts include AT/HU, years 2020-2021, and `rail_passenger_km`.

Next:
- PR #18 is open and mergeable. GAP-009 Spark evidence can now consume the Gold CLI boundary after merge, while full MinIO/Ollama/news E2E remains separate GAP-010/GAP-013 work.

## 2026-06-24 - GAP-011 report and presentation drafts

Status: done for implementation and local verification; PR handoff pending.

Changed:
- `output/report/REPORT.md`
- `output/presentation/PRESENTATION.md`
- `tests/test_report_evidence_links.py`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/VERIFICATION.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/gap-011-report-presentation.md`
- `.planning/coursework/plans/bigdata/gap-011-report-presentation.md`

Findings:
- GAP-009 is already closed in this checkout, so the report's Spark section is
  filled from `output/evidence/spark/manifest.json` instead of leaving the older
  pending placeholder.
- The report and presentation cite committed manifests/counts/samples only, not
  ignored raw Bronze subtrees.
- Known gaps remain explicit: GAP-013 live-MinIO World Bank stats path,
  GAP-023 Eurostat-to-Gold mapping, GAP-006 live Ollama/news and extra parsers,
  and GAP-019 deployable automatic updates.

Evidence:
- RED checker run before deliverables existed: 3 expected failures.
- `python -m pytest -q tests/test_report_evidence_links.py` -> 3 passed.
- Evidence path scan -> `MISSING EVIDENCE PATHS: []`.
- `python -m pytest -q -m "not spark"` -> 107 passed, 2 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q -m spark` -> 1 passed, 1 skipped, 107 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 108 passed, 1 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF warnings only.

Next:
- Commit, push `impl/gap-011`, open the PR against `main`, and confirm GitHub mergeability.

## 2026-06-24 - GAP-011 PR #20 review fixes

Status: done.

Changed:
- `output/report/REPORT.md`
- `output/presentation/PRESENTATION.md`
- `tests/test_report_evidence_links.py`
- `.planning/coursework/research/bigdata/gap-011-report-presentation.md`

Findings:
- Review P2a was valid: the report opening overstated news as part of the
  current reportable dataset. The current Gold is stats-only; news remains
  candidate input pending GAP-006.
- Review P2b was valid: the checker verified headline values only in
  `REPORT.md`, and did not require exact JSON `key=value` tokens in the
  presentation.

Evidence:
- RED: `python -m pytest -q tests/test_report_evidence_links.py` failed after
  extending the checker because both docs lacked the stricter exact tokens.
- GREEN: `python -m pytest -q tests/test_report_evidence_links.py` -> 3 passed.
- `python -m pytest -q -m unit` -> 93 passed, 16 deselected.

Next:
- Commit, push `impl/gap-011`, and confirm PR #20 remains mergeable.
## 2026-06-24 - GAP-013 live World Bank wiring

Status: closed (Codex implemented; orchestrator verified + shipped)

Changed:
- `src/railway_lakehouse/pipeline.py` — `_read_bronze_worldbank`, `_read_bytes`, live Eurostat+World Bank frame combination + zero-WB WARN (local `bronze_root` branch unchanged)
- `tests/test_pipeline_live_stats_worldbank.py` — deterministic fsspec `memory://` integration test
- `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html` — GAP-013 closed + Test Failure Mapping rows
- research: `.planning/coursework/research/bigdata/gap013-live-minio-worldbank-stats-2026-06-24.md`; orch evidence: `output/evidence/orch/gap-013/`

Findings:
- The live `_read_bronze_stats_frames` branch only read Eurostat TSV; World Bank (the only source mapping to a live Gold feature) was dropped, so a genuinely-live Gold stats matrix was silently feature-less.
- `silver.stats.load.load_worldbank_frame` already parses deterministic World Bank `[meta, records]` JSON and tags rows `source_system='worldbank'`; the fix reuses it (no LLM, no numeric rewriting).
- The Codex agent's exec sandbox could not spawn processes (`CreateProcessAsUserW failed: 5`); orchestrator ran verification + closure.

Evidence:
- `python -m pytest -q -m integration tests/test_pipeline_live_stats_worldbank.py` → 2 passed (WB frame returned alongside Eurostat; WB values byte-exact HU=789.12/AT=456.78; `_catalogue` skipped; zero-WB WARN fires).
- `python -m pytest -q` (JAVA_HOME=jdk-21) → 123 passed, 1 skipped (known Windows Spark/winutils skip).
- `python -m compileall -q src tests` → clean.

Next:
- Merge PR; rebase GAP-019's PR over the shared GAP_REGISTER/dashboard rows.

## 2026-06-24 - KSH XLSX Silver Stats Reader

Status: done for `silver/stats-ksh-xlsx-reader`.

Changed:
- Added `openpyxl` dependency for deterministic XLSX parsing.
- Added KSH XLSX parsing in `src/railway_lakehouse/silver/stats/load.py`.
- Registered `ksh` in the Silver stats source registry.
- Added `tests/test_silver_stats_ksh.py`.

Verified:
- `python -m pytest -q tests/test_silver_stats_ksh.py`: 4 passed.
- `python -m pytest -q`: 130 passed, 1 skipped.
- The skipped test is Spark-related and is skipped locally because `pyspark` is not installed.

Scope:
- This implements KSH XLSX -> Silver StatFact.
- Statistik Austria ODS and UIC PDF readers remain separate pending tasks.


## 2026-06-24 - PR 24 KSH XLSX Reader Review Fixes

Status: done for review fixes.

Changed:
- Hardened `src/railway_lakehouse/silver/stats/load.py` for live KSH year-first, regional-total, and sectioned single-year workbook layouts.
- Tightened KSH label mapping in `src/railway_lakehouse/silver/stats/merge.py` so road-network rows stay unmapped and passenger/freight/rolling-stock rows map to the intended canonical features.
- Added `openpyxl`/`et-xmlfile` constraint pins and dependency guard coverage.
- Updated `README.md`, `docs/TASKS.md`, `docs/index.html`, `docs/STATE_AND_ROADMAP.md`, and `docs/GAP_REGISTER.md` for the current KSH parser state.
- Added live KSH evidence manifest `output/evidence/pr24-ksh-live-check-after-fix/manifest.json`.

Findings:
- The original PR parsed only simple label-before-year workbooks; current KSH STADAT XLSX files also use year-first feature columns, regional country-total tables, and sectioned one-year tables.
- The original dashboard still reported KSH as having no XLSX reader while the task row said done.
- The first live parser probe skipped current `ksh_rail_network`, `ksh_rail_passenger`, and `ksh_rail_rolling_stock` shapes or flattened units too aggressively.

Evidence:
- `python -m pytest -q tests/test_silver_stats_ksh.py`: 9 passed.
- `python -m pytest -q tests/test_silver_stats_ksh.py tests/test_env_versions.py`: 14 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/pr24-ksh-live-check-after-fix --max-artifacts 6 --timeout-seconds 60`: 6 artifacts, 92,509 bytes, 0 failures.
- Live parse over `output/evidence/pr24-ksh-live-check-after-fix/bronze`: 6 KSH frames parsed, unified Silver output 382 rows x 8 columns, and 0 road-network rows mapped into Silver features.
- `python -m pytest -q -m integration`: 16 passed, 121 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q`: 136 passed, 1 skipped.
- `python -m compileall -q src tests`: passed.

Next:
- Keep GAP-005 open until KSH is scheduled through `src/railway_lakehouse/bronze/run.py`.
- Add KSH-to-Gold real-data evidence when persisted Silver/Gold runs include KSH rows.

## 2026-06-24 - PR 25 broad stats pipeline review fixes

Status: done.

Changed:
- `src/railway_lakehouse/bronze/sources/eurostat.py`
- `src/railway_lakehouse/bronze/sources/worldbank.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `src/railway_lakehouse/gold/build.py`
- `scripts/bronze_volume.py`
- `tests/test_bronze_live_check.py`
- `tests/test_bronze_characterization.py`
- `tests/test_eurostat_hardening.py`
- `tests/test_silver_eu_stats_features.py`
- `tests/test_silver_stats_integration.py`
- `tests/test_bronze_volume.py`
- `tests/test_pipeline_live_stats_worldbank.py`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/GAP_REGISTER.md`
- `.planning/coursework/research/bigdata/pr25-bigdata-stats-pipeline-review-2026-06-24.md`

Findings:
- PR #25's broad stats goal was directionally correct, but production ingestion and bounded live checks had drifted; shared selector helpers now drive both.
- Unknown World Bank IDs no longer fall back to human labels, preventing non-rail transport indicators from mapping into rail features by substring.
- Eurostat and World Bank catalogue IDs are path-safe filtered before Bronze landing.
- Eurostat collection now has dataset-count and byte-size bounds; dataset reads use bounded streaming when supported.
- `scripts/bronze_volume.py` now handles missing roots and bounded artifact/file reads instead of assuming a small trusted tree.
- The review branch was rebased/merged over current `main`; stale conflict markers in `pipeline.py` and `tests/test_pipeline_live_stats_worldbank.py` were resolved before verification.

Evidence:
- Focused review suite: 69 passed.
- `python -m pytest -q -m unit` -> 144 passed, 18 deselected.
- `python -m pytest -q -m integration` -> 16 passed, 146 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 161 passed, 1 skipped (known Windows Spark `HADOOP_HOME`/`winutils.exe` skip).
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q -m spark` -> 1 passed, 1 skipped, 160 deselected.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF normalization warnings only.
- Bounded live Eurostat/World Bank run under `output/runtime/pr25-live-bounded/`: Eurostat passed, World Bank partial on one no-series discovered indicator, 9 artifacts, 23,209,819 bytes.
- Stats-only Bronze-to-Gold smoke from that live Bronze tree: 3,548 rows x 9 columns, 157 geos, 1962-2025, AT/HU present.
- `python scripts/bronze_volume.py output/runtime/pr25-live-bounded/bronze --out output/runtime/pr25-live-bounded/bronze_volume.json` -> 9 datasets/artifacts, 99,937 observations.
- `python scripts/minio_smoke.py` against existing `railway-minio` -> 32 B write/read/delete round-trip passed.

Next:
- Push PR #25 fixes, wait for GitHub checks, merge PR #25, and remove the temporary PR worktree.

## 2026-06-24 - PR #21 Eurostat pipeline review

Status: done.

Changed:
- `.ship/pr/21/report.md`
- `.ship/pr/21/mode.json`
- `.ship/pr/21/sources.json`
- `.planning/coursework/research/bigdata/pr21-eurostat-pipeline-review-2026-06-24.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- PR #21 hardens Eurostat Bronze collection and adds dataset-aware Silver parsing, but the default bounded Eurostat live-check seeds are `tran_r_rago` and `tran_r_rapa`; a live probe against the PR worktree showed both fetchable datasets produce zero Silver rows under `read_eurostat_tsv`.
- The new Eurostat Silver tests call `build_crosswalk()` without isolating `CROSSWALK_PATH`, which created a repo-local `silver/crosswalk_cache.json` during targeted verification.
- The PR changes parser/source state without updating `docs/TASKS.md` and `docs/index.html`, matching the existing dashboard-sync reminder comment on the PR.
- The deterministic new test modules are not marked `pytest.mark.unit`, so `-m unit` selected only the existing Eurostat live-check test.

Evidence:
- Review report: `.ship/pr/21/report.md`.
- Posted PR comment: https://github.com/pol3et/railway-bigdata/pull/21#issuecomment-4789471429.
- `python -m pytest -q tests/test_eurostat_hardening.py tests/test_eurostat_silver_reader.py tests/test_bronze_live_check.py -k eurostat` -> 14 passed, 10 deselected.
- `python -m pytest -q` -> 121 passed, 1 skipped.
- `python -m pytest -q -m unit tests/test_eurostat_hardening.py tests/test_eurostat_silver_reader.py tests/test_bronze_live_check.py -k eurostat` -> 1 passed, 23 deselected.
- Live Eurostat probe with `PYTHONPATH` pinned to `Halo-Skills-pr-21`: bounded codes `tran_r_rago`, `tran_r_rapa`; both `silver_rows=0`.

Next:
- PR author should either choose bounded seeds that exercise mapped Eurostat features, or add rules/tests for `tran_r_rago` and `tran_r_rapa`; isolate the test crosswalk cache; and update `docs/TASKS.md` / `docs/index.html` if the PR changes Eurostat status.

## 2026-06-24 - PR #26 UIC PDF reader ship-pr review

Status: done for read-only review; no PR comments posted.

Changed:
- `.ship/pr/26/report.md`
- `.ship/pr/26/mode.json`
- `.ship/pr/26/sources.json`
- `.planning/coursework/research/bigdata/pr26-uic-pdf-reader-review-2026-06-24.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Findings:
- PR #26 is open but conflicting with `origin/main`; merge-tree reports conflicts in docs, `pyproject.toml`, `src/railway_lakehouse/silver/stats/load.py`, and `tests/test_silver_stats_ksh.py`.
- The two existing real UIC PDF artifacts from `output/evidence/uic-live-check-2026-06-22/bronze` produced zero rows through `load_uic_frame()` and zero unified rows through `build_silver_stats()`.
- The UIC unit tests monkeypatch fake extracted text and do not exercise real `pdfplumber` extraction or UIC `build_silver_stats`.
- Additional survived findings: bare `at` can become `geo=AT`, decimal-comma values parse incorrectly, dashboard/constraints are stale, and UIC `source_column` loses original provenance.

Evidence:
- Review report: `.ship/pr/26/report.md`.
- Research note: `.planning/coursework/research/bigdata/pr26-uic-pdf-reader-review-2026-06-24.md`.
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py` -> 4 passed.
- Focused suite -> 14 passed.
- `python -m pytest -q` in PR worktree -> 135 passed, 1 skipped.
- Real UIC PDF parse probe -> both PDFs `silver_rows=0`; `build_silver_stats` rows=0.
- `git merge-tree --write-tree origin/main HEAD` -> exit 1 with conflicts.
- External research: Context7 pdfplumber/Camelot docs; Tavily PDF extraction synthesis; Ref attempted but unavailable due credits.

Next:
- Rebase PR #26 over current `main`, split or settle KSH branch state, and replace the line-regex UIC parser with a table-aware parser tested against a realistic UIC PDF fixture before marking UIC done.

## 2026-06-24 - PR 26 UIC PDF reader review fixes

Status: done for review fixes.

Changed:
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `tests/test_silver_stats_uic_pdf.py`
- `pyproject.toml`
- `constraints.txt`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/STATE_AND_ROADMAP.md`
- `docs/GAP_REGISTER.md`
- `output/report/REPORT.md`
- `.planning/coursework/research/bigdata/pr26-uic-pdf-reader-fix-2026-06-24.md`
- `output/evidence/pr26-uic-pdf-silver-probe/manifest.json`

Findings:
- The original UIC line heuristic parsed zero rows because the real Synopsis PDF stores feature labels in table headers and values in separate country/operator rows.
- OCR is not needed for the current public Synopsis PDF; `pdfplumber` extracts text and a table from it.
- The current Traffic Trends PDF has no country-level Synopsis table and is skipped rather than parsed by narrative heuristics.
- UIC parsing is deliberately scoped to recognized UIC stat tables and exact AT/HU country codes for this project.

Evidence:
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py` -> 6 passed.
- Real UIC PDF probe with `PYTHONPATH=src` over `output/evidence/uic-live-check-2026-06-22/bronze`: Synopsis parsed to 39 rows; Traffic Trends parsed to 0 rows; `build_silver_stats` produced 39 unified rows across 9 mapped UIC features.
- Evidence manifest: `output/evidence/pr26-uic-pdf-silver-probe/manifest.json`.
- External reference used through Context7: `pdfplumber` `Page.extract_tables()` docs at https://github.com/jsvine/pdfplumber/blob/stable/README.md.

Next:
- Keep GAP-005 open until UIC is scheduled through `src/railway_lakehouse/bronze/run.py`.
- Add UIC-to-Gold real-data evidence when persisted Silver/Gold runs include UIC rows.

## 2026-06-25 - PR 27 Spark analysis review fixes

Status: done for review fixes.

Changed:
- `src/railway_lakehouse/gold/build.py`
- `src/railway_lakehouse/spark_jobs/correlations.py`
- `src/railway_lakehouse/spark_jobs/regional.py`
- `tests/test_silver_eu_stats_features.py`
- `tests/test_spark_stack_pins.py`
- `tests/test_spark_analysis_jobs.py`
- `output/evidence/analysis-artifacts/`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/VERIFICATION.md`
- `.planning/coursework/research/bigdata/pr27-spark-analysis-review-fixes-2026-06-25.md`

Findings:
- PR #27 originally injected a constant `terrain_complexity` into Gold without a
  source contract; that fabricated feature was removed.
- The new Spark jobs now default to the existing committed Gold Parquet and fail
  loudly when the selected Gold lacks rail-investment or regional columns.
- Correlation outputs are mode-specific, so panel/level and pooled/by-country
  runs no longer overwrite each other.
- Per-country Spearman ranking now partitions by country and variable.
- The committed analysis snapshot now lives under
  `output/evidence/analysis-artifacts/`; manifests point to committed CSV copies
  and mark the original source Gold/Parquet outputs as not committed.

Evidence:
- `$env:PYTHONPATH='src'; $env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q tests/test_silver_eu_stats_features.py tests/test_spark_stack_pins.py tests/test_spark_analysis_jobs.py` -> 19 passed, 2 skipped because this Windows worktree has no `HADOOP_HOME` with `bin/winutils.exe`.
- `$env:PYTHONPATH='src'; python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF normalization warnings only.

Next:
- Push PR #27 fixes, wait for GitHub checks, merge PR #27, and remove the
  temporary PR worktree.

## 2026-06-25 - News multi-model preprocessing spec + 14-task pack + adversarial review

Status: done for design/planning (docs only; git left to the owner).

Changed:
- `docs/SPEC_NEWS_PREPROCESSING.md` (new) — design + eval strategy + single-box (Ryzen 1600 / GTX 1060 6GB) sequential-pass compute plan + 8 must-fix review blockers + MVP build order + open decisions.
- `docs/GAP_TASKS.md` — appended 14 pick-up-cold specs (GAP-031…044).
- `docs/GAP_REGISTER.md` — GAP-031…044 rows. `docs/TASKS.md` — Wave 6. `docs/index.html` — WAVE 6 chips + footer + snapshot 2026-06-25.
- `.planning/coursework/research/bigdata/news-model-spec-task-pack-2026-06-25.md` (research record).

Findings:
- Method: dynamic workflow (1 spec author + 14 task-spec authors + 5 independent reviewers + 1 synthesis = 21 agents); `research-orchestrator` routed (Tavily/Exa/Context7/Ref/WebFetch).
- Owner decisions: UIC PDF = capture-all/map-deliberately (GAP-041); single box, sequential model passes (6 GB VRAM), torch CPU-only on Py3.14 (Ollama uses GPU).
- Must-fix review blockers recorded in the spec: torch CPU-only on Py3.14; GDELT/RSS = snippets; GKG absent for live DOC rows; LaBSE→e5/bge-m3; Spark KMeans non-deterministic; NER ids were base LMs; cache-key/identity unsound; golden-set statistics.

Evidence:
- No source edits, tests, or live runs. Spec claims grounded in agent file:line reads; review claims cite source URLs (PyTorch #169929, SPARK-21679, MMTEB 2502.13595, HF model cards).

Next:
- Owner resolves the spec's open decisions; build MVP-first: GAP-039 → GAP-033 → P1 encoders/Gold/eval.

## 2026-06-25 - GAP-050 LLM Pipeline Engineering

Status: done

Changed:
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/news/failures.py`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/ollama_client.py`
- `tests/test_silver_news_extract_prompt.py`
- `tests/test_silver_news_extraction_e2e.py`
- `tests/test_spark_analysis_jobs.py`
- `tests/test_spark_coverage.py`
- `docs/LLM_EXTRACTION_DESIGN.md`
- `docs/DATA_CONTRACTS.md`
- `docs/SILVER_DESIGN.md`
- `docs/INDEX.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.planning/coursework/plans/bigdata/gap-050-llm-pipeline-engineering.md`
- `.planning/coursework/research/bigdata/llm-pipeline-engineering-gap050.md`

Findings:
- The Claude GAP-050 draft was stale after GAP-039: cache and basic failure sidecar already existed, but the prompt remained too broad and the cache digest lacked an explicit prompt version.
- The current `NewsFeature` schema has no `monetary_currency`; GAP-050 stores original currency text in `monetary_raw` and does not perform FX conversion.
- LangChain-style batch parallelism is not useful on this single 6 GB GPU; the implemented default is a sequential cached runner with observable retry and lifecycle hooks.

Evidence:
- `python -m pytest -q -m unit tests/test_silver_news_extract_prompt.py` -> 5 passed.
- `python -m pytest -q -m integration tests/test_silver_news_extraction_e2e.py` -> 3 passed.
- `python -m pytest -q tests/test_pipeline_gaps.py tests/test_silver_news_parsers.py` -> 19 passed.
- `python -m pytest -q` -> 190 passed, 6 skipped.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q -m spark` -> 3 passed, 3 skipped.
- `python -m compileall -q src tests` -> passed.

Next:
- GAP-033 should call `run_extraction_pipeline(..., warm_up=True, unload_after=True)` for the bounded live Ollama run and persist the returned failures plus run manifest as evidence.

## 2026-06-25 - Full roadmap + compute/embedder/feature research + GAP-045…050

Status: done for planning (docs only; git left to the owner).

Changed:
- `docs/ROADMAP_NEWS_TO_REPORT.md` (new) — Sessions A/B/C, Waves 6-7, Contracts D/E/F; EDA-first (hypotheses formed FROM artifacts in GAP-048, not pre-listed); single-box compute plan; all-data-local note; investment finding.
- `docs/GAP_TASKS.md` — appended GAP-045…050 specs. `docs/GAP_REGISTER.md` — GAP-045…050 rows. `docs/TASKS.md` — Wave 7 + GAP-050. `docs/index.html` — WAVE 7 + GAP-050 chips + footer (GAP-001…050). `docs/SPEC_NEWS_PREPROCESSING.md` — embedder/sidecar decision. Research note `roadmap-compute-eda-2026-06-25.md`.

Findings / owner decisions:
- Embedder DEFAULT = `multilingual-e5-base` (short snippets; dedup is algorithm-dominated; config knob, bge-m3 swappable). torch via Py3.12+cu126 GPU sidecar (Pascal sm_61; cu128+ drops it) or CPU; sequential passes; kill idle MCP servers.
- Investment = Eurostat `rail_investment` (dense) primary, news money secondary; 9/12 teammate correlates already collected; new WB codes IS.VEH.PCAR.P3 + PA.NUS.PPP (GAP-045); terrain/coords-speeds deferred.
- GAP-050 = LLM prompt-engineering design (prompt-master + research-orchestrator), precedes GAP-033. All data local (MinIO volume + output/).

Evidence:
- No source edits, tests, or live runs. Sources cited: PyTorch #169929, uv #14742 (sm_61/cu126), WB indicator pages, Eurostat, MMTEB 2502.13595.

Next:
- Orchestrate Wave 6a (GAP-039 → GAP-050 → GAP-033) via `scripts/orch/codex_impl.sh` once the owner gives go.

## 2026-06-25 - GAP-039 wide NewsFeature contract + cache

Status: done; ready for PR.

Changed:
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/failures.py`
- `src/railway_lakehouse/silver/persist.py`
- `tests/test_silver_news_wide_contract.py`
- `tests/test_silver_news_extraction_e2e.py`
- `docs/DATA_CONTRACTS.md`, `README.md`, dashboard docs
- `.planning/coursework/research/bigdata/newsfeature-wide-contract.md`

Findings:
- GAP-039 closes the wide article-grain Silver news contract with 43 dataclass fields, content-hash/model-digest cache wiring, in-memory extraction failures plus JSON sidecar helper, and legacy 15-field load compatibility.
- Live LLM quality remains intentionally deferred to GAP-033/GAP-050 and downstream model-population gaps.

Evidence:
- `python -m pytest -q -m unit tests/test_silver_news_wide_contract.py` -> 10 passed.
- `python -m pytest -q -m integration tests/test_silver_news_extraction_e2e.py` -> 1 passed.
- `python -m compileall -q src tests` -> passed.
- Full suite result already verified before ship step: 183 passed, 3 skipped.

Next:
- Open PR for `impl/gap-039` against `main`; continue Wave 6 with GAP-050 then GAP-033 after merge.

## 2026-06-25 - GAP-039 PR review fixes

Status: done; PR #28 updated.

Changed:
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/run.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/config.py`
- `tests/test_pipeline_gaps.py`
- `tests/test_silver_news_extraction_e2e.py`
- `tests/test_silver_news_wide_contract.py`

Findings:
- Production news extraction now passes a configurable `FileSystemCache` instead of the no-op default.
- Bronze GDELT normalization preserves GKG/tone/source metadata so passthrough rows avoid the LLM.
- GDELT tone selection now preserves a valid `0` tone as neutral.

Evidence:
- Focused regressions: 4 passed.
- `python -m compileall -q src tests` -> passed.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 187 passed, 3 skipped.

Next:
- Wait for PR #28 checks/review; continue with GAP-050/GAP-033 after merge.

## 2026-06-25 - GAP-050 PR #29 review fixes

Status: done; PR #29 updated.

Changed:
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/run.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/news/failures.py`
- `src/railway_lakehouse/silver/config.py`
- `tests/test_pipeline_gaps.py`
- `tests/test_silver_news_extraction_e2e.py`
- `tests/test_silver_news_extract_prompt.py`
- `tests/test_silver_news_wide_contract.py`
- `docs/LLM_EXTRACTION_DESIGN.md`, `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`
- `.planning/coursework/research/bigdata/llm-pipeline-engineering-gap050.md`

Findings:
- Review P1 was valid: `pipeline.run_pipeline()` and `silver.run.run_news()` still used the compatibility `extract_batch()` path, so live production runs would not write the GAP-050 run manifest or persist the typed failure sidecar.
- Review P2 was valid: deterministic GDELT passthrough cache keys ignored GKG/source annotations that affect the produced `NewsFeature`.
- Review P3 was valid: `max_attempts=0` needed explicit validation to avoid zero-attempt accounting gaps.

Evidence:
- RED regressions before fixes: 4 failed for missing production artifact parameters, stale GDELT replay, and missing `max_attempts` validation.
- Focused affected files after fixes: `python -m pytest -q tests/test_silver_news_extract_prompt.py tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py tests/test_pipeline_gaps.py` -> 35 passed.
- Verify command: `python -m pytest -q -m unit tests/test_silver_news_extract_prompt.py` -> 6 passed; `python -m pytest -q` -> 194 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.

Next:
- GAP-033 can run the now-wired production path with live Ollama and commit bounded evidence artifacts under `output/evidence/`.

## 2026-06-25 - GAP-033 live qwen3:4b news extraction evidence

Status: done; shipping via PR.

Changed:
- `tests/test_silver_news_extraction_live.py`
- `output/evidence/news-extraction-sample/MANIFEST.md`
- `output/evidence/news-extraction-sample/silver/news/news_feature/ingest_date=2026-06-25/news_feature.parquet`
- `output/evidence/news-extraction-sample/silver/news/news_extraction_runs/ingest_date=2026-06-25/manifest.json`
- `output/evidence/news-extraction-sample/silver/news/news_extraction_failures/ingest_date=2026-06-25/failures.json`
- `output/evidence/news-extraction-sample/railway_ml.parquet`
- `output/evidence/news-extraction-sample/counts.json`
- `.planning/coursework/research/bigdata/silver-news-llm-extraction-live.md`
- `.planning/coursework/plans/bigdata/gap-033-news-llm-extraction-live.md`
- `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/LLM_EXTRACTION_DESIGN.md`

Findings:
- Local Ollama 0.30.9 served `qwen3:4b` Q4_K_M; API model digest is `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- The bounded real Bronze pool contained 237 parsed articles (`gdelt=25`, `rss=212`); the live extraction selected 40 (`gdelt=25`, `rss=15`).
- The GAP-050 production `silver.run.run_news(...)` path processed 40/40 articles, persisted 40 validated `NewsFeature` rows, wrote a run manifest, and wrote an empty failure sidecar.
- Quality caveat: schema and persistence are proven, but sparse GDELT snippets over-marked some non-rail items as rail-related; report-quality gates remain GAP-040/GAP-043 follow-up.

Evidence:
- `python -m pytest tests/test_silver_news_extraction_live.py -m live -v` -> 1 passed.
- Parquet readback -> `(40, 43)`, `is_rail_related`: `True=21`, `False=19`.
- `python -m pytest -m unit -q` -> 171 passed, 30 deselected.
- `python -m pytest -q` -> 195 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed (line-ending warnings only).

Next:
- Use GAP-043 to add a held-out quality harness before report-grade use of the qwen3:4b outputs; use GAP-040/GAP-022 to improve Gold news aggregation and RSS date coverage.

## 2026-06-25 - GAP-044 parser correctness audit

Status: done; shipping via PR.

Research:
- `research-orchestrator` record written at `.planning/coursework/research/bigdata/parser-correctness-audit.md`.
- Self-approved implementation plan written at `.planning/coursework/plans/bigdata/gap-044-parser-correctness-audit.md`.

Changed:
- Hardened parser and aggregation code in `src/railway_lakehouse/silver/news/rss.py`, `src/railway_lakehouse/silver/news/gdelt.py`, `src/railway_lakehouse/silver/news/extract.py`, `src/railway_lakehouse/silver/stats/load.py`, and `src/railway_lakehouse/gold/build.py`.
- Added self-contained parser golden fixtures under `tests/fixtures/silver/` for RSS, GDELT, World Bank, Eurostat, KSH, and UIC.
- Added parser golden-fixture, robustness, field-coverage, and import/schema guard tests.
- Added `docs/PARSER_FIELD_COVERAGE.md` and `docs/PARSER_FIELD_COVERAGE.json`; synced `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, and `README.md`.
- Added `.gitattributes` binary guards for fixture formats such as PDF, XLSX, GZ, ODS, and Parquet.

Findings:
- The draft spec was stale on schema details: `NewsFeature` is a 43-field dataclass, not a 15-field Pydantic model.
- The worktree did not contain raw KSH/UIC bytes under `output/evidence/`; KSH/UIC fixtures are deterministic parser-shape samples modeled on the current parser contract and evidence manifests, with no test-time network access.
- RSS malformed XML now logs and skips a feed; GDELT malformed JSON/articles log and skip bad rows; Gold news aggregation handles ISO, GDELT compact, and RFC-822 dates plus dict rows missing optional fields.

Evidence:
- TDD red run before fixes: focused parser suite -> 7 failed, 14 passed.
- Focused verify: `python -m pytest -q tests/test_silver_parser_golden_fixtures.py tests/test_parser_robustness.py tests/test_parser_field_coverage.py tests/test_parser_imports_and_schemas.py` -> 21 passed.
- Full suite: `python -m pytest -q` -> 216 passed, 6 skipped.
- Compileall: `python -m compileall -q src tests` -> passed.
- Coverage smoke: `python -c "import json; m=json.load(open('docs/PARSER_FIELD_COVERAGE.json', encoding='utf-8')); assert len(m['sources']) >= 6; print('Parser coverage matrix OK')"` -> Parser coverage matrix OK.
- `git diff --check` -> passed with line-ending warnings only.

Next:
- Open the GAP-044 PR against `main`; follow-up report-quality gaps remain GAP-040/GAP-043, Statistik Austria parser work remains GAP-042, and UIC widening remains GAP-041.
## 2026-06-25 - GAP-036 Silver news embeddings and dedup markers
## 2026-06-25 - GAP-031 GDELT GKG parser and passthrough
## 2026-06-25 - GAP-034 deterministic XLM-R sentiment encoder
## 2026-06-25 - GAP-041 UIC Widen And Staging

Status: done

Changed:
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/persist.py`
- `tests/test_silver_stats_uic_pdf.py`
- `docs/DATA_CONTRACTS.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/silver-uic-pdf-widen-and-stage.md`
- `.planning/coursework/plans/GAP-041-uic-widen-and-stage.md`
- `output/evidence/uic-proof-of-widen-2026-06-25/`

Findings:
- UIC Silver parsing no longer has an AT/HU-only geo gate; the live Synopsis PDF now parses to 738 golden rows across 80 geos while Traffic Trends remains 0 golden rows because it has no country-level synopsis table.
- UIC staging preserves table/header/unmapped rows plus text chunks. Live staging evidence wrote 747 rows, including 476 text chunks across the two public UIC PDFs.
- Ref MCP was unavailable due credits; Context7 plus Firecrawl/Tavily routed the pdfplumber, pycountry, and ISO-3166 research fallback sources.

Evidence:
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py` -> 10 passed.
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py::test_uic_staging_roundtrip_persists_and_reloads -v` -> 1 passed.
- `python -m pytest -q` -> 199 passed, 6 skipped.
- `python -m compileall -q src tests` -> clean.
- `python -m html.parser docs/index.html` -> clean.
- `python -m railway_lakehouse.bronze.live_check --sources uic --out output/evidence/uic-proof-of-widen-2026-06-25 --max-artifacts 2 --timeout-seconds 30` -> artifact_count=2, byte_count=2109240, UIC passed.
- `output/evidence/uic-proof-of-widen-2026-06-25/uic_staging_summary.json` records the staging/golden counts.

Next:
- Open the PR for `impl/gap-041` and wait for review/merge.
## 2026-06-25 - GAP-040 widened Gold news aggregation
## 2026-06-25 - GAP-045 World Bank macro indicators
## 2026-06-25 - GAP-035 deterministic Silver language ID

Status: done; shipping via PR.

Changed:
- `src/railway_lakehouse/silver/news/embeddings.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/persist.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/config.py`
- `pyproject.toml`
- `tests/test_silver_news_embeddings.py`
- `tests/test_silver_news_embeddings_integration.py`
- `tests/test_silver_news_wide_contract.py`
- `tests/test_silver_persist_integration.py`
- `tests/test_gold_load_from_silver.py`
- `.planning/coursework/research/bigdata/labse-embeddings-dedup.md`
- `.planning/coursework/plans/bigdata/gap-036-news-embeddings-dedup.md`
- `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/STATE_AND_ROADMAP.md`, `docs/TASKS.md`, `docs/index.html`, `docs/GAP_REGISTER.md`, `README.md`

Findings:
- The Claude draft was stale: GAP-039 already reserved `text_embedding_model`, `text_embedding`, `cluster_id`, and `cross_lingual_dedup_id`, so GAP-036 reuses those fields and adds only `is_duplicate`.
- The repo's reviewed model decision is `intfloat/multilingual-e5-base`, not LaBSE. `text_embedding` now persists as `list<float32>`.
- `cluster_near_duplicates()` assigns deterministic `cross_lingual_dedup_id` values from sorted article ids at cosine threshold 0.95 and marks non-canonical siblings with `is_duplicate=True`.
- Spark-scale dedup enforcement and Gold count deflation remain GAP-037/GAP-040.

Evidence:
- `python -m pytest -q tests/test_silver_news_embeddings.py -v` -> 10 passed.
- `python -m pytest -q -m integration tests/test_silver_persist_integration.py tests/test_gold_load_from_silver.py tests/test_silver_news_embeddings_integration.py -v` -> 2 passed, 1 skipped (`sentence_transformers` not installed).
- `python -m pytest -q -m unit` -> 181 passed, 31 deselected.
- `python -m pytest -q -m integration` -> 23 passed, 1 skipped, 188 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 208 passed, 4 skipped.
- `python -m compileall -q src tests` -> passed.
- `Select-String -Path docs/DATA_CONTRACTS.md -Pattern 'embedding|dedup_group_id|cross_lingual_dedup_id|is_duplicate'` -> returned the updated embedding/dedup contract lines.
- Schema smoke after refreshing editable install -> passed.

Next:
- GAP-037 should consume persisted embeddings in Spark for distributed clustering; GAP-040 should enforce canonical/duplicate filtering before report-grade Gold news counts.

## 2026-06-25 - GAP-036 PR review fixes

Status: done; PR #39 updated.

Changed:
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/embeddings.py`
- `tests/test_silver_news_extraction_e2e.py`
- `tests/test_silver_news_extract_prompt.py`
- `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/index.html`, `docs/GAP_REGISTER.md`, `README.md`

Findings:
- PR review P1 was valid: production `run_extraction_pipeline(...)` computed embeddings but did not call `cluster_near_duplicates(...)`.
- Production Silver news extraction now gates embedding model use on `sentence_transformers` availability, clusters after embeddings are present, and refreshes cache entries with the resulting dedup markers.
- The regression test uses the production `silver.run.run_news(...)` entrypoint with mocked embeddings, so CI needs no GPU or network.

Evidence:
- RED check before the fix: `python -m pytest -q tests/test_silver_news_extraction_e2e.py::test_run_news_production_entrypoint_clusters_cross_lingual_duplicates -v` failed with `cross_lingual_dedup_id is None`.
- `python -m pytest -q tests/test_silver_news_embeddings.py tests/test_silver_news_extract_prompt.py tests/test_silver_news_extraction_e2e.py -v` -> 22 passed.
- `python -m pytest -q -m integration tests/test_silver_persist_integration.py tests/test_gold_load_from_silver.py tests/test_silver_news_embeddings_integration.py tests/test_silver_news_extraction_e2e.py -v` -> 7 passed, 1 skipped (`sentence_transformers` not installed).
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 210 passed, 4 skipped.
- `python -m compileall -q src tests` -> passed.

Next:
- PR #39 can proceed through review/CI; GAP-037/GAP-040 remain the Spark/Gold enforcement follow-ups.
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/news/gkg_parser.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `tests/test_silver_gkg_parser.py`
- `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`
- `.planning/coursework/research/bigdata/silver/gdelt-gkg-codebook-2026-06-25.md`
- `.planning/coursework/plans/bigdata/gap-031-gdelt-gkg-parser.md`

Findings:
- The original GAP-031 draft was stale after GAP-039/GAP-050: `NewsFeature` already had GKG columns and cached passthrough already existed for GDELT article dicts carrying `gkg_*`.
- Official GDELT docs show GKG 2.1 is a 27-column tab-delimited format and GKG 1.0 daily rows use a different tab-delimited layout; GAP-031 supports fixture-covered parser paths for both.
- GKG themes are text tokens, not numeric CAMEO event codes, so event mapping is limited to explicit rail/transport theme tokens and falls back to `other`.
- No live GKG backfill, separate GKG Silver table, or automatic DOC-to-GKG URL cross-linking is claimed.

Evidence:
- RED: `python -m pytest -q tests/test_silver_gkg_parser.py` failed on missing `GKGRecord` before implementation.
- `python -m pytest -q tests/test_silver_gkg_parser.py` -> 28 passed.
- `python -m pytest -q -m unit tests/test_silver_gkg_parser.py` -> 27 passed, 1 deselected.
- `python -m pytest -q tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py` -> 16 passed.
- `python -m pytest -q -m integration` -> 25 passed, 204 deselected.
- `python -m pytest -q` -> 223 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF warnings only.

Next:
- Feed real historical GKG Bronze files through the parser once the live history backfill is run; keep automatic URL cross-linking as a separate follow-up.

## 2026-06-25 - GAP-031 PR #33 production GKG wiring fixes

Status: done; shipping via PR #33 update.

Changed:
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/run.py`
- `tests/test_silver_gkg_parser.py`
- `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/TASKS.md`, `docs/index.html`
- `.planning/COURSEWORK_PROGRESS.md`
- `.planning/coursework/research/bigdata/silver/gdelt-gkg-codebook-2026-06-25.md`

Findings:
- The PR #33 review was valid: the first GAP-031 implementation parsed GKG ZIPs only in tests/direct helpers and did not feed them through `pipeline.run_pipeline(...)` or `silver.run.run_news(...)`.
- Production now reads raw Bronze `*.gkg.csv.zip` files from `news/gdelt_history/gkg_v1_daily`, parses transient `GKGRecord` objects, forwards them to `run_extraction_pipeline(..., gkg_records=...)`, and emits bounded GKG-sourced GDELT article rows when no matching article row exists.
- The fix still does not claim a live high-volume backfill run or a persisted GKG Silver table.

Evidence:
- RED: targeted review regressions failed on missing `gkg_records` plumbing and ignored GKG ZIP Bronze input.
- `python -m pytest -q tests/test_silver_gkg_parser.py` -> 28 passed.
- `python -m pytest -q -m integration` -> 25 passed, 204 deselected.
- `python -m pytest -q` -> 223 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.

Next:
- Keep live historical volume evidence and richer DOC-to-GKG dedup/cross-linking as follow-up work.
- `pyproject.toml`
- `src/railway_lakehouse/silver/news/sentiment_encoder.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/gold/build.py`
- `tests/conftest.py`
- `tests/test_silver_sentiment_encoder.py`
- `tests/test_silver_news_sentiment_imports.py`
- `tests/test_silver_news_extract_prompt.py`
- `tests/test_silver_characterization.py`
- `tests/test_gold_characterization.py`
- `.planning/coursework/research/bigdata/silver-sentiment-encoder.md`
- `.planning/coursework/plans/bigdata/gap-034-sentiment-encoder.md`
- `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`, `docs/GAP_TASKS.md`, `docs/TASKS.md`, `docs/index.html`

Findings:
- The drafted spec was stale: GAP-050 had already removed sentiment from the LLM prompt/schema.
- CardiffNLP revision `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8` is the pinned model revision used by the encoder; the draft's `59b7eda` revision was not current.
- German and English are in the model fine-tune language set; Hungarian remains a multilingual transfer/out-of-domain use case and needs later evaluation/calibration.
- Gold now prefers deterministic signed `sentiment_score` and falls back to legacy label mapping for rows without encoder scores.

Evidence:
- `python -m pytest -q tests/test_silver_sentiment_encoder.py` -> 7 passed.
- `python -m pytest -q tests/test_silver_news_parsers.py` -> 7 passed.
- `python -m pytest -q tests/test_silver_sentiment_encoder.py tests/test_silver_news_sentiment_imports.py tests/test_silver_news_parsers.py` -> 15 passed.
- `python -m pytest -q tests/test_silver_news_extract_prompt.py tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py tests/test_pipeline_gaps.py tests/test_gold_characterization.py` -> 41 passed.
- `python -m pytest -q` -> 204 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with line-ending warnings only.

Next:
- GAP-035 can add deterministic language ID; GAP-043 should evaluate sentiment quality, especially for Hungarian transfer behavior.

## 2026-06-25 - GAP-034 PR #31 long-text sentiment review fix

Status: done; PR #31 updated.

Changed:
- `src/railway_lakehouse/silver/news/sentiment_encoder.py`
- `tests/test_silver_sentiment_encoder.py`
- `docs/GAP_REGISTER.md`

Findings:
- Review P2 was valid: `SentimentEncoder.encode()` called the Hugging Face pipeline without truncation kwargs, so an over-length article could raise at the 512-token XLM-R boundary and be reduced to null sentiment.
- P3 cache replay was left out of this narrow fix because skipping cache writes for null sentiment would change broader production cache semantics and manifest counts; backend dependency declaration was also left out because a trivial torch pin is not available for this Python 3.14 stack.

Evidence:
- RED regression before fix: `test_sentiment_encoder_truncates_long_text_at_model_boundary` failed because encode returned `None` after a mocked length error.
- `python -m pytest -q tests/test_silver_sentiment_encoder.py::test_sentiment_encoder_truncates_long_text_at_model_boundary` -> 1 passed.
- `python -m pytest -q tests/test_silver_sentiment_encoder.py` -> 8 passed.
- `python -m pytest -q tests/test_silver_sentiment_encoder.py tests/test_silver_news_sentiment_imports.py tests/test_silver_news_parsers.py` -> 16 passed.
- `python -m pytest -q tests/test_silver_news_extract_prompt.py tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py tests/test_pipeline_gaps.py tests/test_gold_characterization.py` -> 41 passed.
- `python -m pytest -q` -> 205 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with line-ending warnings only.

Next:
- Push the review-fix commit to `origin/impl/gap-034`.
- `src/railway_lakehouse/gold/build.py`
- `tests/test_gold_characterization.py`
- `tests/test_gold_load_from_silver.py`
- `docs/DATA_CONTRACTS.md`
- `docs/TASKS.md`
- `docs/GAP_REGISTER.md`
- `docs/index.html`
- `.planning/coursework/research/bigdata/gold-widen-news.md`

Findings:
- The drafted GAP-040 spec was stale: `NewsFeature` is now a 43-field Silver contract and includes persisted `gkg_*` fields.
- Gold now aggregates deterministic language counts/modal/entropy, confidence stats/bins, rail-line unique/list rollups, bounded GKG tone/token rollups, canonical event/operator counts, and optional year-month grain.
- GAP-016, GAP-022, and GAP-026 are closed inside this change for Gold aggregation: canonical column reindexing, mixed ISO/RFC-822/GDELT date parsing, and optional dict-field defaults are covered.

Evidence:
- Red phase: focused unit suite failed 4 tests and focused integration failed 1 test before implementation.
- `python -m pytest -q -m unit tests/test_gold_characterization.py` -> 9 passed.
- `python -m pytest -q -m integration tests/test_gold_load_from_silver.py` -> 2 passed.
- `python -m pytest -q -m unit` -> 175 passed, 31 deselected.
- `python -m pytest -q -m integration` -> 24 passed, 182 deselected.
- `python -m pytest -q` -> 200 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with line-ending warnings only.

Next:
- Use GAP-043 to evaluate the qwen3:4b NewsFeature quality before report-grade use; use GAP-031/GKG backfill work for deeper GKG parsing or canonical theme pivots.
- `src/railway_lakehouse/bronze/sources/worldbank.py`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `tests/test_macro_indicators.py`
- `.planning/coursework/research/bigdata/macro-indicators-gap045.md`
- `.planning/coursework/plans/bigdata/macro-indicators-gap045-plan.md`
- `output/evidence/macro-indicators-gap045/`
- `README.md`, `docs/STATE_AND_ROADMAP.md`, `docs/GAP_REGISTER.md`, `docs/GAP_TASKS.md`, `docs/TASKS.md`, `docs/index.html`

Findings:
- `PA.NUS.PPP` is active in the live World Bank V2 API and reaches Gold for AT/HU with 36 non-null rows per country (1990-2025).
- `IS.VEH.PCAR.P3` is now collected and mapped to `cars_per_1000`, but current World Bank API data has 0 AT/HU non-null rows; evidence records this as an upstream coverage caveat, not a data claim.
- `IS.VEH.NVEH.P3` was not added.

Evidence:
- RED before implementation: `python -m pytest -q tests/test_macro_indicators.py` -> 2 failed for missing mappings.
- GREEN after implementation: `python -m pytest -q tests/test_macro_indicators.py` -> 2 passed.
- `python -m railway_lakehouse.bronze.live_check --sources worldbank --out output/evidence/macro-indicators-gap045 --max-artifacts 12 --timeout-seconds 90` -> 13 artifacts, 49,874,290 bytes.
- `python -m railway_lakehouse.pipeline --bronze-root output/evidence/macro-indicators-gap045/bronze --skip-news-extraction --news 0 --out output/evidence/macro-indicators-gap045/railway_ml.parquet --crosswalk-path output/evidence/macro-indicators-gap045/crosswalk_cache.json --counts-out output/evidence/macro-indicators-gap045/counts.json` -> 14,903 rows x 12 columns.
- `output/evidence/macro-indicators-gap045/gap045_feature_coverage.json` -> `ppp_conversion_factor` AT/HU 36 rows each; `cars_per_1000` AT/HU 0 rows.
- `python -m pytest -q -m unit` plus the GAP-045 indicator assertion command -> 172 passed, 31 deselected.
- `python -m pytest -q -m integration` -> 24 passed, 179 deselected.
- `python -m pytest -q` -> 197 passed, 6 skipped.
- `src/railway_lakehouse/silver/language_id.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/schema.py`
- `tests/test_silver_language_id.py`
- `tests/test_silver_news_parsers.py`
- `tests/test_silver_news_extraction_e2e.py`
- `tests/test_silver_news_wide_contract.py`
- `tests/test_pipeline_gaps.py`
- `pyproject.toml`, `constraints.txt`
- `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/STATE_AND_ROADMAP.md`, `docs/SPEC_NEWS_PREPROCESSING.md`, `README.md`
- `.planning/coursework/research/bigdata/silver-language-id.md`

Findings:
- GAP-050 had already removed `language` from the LLM JSON schema, but the few-shot prompt examples still carried `language` metadata and validation still accepted raw model language.
- GAP-035 now uses pinned `lingua-language-detector==2.2.0` restricted to EN/DE/HU. `extract_article()` and GDELT passthrough populate `language` and `language_detected_code` deterministically before validation; the LLM prompt/schema no longer include language.
- The extraction cache digest now includes the language-id identity so cached `NewsFeature` rows invalidate if the deterministic classifier changes.

Evidence:
- RED first: `python -m pytest -q tests/test_silver_language_id.py` failed on missing `railway_lakehouse.silver.language_id`.
- `python -c "from railway_lakehouse.silver.language_id import identify_language; print(identify_language('Vasúti bővítés'))"` -> `hu`.
- `python -m pytest -q tests/test_silver_language_id.py` -> 7 passed.
- `python -m pytest -q tests/test_silver_news_parsers.py` -> 7 passed.
- `python -m pytest -q -m unit tests/test_silver_language_id.py` -> 7 passed.
- `python -m pytest -q` -> 202 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed (line-ending warnings only).

Next:
- Use the GAP-045 evidence caveat in EDA/reporting: PPP is available for AT/HU; World Bank car ownership must be treated as not covered for AT/HU unless a later source supplies it.
- GAP-034 can consume `language` for sentiment routing; GAP-038 can use it for conditional NER routing.

## 2026-06-25 - GAP-044 PR #35 merge conflict resolution

Status: done; pushed to PR #35.

Changed:
- Merged `origin/main` into `impl/gap-044`.
- Resolved conflicts in `src/railway_lakehouse/gold/build.py` and `src/railway_lakehouse/silver/news/extract.py`.
- Preserved GAP-044 parser audit guards while keeping main's language ID, sentiment, GKG passthrough, embedding, and dedup behavior.
- Updated the GAP-044 schema guard/docs from 43 to 44 `NewsFeature` fields after main added `is_duplicate`.

Evidence:
- Focused conflict regression: 86 passed.
- Schema/focused guard rerun: 25 passed.
- Full suite: `python -m pytest -q` -> 289 passed, 7 skipped.
- Compileall: `python -m compileall -q src tests` -> passed.

Next:
- PR #35 should be mergeable once GitHub refreshes the updated head.
