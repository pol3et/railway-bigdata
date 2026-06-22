# Project Progress And Findings Log

This is the single persistent log for `bigdata/course_proj`. Future agents should append here before stopping.

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
- `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --skip-news-extraction` passed and wrote Gold Parquet.
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

Status: done for default/model-selection docs; no live Ollama run was launched.

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
