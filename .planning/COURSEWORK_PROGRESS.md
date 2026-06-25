# Coursework Progress

## 2026-06-25 - GAP-031 GDELT GKG Parser And Passthrough

Status: done; shipping via PR.

Review update:
- PR #33 request-changes fixes are included: `pipeline.run_pipeline(...)` now reads Bronze GKG `.gkg.csv.zip` files into transient `GKGRecord` objects, forwards them to the production extraction runner, and creates bounded GKG-sourced GDELT article rows when no matching article row exists.
- `run_extraction_pipeline(..., gkg_records=...)` and `silver.run.run_news(..., gkg_records=...)` now expose the deterministic GKG passthrough path to production entrypoints, not only unit tests.

Research:
- Required note written at `.planning/coursework/research/bigdata/silver/gdelt-gkg-codebook-2026-06-25.md`.
- Used `research-orchestrator` with local files first, then Tavily/Firecrawl MCP against official GDELT GKG codebooks, theme lists, and the GDELT data overview.
- Approved local implementation plan: `.planning/coursework/plans/bigdata/gap-031-gdelt-gkg-parser.md`.

Changed:
- Added transient `GKGRecord` and `silver/news/gkg_parser.py` for fixture-covered GKG 1.0/2.x tab-delimited CSV.zip parsing.
- Extended `gdelt_passthrough()` to accept `GKGRecord` while preserving old bare `gkg_tone/gkg_themes/gkg_locations` calls.
- Added deterministic tone->sentiment, location->country, theme->event_type, and GKG org/person->known-operator mapping.
- Added explicit `article_records_to_news_features(..., gkg_records=...)` routing so matched GDELT articles avoid Ollama.
- Wired Bronze GKG zip parsing through `pipeline.run_pipeline(...)`, including GKG-only tmp Bronze fixture coverage.
- Synced `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, and `docs/PROGRESS_LOG.md`.

Evidence:
- RED: `python -m pytest -q tests/test_silver_gkg_parser.py` failed on missing `GKGRecord`.
- RED review regressions: targeted production-runner tests failed on missing `gkg_records` plumbing and ignored Bronze GKG zip input.
- `python -m pytest -q tests/test_silver_gkg_parser.py` -> 28 passed.
- `python -m pytest -q tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py` -> 16 passed.
- `python -m pytest -q -m integration` -> 25 passed, 204 deselected.
- `python -m pytest -q` -> 223 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF warnings only.

Next:
- Real high-volume historical GKG backfill evidence and richer DOC-to-GKG dedup/cross-linking remain separate follow-ups; this change claims fixture-backed production runner wiring and deterministic passthrough behavior.
## 2026-06-25 - GAP-042 Statistik Austria ODS Reader

Status: done; ready for PR.

Research:
- Required `research-orchestrator` record written at `.planning/coursework/research/bigdata/silver-stataustria-ods-reader.md`.
- Local files were reviewed first; Context7 was used for pandas ODS IO, Ref was attempted and credit-blocked, and Firecrawl/Tavily were used for odfpy/Statistik Austria source checks.
- Self-approved implementation plan written at `.planning/coursework/plans/bigdata/gap-042-stataustria-ods-reader.md`.

Changed:
- Added core dependency `odfpy>=1.4,<2`.
- Added `load_stataustria_frame` and ODS layout helpers for freight report-year totals and rolling-stock year-column blocks.
- Registered `statistik_austria` in `_SOURCES`.
- Added deterministic German label rules for the emitted Statistik Austria total labels.
- Added generated-ODS unit tests plus a `frames_from_bronze` routing integration test.
- Synced `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, and `docs/STATE_AND_ROADMAP.md`.

Evidence:
- RED: `python -m pytest -q tests/test_silver_stats_stataustria.py` failed before implementation with missing loader/routing.
- `python -m pip install -e ".[test]"` passed; `odfpy==1.4.1` satisfied the new dependency.
- `python -m pytest -q tests/test_silver_stats_stataustria.py` -> 5 passed.
- `python -m pytest -q -m unit` -> 175 passed, 31 deselected.
- `python -m pytest -q` -> 200 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF normalization warnings only.

Next:
- Commit, push `impl/gap-042`, open the PR, and verify mergeability.
## 2026-06-25 - GAP-035 Deterministic Silver Language ID

Status: done

Research:
- Required `research-orchestrator` record written at `.planning/coursework/research/bigdata/silver-language-id.md`.
- Local-first review found the spec was stale: GAP-050 had already removed `language` from `_JSON_SCHEMA`, but few-shot examples and validation still let language come from model output.
- Routed docs used Context7, Tavily, and Firecrawl. Chosen dependency: `lingua-language-detector==2.2.0`, restricted to EN/DE/HU for this project.

Changed:
- Added `src/railway_lakehouse/silver/language_id.py`.
- Wired deterministic language detection into RSS/article extraction and GDELT passthrough before validation.
- Added language-id identity to the news extraction cache digest.
- Updated `validate_news_feature()` to prioritize explicit deterministic language over legacy raw model fields.
- Removed language from the LLM prompt examples/rules and updated fake LLM test payloads.
- Synced `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/STATE_AND_ROADMAP.md`, `docs/SPEC_NEWS_PREPROCESSING.md`, and `README.md`.

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
- Continue Wave 6 with GAP-034 sentiment and GAP-031/GAP-038 language-routed news follow-ups.

## 2026-06-25 - GAP-050 LLM Pipeline Engineering

Status: done

Review update:
- PR #29 request-changes fixes are included: production/live news paths now call `run_extraction_pipeline(..., warm_up=True, manifest_path=...)`, persist the typed failure sidecar, and surface artifact paths.
- GDELT passthrough cache keys now include all GKG/source annotations used in the deterministic feature.
- `max_attempts < 1` now raises `ValueError` instead of allowing zero-attempt accounting gaps.

Research:
- Required note written at `.planning/coursework/research/bigdata/llm-pipeline-engineering-gap050.md`.
- Used `research-orchestrator` with local files first and Context7 for Ollama, LangChain, and Qwen docs.
- Used `prompt-master`, `senior-prompt-engineer`, and ship-it workflow discipline with a repo-local approved plan at `.planning/coursework/plans/bigdata/gap-050-llm-pipeline-engineering.md`.

Changed:
- Rebuilt the Silver news prompt around the narrowed LLM-owned fields.
- Added `NEWS_EXTRACTION_PROMPT_VERSION`, `num_ctx=4096`, keep-alive/num-batch config, digest invalidation, sequential runner, retries/backoff, raw failure capture, optional Ollama lifecycle hooks, and run-manifest metrics.
- Added unit/integration coverage and `docs/LLM_EXTRACTION_DESIGN.md`.
- Synced `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, and `docs/INDEX.md`.
- Hardened Spark tests so the literal full-suite command skips Spark on native Windows when `JAVA_HOME` is absent instead of hanging.

Evidence:
- `python -m pytest -q tests/test_silver_news_extract_prompt.py tests/test_silver_news_wide_contract.py tests/test_silver_news_extraction_e2e.py tests/test_pipeline_gaps.py` -> 35 passed.
- `python -m pytest -q -m unit tests/test_silver_news_extract_prompt.py` -> 6 passed.
- `python -m pytest -q -m integration tests/test_silver_news_extraction_e2e.py` -> 4 passed.
- `python -m pytest -q` -> 194 passed, 6 skipped.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q -m spark` -> 3 passed, 3 skipped.
- `python -m compileall -q src tests` -> passed.

Next:
- Run GAP-033 live extraction with the GAP-050 runner; commit only bounded evidence artifacts, not raw Bronze bytes.

## 2026-06-24 - GAP-019 Deployable Bronze Scheduler

Status: closed — implemented by the Codex agent (exec sandbox could not spawn processes; recorded honestly below); orchestrator verified (`pytest -q -m unit tests/test_bronze_scheduler.py` → 4 passed; full `pytest -q` → 127 passed, 1 skipped; `compileall` clean), rebased on GAP-013, and shipped via PR.

Research:
- Updated `.planning/coursework/research/bigdata/gap019-deployable-scheduler-spec-2026-06-24.md` with local file findings plus primary-source checks for `schedule`, Docker Compose service dependencies, and systemd timers.
- Approved implementation plan: `.planning/coursework/plans/bigdata/gap-019-deployable-scheduler.md`.

Changed:
- Added deterministic scheduler tests in `tests/test_bronze_scheduler.py`.
- Updated `src/railway_lakehouse/bronze/run.py` with S3 preflight, fail-soft `_run_batch`, scheduler manifests, and `_tick()`.
- Added `Dockerfile` and a Compose `scheduler` service.
- Added scheduler operations/runbook docs in `README.md` and `docs/OPERATIONS.md`.
- Synced `docs/INDEX.md`, `docs/CODEMAP.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, and `docs/PROGRESS_LOG.md`.

Evidence:
- `python -m pytest -q -m unit tests/test_bronze_scheduler.py` could not start in this session: spawning `python` fails with `windows sandbox: runner error: CreateProcessAsUserW failed: 5`.
- Serena shell execution was also rejected before running; no test, compileall, git, gh, or PR result is claimed.

Next:
- Resume from verification: run the GAP-019 unit test, full pytest, compileall, `git diff --check`, then commit/push/open the PR.

## 2026-06-24 - GAP-011 Report And Presentation Drafts

Status: done for implementation and local verification; PR handoff pending.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/gap-011-report-presentation.md`.
- Approved implementation plan:
  `.planning/coursework/plans/bigdata/gap-011-report-presentation.md`.
- Local files and committed evidence JSON were researched first. No external
  docs were needed because the work quotes repo artifacts rather than new API or
  library behavior.

Changed:
- Added `output/report/REPORT.md` with problem/dataset, architecture,
  proven Gold result, MinIO, Bronze source coverage, Spark evidence, known
  gaps, and Evidence Index.
- Added `output/presentation/PRESENTATION.md` as a slide outline using the same
  cited figures.
- Added `tests/test_report_evidence_links.py`, marked `unit`, to assert
  deliverables exist, cited evidence paths exist, and headline values loaded
  from JSON appear in the report.
- Synced `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`,
  `docs/VERIFICATION.md`, `docs/index.html`, and `docs/PROGRESS_LOG.md`.

Findings:
- GAP-009 Spark evidence already exists in this checkout, so the report cites
  `output/evidence/spark/manifest.json` instead of claiming Spark is unbuilt.
- No raw Bronze paths are cited; the documents cite committed manifests,
  counts, crosswalk, samples, and Spark/MinIO evidence only.

Evidence:
- RED: `python -m pytest -q tests/test_report_evidence_links.py` failed with
  3 expected failures before the deliverables existed.
- GREEN: `python -m pytest -q tests/test_report_evidence_links.py` -> 3 passed.
- Evidence path scan -> `MISSING EVIDENCE PATHS: []`.
- `python -m pytest -q -m "not spark"` -> 107 passed, 2 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q -m spark` -> 1 passed, 1 skipped, 107 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 108 passed, 1 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with CRLF warnings only.

Boundary:
- No live collectors, MinIO/Ollama/Spark evidence regeneration, raw Bronze
  movement, or pipeline behavior changes were made for GAP-011.

Next:
- Commit, push `impl/gap-011`, open the PR against `main`, and verify mergeability.

## 2026-06-24 - GAP-011 PR #20 Review Fixes

Status: done.

Research:
- Updated `.planning/coursework/research/bigdata/gap-011-report-presentation.md`
  after verifying both review findings against local files.

Changed:
- Reworded `output/report/REPORT.md` so the problem/dataset section states
  that current reportable Gold is stats-only and news features remain pending
  GAP-006.
- Added exact source-derived `key=value` headline tokens to
  `output/presentation/PRESENTATION.md`.
- Extended `tests/test_report_evidence_links.py` to build exact `key=value`
  tokens from committed evidence JSON and require them in both the report and
  presentation.

Evidence:
- RED: `python -m pytest -q tests/test_report_evidence_links.py` failed after
  the stricter checker was added.
- GREEN: `python -m pytest -q tests/test_report_evidence_links.py` -> 3 passed.
- `python -m pytest -q -m unit` -> 93 passed, 16 deselected.

Next:
- Commit, push, and confirm PR #20 mergeability.

## 2026-06-24 - GAP-018 Dependency Bounds And Lockfile

Status: done for implementation and local verification.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/gap-018-dependency-bounds-lockfile-2026-06-24.md`.
- Local files reviewed first: `AGENTS.md`, `pyproject.toml`, `.gitignore`,
  `tests/test_infra_minio.py`, README/verification/gap/task/dashboard docs,
  `docs/PROGRESS_LOG.md`, and this progress log.
- `research-orchestrator` was used. Ref was credit-blocked; Context7 supplied
  Python 3.14 `tomllib.load` and pip constraints documentation.

Changed:
- Bounded `requires-python`, pandas, pyarrow, requests, and schedule in
  `pyproject.toml` while preserving the four exact S3 pins and leaving `[spark]`
  untouched for GAP-017.
- Added root `constraints.txt` for the active Python 3.14 runtime/test closure.
- Added offline unit guard `tests/test_env_versions.py`.
- Updated Quickstart, verification docs, GAP register, roadmap, task contract,
  dashboard, and the implementation plan/research artifacts.

Evidence:
- Guard test RED before implementation: 2 failed, 3 passed.
- Guard test GREEN: 5 passed.
- Full suite: 92 passed.
- Unit marker: 82 passed, 10 deselected.
- Integration marker: 10 passed, 82 deselected.
- Compileall: `python -m compileall -q src tests` exited 0.
- Constrained dry-run: `python -m pip install --dry-run -e ".[test]" -c constraints.txt`
  kept pandas 3.0.3 and pyarrow 24.0.0.
- `git diff --check` exited 0.

Boundary:
- No live collectors, MinIO/Ollama/Spark jobs, raw Bronze writes, or data-layer
  behavior changes were used for this ops task.

Next:
- Push `impl/gap-018`, open the PR against `main`, and confirm mergeability.

## 2026-06-23 - State Analysis, Inventory, And Spark Roadmap

Status: done for read-only analysis/planning; no source code changed.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/state-analysis-spark-roadmap-2026-06-23.md`.
- `research-orchestrator` was used. Routed MCP providers: Context7, Tavily, Exa,
  Ref (some Ref pages credit-limited).
- Local files read first: `AGENTS.md`, `README.md`, `TASK.md`, `WIRING.md`,
  `docs/GAP_REGISTER.md`, `docs/NEXT_SESSION_HANDOFF.md`, `docs/ARCHITECTURE.md`,
  `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/PIPELINE.md`,
  `docs/VERIFICATION.md`, `.planning/COURSEWORK_PROGRESS.md`, all Bronze source
  adapters, Silver stats/news parsers, `pipeline.py`, `gold/build.py`/`run.py`,
  and committed `output/evidence/**` manifests.

Findings:
- Project sits at the end of the storage-boundary phase / start of the Spark
  phase. Bronze landing operational (4 scheduled sources; KSH/StatAustria/UIC
  live-proven as raw bytes but not scheduled, GAP-005). Silver normalizes
  World Bank + Eurostat stats and RSS + GDELT news IN-MEMORY only; no persisted
  Silver writer (GAP-006). Gold matrix builder works + writes Parquet but only
  from a 4-row fixture; `gold/run.py` storage-load is a stub (GAP-007).
- Only end-to-end artifact: `output/evidence/fixture-e2e/railway_ml.parquet`
  (4 rows x 3 cols, news skipped). Live evidence proves raw Bronze landing only.
- Task list 9-12: #9 stats-parsers 2/5 (Eurostat+World Bank done; KSH XLSX /
  StatAustria ODS / UIC PDF readers missing; list was stale on UIC=XLS and
  StatAustria=JSON/CSV). #10 news-parsers 3/3 (LLM step mocked in tests). #11
  gold feature-matrix done on fixture. #12 spark/evidence-job 0/3, not started.
- Engine recommendation: Apache Spark/PySpark (rubric-aligned), Delta Lake on
  Parquet, pinned Spark 3.5.x/Scala 2.12/delta-spark 3.2.x/hadoop-aws 3.3.4/JDK
  17 + winutils on Windows; DuckDB/Polars as EDA/benchmark sidecar. Raise real
  volume via the existing `past_recordings` GDELT backfill so Spark is justified.

Evidence:
- No source edits, tests, live collectors, MinIO, Ollama, or Spark runs were
  executed for this analysis. Produced a visual status/roadmap dashboard
  (Artifact) plus the research note above.

Next:
- Critical path: GAP-006 (min Silver persist) -> GAP-007 (Gold<-Silver) ->
  GAP-009 (Spark evidence) -> GAP-011 (report). GAP-010 live + GDELT volume
  backfill run in parallel.

## 2026-06-23 - PR #9 And #10 Review

Status: done for read-only review.

Research:
- Required local research note: `.planning/coursework/research/bigdata/pr9-pr10-review-2026-06-23.md`.
- Local files read first: `AGENTS.md`, `README.md`, `TASK.md`, `docs/PROGRESS_LOG.md`, `docs/GAP_REGISTER.md`, `docs/WORKSTREAMS.md`, `docs/DATA_CONTRACTS.md`, `docs/ARCHITECTURE.md`, `docs/SILVER_DESIGN.md`, PR metadata, PR diffs, and changed source/tests.
- `ship-it:ship-pr` was used for each same-repo PR. No external docs were needed.

Evidence:
- PR #9 is open, same-repo, `DIRTY`/`CONFLICTING`; report at `.ship/pr/9/report.md`.
- PR #10 is open, same-repo, `CLEAN`/`MERGEABLE`; report at `.ship/pr/10/report.md`.
- PR #9 branch tests with `PYTHONPATH=src`: targeted Silver tests passed, 8 passed; full branch suite passed, 56 passed and 1 xfailed.
- PR #10 branch tests with `PYTHONPATH=src`: targeted Silver stats tests passed, 11 passed; full branch suite passed, 64 passed.
- Adversarial verification challenged four findings and dropped none.

Findings:
- PR #9 needs conflict resolution and a blank-URL article-id fix before merge.
- PR #10 needs World Bank ISO3-to-project-geo normalization (`AUT -> AT`) and Austria-specific test coverage before merge.
- The PRs are complementary slices of GAP-006, but shared test/docs edits must be reconciled.

Next:
- Fix PR #10 first if taking the lowest-conflict path.
- Rebase PR #9 after the stats/test state is settled.

## 2026-06-21 - Bronze Local Live Check Command

Status: done for bounded local RSS/KSH Bronze command; broader live pipeline evidence remains open.

Research:

- Required local research note: `.planning/coursework/research/bigdata/live-check-command.md`.
- Local files read first: `AGENTS.md`, `docs/PARSER_WORK_LOG.md`, `docs/GAP_REGISTER.md`, `docs/DATA_CONTRACTS.md`, `docs/CODEMAP.md`, `WIRING.md`, and `docs/WORKSTREAMS.md`.
- No external docs were needed because the work used repo-local Bronze contracts and did not make Spark/API claims.

Changed:

- `src/railway_lakehouse/bronze/live_check.py`
- `tests/test_bronze_live_check.py`
- `docs/PARSER_WORK_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `output/evidence/live-bronze/manifest.json`

Generated local evidence:

- `output/evidence/live-bronze/bronze/**` during the recorded command run; raw files remain local/ignored and are summarized by the committed manifest.

Evidence:

- `python -m pytest -q tests\test_bronze_live_check.py` passed: 3 passed.
- `python -m pytest -q` passed: 18 passed, 1 xfailed.
- `python -m railway_lakehouse.bronze.live_check --sources rss,ksh --out output/evidence/live-bronze --max-artifacts 5` passed and wrote `output/evidence/live-bronze/manifest.json`.
- Live command output: `artifact_count=8`, `byte_count=264670`; RSS passed with 5 artifacts and 0 failures; KSH passed with 3 artifacts and 0 failures.
- Future reruns under the same output root create a run-specific subdirectory instead of overwriting the committed evidence manifest.

Next:

- Keep raw live artifacts local unless the course submission explicitly needs them committed.
- Extend command coverage only after source-specific fixes are verified.

## 2026-06-22 - PR Review And Parser Merges

Status: done.

Research:

- Required local research note: `.planning/coursework/research/bigdata/pr-review-merge-2026-06-22.md`.
- Local files read first: `README.md`, `TASK.md`, `docs/INDEX.md`, `docs/CODEMAP.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACTS.md`, `docs/WORKSTREAMS.md`, `docs/AGENTIC_WORKFLOW.md`, `docs/VERIFICATION.md`, `docs/ORGANIZATION_PLAN.md`, `docs/PROGRESS_LOG.md`, `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, and PR branch diffs.
- No Linear task was used; PR intent was reconstructed from code, docs, tests, and live probe evidence.

Changed:

- `.planning/coursework/research/bigdata/pr-review-merge-2026-06-22.md`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/bronze/sources/eurostat.py`
- `src/railway_lakehouse/bronze/sources/worldbank.py`
- `tests/test_bronze_live_check.py`
- `tests/test_bronze_characterization.py`
- `docs/PARSER_WORK_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`

Evidence:

- PR #1 reviewed, fixed, verified, and merged at `226df6fb8e7a8482c8046bba3f499662e2a2ca13`.
- PR #2 reviewed, fixed, verified, and merged at `4f0f17e337a25a7cd646203848e5f480e05a38d3`.
- PR #3 reviewed, fixed, verified, and merged at `20c86e5521e26ff8ff978f4bc471ab9e9ce6f476`.
- `python -m pytest -q tests\test_bronze_live_check.py` passed: 8 passed.
- `python -m pytest -q tests\test_bronze_characterization.py` passed: 11 passed.
- `python -m pytest -q` passed after all merges: 29 passed, 1 xfailed.
- `python -m compileall .` passed after all merges.
- `gh pr list --state open --json number,title,headRefName,author,isDraft,mergeStateStatus,reviewDecision,url` returned an empty list.

Next:

- Keep the GAP-004 xfail in place until fixture-backed Bronze storage reads are implemented and verified.

## 2026-06-22 - Dataset Readiness Estimate

Status: done for planning/status answer; no source code changed.

Research:

- Required local research note: `.planning/coursework/research/bigdata/dataset-readiness-2026-06-22.md`.
- Local files read first: `docs/PARSER_WORK_LOG.md`, `docs/GAP_REGISTER.md`, `docs/TEST_FIRST_INTEGRATION_PLAN.md`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`, `README.md`, `TASK.md`, and source entrypoints.
- No external docs were needed because this estimate is based on current repo evidence, not new API behavior.

Evidence:

- Current proven Bronze sources: RSS, KSH, Eurostat bounded dataset probe, and World Bank bounded indicator probe.
- Current blockers: GDELT 429 handling, Statistik Austria empty 200 response, UIC 404/access resolution, GAP-004 pipeline Bronze reads, GAP-006 Silver persistence, GAP-007 Gold storage loading, and GAP-009 Spark job.
- `docs/PARSER_WORK_LOG.md` now records target milestones for MVP Bronze, first Gold Parquet, Spark evidence, and full parser hardening.

Next:

- Produce a minimal analysis-ready dataset from proven sources first; treat full parser completion as the next reliability milestone.

## 2026-06-22 - KSH STADAT Seed Correction PR

Status: done for KSH Bronze seed correction; broader pipeline remains open.

Research:

- Required local research note: `.planning/coursework/research/bigdata/ksh-stadat-seeds-2026-06-22.md`.
- Local files read first: `README.md`, `TASK.md`, `docs/PROGRESS_LOG.md`, `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, `docs/CODEMAP.md`, `docs/DATA_CONTRACTS.md`, `docs/WORKSTREAMS.md`, `docs/VERIFICATION.md`, `docs/ARCHITECTURE.md`, `WIRING.md`, `.planning/COURSEWORK_PROGRESS.md`, `src/railway_lakehouse/bronze/sources/ksh.py`, `src/railway_lakehouse/bronze/live_check.py`, and related tests.
- No Linear ticket was used; intent came from the supplied patch plus repo docs/code.
- No external docs were needed because the work used current repo contracts and a bounded current-code live check.

Changed:

- Corrected KSH STADAT seed metadata in `src/railway_lakehouse/bronze/sources/ksh.py`.
- Updated local KSH live-check collection in `src/railway_lakehouse/bronze/live_check.py`.
- Added unit coverage in `tests/test_bronze_characterization.py` and `tests/test_bronze_live_check.py`.
- Updated roadmap/status docs and committed `output/evidence/ksh-live-check-2026-06-22/manifest.json`.

Evidence:

- `python -m pytest -q tests\test_bronze_characterization.py` passed: 15 passed.
- `python -m pytest -q tests\test_bronze_live_check.py` passed: 8 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/runtime/ksh-live-check-validation --max-artifacts 6 --timeout-seconds 30` passed with `artifact_count=6`, `byte_count=92509`, KSH `passed`, and 0 failures.
- `python -m pytest -q` passed: 33 passed, 1 xfailed for documented GAP-004.
- `python -m compileall .` passed.
- `python -m json.tool output\evidence\ksh-live-check-2026-06-22\manifest.json` passed.

Next:

- KSH still needs scheduler wiring under GAP-005.
- Silver stats still needs a deterministic KSH XLSX parser before KSH contributes to Gold.

## 2026-06-22 - PR 4 Review Fixes

Status: done for review fixes; PR push/green/merge remains.

Research:

- Required local research note: `.planning/coursework/research/bigdata/pr4-review-fixes-2026-06-22.md`.
- Local files read first: `docs/PARSER_WORK_LOG.md`, `docs/VERIFICATION.md`, `docs/GAP_REGISTER.md`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`, `.planning/coursework/research/bigdata/ksh-stadat-seeds-2026-06-22.md`, `src/railway_lakehouse/bronze/sources/ksh.py`, `src/railway_lakehouse/bronze/live_check.py`, and related tests.
- No external docs were needed because the fixes were based on local PR review artifacts, repo code, and repo documentation.

Changed:

- Separated historical pre-correction KSH evidence from current KSH evidence in `docs/PARSER_WORK_LOG.md`.
- Added committed current-code KSH live-check manifest `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`.
- Strengthened KSH XLSX validation to inspect the workbook ZIP container.
- Added deterministic integration coverage in `tests/test_bronze_live_check_integration.py`.
- Updated verification, gap, progress, and research docs.

Evidence:

- `python -m pytest -q tests\test_bronze_characterization.py tests\test_bronze_live_check.py tests\test_bronze_live_check_integration.py` passed: 24 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/ksh-live-check-2026-06-22-current --max-artifacts 6 --timeout-seconds 30` passed with `artifact_count=6`, `byte_count=92509`, KSH `passed`, and 0 failures.
- `python -m pytest -q -m integration` passed: 1 passed, 33 deselected, 1 xfailed for documented GAP-004.
- `python -m pytest -q` passed: 34 passed, 1 xfailed for documented GAP-004.
- `python -m compileall src tests` passed.
- `python -m json.tool output\evidence\ksh-live-check-2026-06-22-current\manifest.json` passed.

Next:

- Push PR #4, confirm GitHub has no failing checks, and merge.
- KSH still needs scheduler wiring under GAP-005.

## 2026-06-22 - KSH STADAT Task Status Docs

Status: done for doc clarification; no runtime behavior changed.

Research:

- Required local research note: `.planning/coursework/research/bigdata/ksh-stadat-doc-status-2026-06-22.md`.
- Local files read first: `docs/PARSER_WORK_LOG.md`, `docs/WORKSTREAMS.md`, `docs/GAP_REGISTER.md`, `docs/CODEMAP.md`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`, prior KSH research notes, and `WIRING.md`.
- No external docs were needed because this change only reconciles repo status documentation.

Changed:

- Added an explicit `parser/ksh-stadat` task-status section to `docs/PARSER_WORK_LOG.md`.
- Marked KSH Bronze source work complete while keeping GAP-005 scheduler wiring and GAP-006 Silver parser/tests open.
- Updated `docs/WORKSTREAMS.md`, `docs/GAP_REGISTER.md`, and `docs/CODEMAP.md` to reflect the same boundary.

Evidence:

- Local status search used `rg` across `README.md`, `TASK.md`, `docs/`, `.planning/`, and `WIRING.md`.
- `git diff --check` passed.

Next:

- Push the documentation update directly to `main`.
- Implement KSH scheduler wiring under GAP-005.
- Implement KSH Silver XLSX parser/tests under GAP-006.

## 2026-06-22 - Undone Task Triage

Status: done for planning/status answer; no source behavior changed.

Research:

- Required local research note: `.planning/coursework/research/bigdata/undone-task-triage-2026-06-22.md`.
- Local files read first: `README.md`, `TASK.md`, `docs/PROGRESS_LOG.md`, `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, `docs/WORKSTREAMS.md`, `docs/TEST_FIRST_INTEGRATION_PLAN.md`, `.planning/COURSEWORK_PROGRESS.md`, relevant Bronze source modules, `src/railway_lakehouse/bronze/live_check.py`, `src/railway_lakehouse/bronze/run.py`, Silver/Gold modules, and Bronze tests.
- External primary-source checks covered GDELT DOC/rate-limit context, Statistik Austria Open.data/catalog/formats, and UIC RAILISA/resources.

Findings:

- Missing from the supplied list: fixture-backed Bronze reads, scheduler wiring, Silver persistence/output contracts, Gold load/write evidence, Spark evidence, report/presentation work, and live-check collector support beyond RSS/KSH.
- Highest-leverage next work is a minimal vertical slice from already proven sources before waiting for all parser hardening.
- Parser hardening tasks can run in parallel, but PRs will collide around `docs/PARSER_WORK_LOG.md`, `docs/GAP_REGISTER.md`, `tests/test_bronze_characterization.py`, and `tests/test_bronze_live_check.py`.

Evidence:

- No tests, source edits, live collectors, Spark jobs, MinIO, or historical backfills were run for this triage.

Next:

- Take the vertical slice first: GAP-004, minimal GAP-006, GAP-007, then GAP-009.
- Run GDELT, RSS, Statistik Austria, and UIC parser fixes as independent PRs with small doc/test updates.

## 2026-06-22 - GDELT Rate-Limit Handling

Status: done for mocked rate-limit and historical safety coverage; latest bounded recent GDELT live probe failed without artifacts.

Research:

- Required local research note: `.planning/coursework/research/bigdata/gdelt-rate-limit-2026-06-22.md`.
- Local files read first: `README.md`, `TASK.md`, `docs/PROGRESS_LOG.md`, `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, `docs/CODEMAP.md`, `docs/DATA_CONTRACTS.md`, `docs/WORKSTREAMS.md`, `docs/VERIFICATION.md`, `WIRING.md`, `src/railway_lakehouse/bronze/sources/gdelt.py`, `src/railway_lakehouse/bronze/sources/past_recordings.py`, and `tests/test_bronze_characterization.py`.
- External official GDELT pages confirmed DOC 2.0 JSON support and the 200-record documented `MAXRECORDS` bound.

Changed:

- Added `src/railway_lakehouse/bronze/sources/gdelt_common.py` for shared GDELT retry and request-bound helpers.
- Updated recent GDELT ingestion to retry HTTP 429, respect `Retry-After`, use a project user agent, and cap DOC API requests at 200 records.
- Updated historical GDELT DOC/GKG collection with the same retry helper, injectable test hooks, `--dry-run`, and bounded `--max-pages` CLI behavior.
- Added GDELT/past-recordings mocked HTTP tests in `tests/test_bronze_characterization.py`.
- Generated bounded recent GDELT evidence manifest at `output/evidence/gdelt-live-check-2026-06-22/manifest.json`.
- Updated parser, verification, wiring, gap, and progress docs.
- Decision: recent GDELT is marked not working for live Bronze collection now,
  but it does not block the Bronze MVP because other sources have usable
  bounded evidence.

Evidence:

- `python -m pytest -q tests\test_bronze_characterization.py -k "gdelt or past_recordings"` passed: 6 passed, 17 deselected.
- `python -m pytest -q tests\test_bronze_characterization.py` passed: 23 passed.
- Bounded recent GDELT live retry probe wrote `output/evidence/gdelt-live-check-2026-06-22/manifest.json`: `status=failed`, `artifact_count=0`, `byte_count=0`, with failures for HU HTTP 429 and AT `RemoteDisconnected`.
- Decision: GDELT remains not working for live Bronze collection now, but it does not block the MVP Bronze/Gold/Spark path because RSS can supply first news evidence and proven stats sources can supply the first dataset. It is not a Silver blocker until raw GDELT ArtList JSON exists.
- `python -m pytest -q` passed: 43 passed, 1 xfailed for documented GAP-004.
- `python -m compileall src tests` passed.
- `git diff --check` passed.

Next:

- Keep GDELT as fix-if-time parser hardening unless the report specifically needs GDELT news coverage.
- Keep historical GDELT backfills behind explicit `--max-pages` / evidence-plan bounds.

## 2026-06-22 - UIC Refresh Public Publications

Status: done for `parser/uic-refresh` public-publication Bronze scope; subscribed RAILISA CSV/Excel/API access remains blocked on credentials/subscription.

Research:

- Required local research note: `.planning/coursework/research/bigdata/uic-refresh-2026-06-22.md`.
- Local files read first: `docs/GAP_REGISTER.md`, `docs/CODEMAP.md`, `docs/DATA_CONTRACTS.md`, `docs/PARSER_WORK_LOG.md`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`, `WIRING.md`, `src/railway_lakehouse/bronze/sources/uic.py`, `src/railway_lakehouse/bronze/live_check.py`, and related Bronze tests.
- External primary-source checks covered UIC statistics, RAILISA list/download, RAILISA resources, and the RAILISA API guide.

Changed:

- Refreshed `src/railway_lakehouse/bronze/sources/uic.py` from stale public XLS seeds to current public RAILISA PDF resources.
- Added UIC PDF validation and source-level mocked tests.
- Added explicit `uic` support to `src/railway_lakehouse/bronze/live_check.py` and mocked live-check coverage.
- Generated bounded UIC evidence manifest at `output/evidence/uic-live-check-2026-06-22/manifest.json`.
- Updated parser, gap, verification, code map, wiring, and progress docs.
- Decision: UIC public PDF collection is complete for Bronze; extracting facts
  from those PDFs belongs to Silver parser work.

Evidence:

- Direct probe: UIC `help_resource/?id=12` and `help_resource/?id=14` returned HTTP 200 PDF bytes; stale XLS seed returned HTTP 404 HTML.
- `python -m pytest -q tests\test_bronze_live_check.py` passed: 9 passed.
- UIC-specific source/live-check tests passed: 4 passed.
- `python -m railway_lakehouse.bronze.live_check --sources uic --out output/evidence/uic-live-check-2026-06-22 --max-artifacts 2 --timeout-seconds 30` passed with `artifact_count=2`, `byte_count=2109240`, and 0 failures.
- `python -m compileall .` passed.
- `python -m pytest -q` passed: 43 passed, 1 xfailed for documented GAP-004.

Next:

- Decide whether scheduled Bronze stats should include UIC public PDFs before closing the UIC part of GAP-005.
- Plan Silver UIC parsing against public PDF evidence or subscribed RAILISA CSV/Excel exports if credentials become available.

## 2026-06-22 - PR #5-#7 Review, Fixes, And Merge

Status: done; all open PRs merged.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/pr5-pr7-review-merge-2026-06-22.md`.
- Local files read first: `AGENTS.md`, `README.md`, `TASK.md`,
  `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`,
  `docs/CODEMAP.md`, `docs/DATA_CONTRACTS.md`, `docs/VERIFICATION.md`,
  PR metadata, and PR branch diffs.
- `ship-it:ship-pr` was used for PR #5; PR #6 and PR #7 were fork PRs and
  were reviewed with fallback read-only subagents after `ship-pr` halted.

Changed:
- Invited `alyonaprikhodko` and `Soomphik` as write collaborators.
- Fixed and merged PR #5, PR #6, and PR #7.
- Added this progress entry and the session research note.

Evidence:
- PR #5 merged at `53287a11bf8b91160b2f1af36c9c5bb6c50e5792`.
- PR #6 merged at `3fa4c899247a3c0c058f133a3a1e80345d3fe18c`.
- PR #7 merged at `8f69200b151a2989c9f7f5d665e61f6eeb81deb7`.
- `gh pr list --state open --json number,title,url,isDraft,mergeStateStatus`
  returned `[]`.
- `python -m pytest -q` passed on merged `main`: 53 passed, 1 xfailed for
  documented GAP-004.
- `python -m compileall src tests` passed.
- `python -m json.tool` passed for all four merged parser evidence manifests.
- `git diff --check` passed.

Next:
- Continue with GAP-004 fixture-backed Bronze reads, then minimal Silver/Gold
  persistence and Spark evidence.

## 2026-06-22 - Current State And Next Plan

Status: done for planning/status review; no source behavior changed.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/current-state-next-plan-2026-06-22.md`.
- Local files read first: `README.md`, `docs/GAP_REGISTER.md`,
  `docs/PARSER_WORK_LOG.md`, `docs/WORKSTREAMS.md`, `docs/PROGRESS_LOG.md`,
  `.planning/COURSEWORK_PROGRESS.md`, `pyproject.toml`, pipeline, Bronze,
  Silver, Gold, and related tests.
- External source checked: Apache Spark official Parquet docs for the future
  Gold Parquet -> Spark evidence path.

Findings:
- Local `main` is current at `2dc5091` and contains PR #5, PR #6, and PR #7.
- The proposed stage plan is mostly correct, but Stage A should emphasize
  fixture-backed inputs and persistence contracts, not rewriting already-tested
  Gold/Silver primitives.
- Parallel Stage A branches should be: RSS article records, World Bank/Eurostat
  `StatFact` fixtures, and GAP-004 no-network Bronze -> Silver -> Gold wiring.
- Spark remains blocked on Gold Parquet evidence; report/presentation claims
  remain blocked on generated outputs.

Evidence:
- `python -m pytest -q` passed: 53 passed, 1 xfailed for GAP-004.
- `python -m compileall src tests` passed.
- No live collectors, MinIO, Ollama, Spark jobs, or long historical backfills were run.

Next:
- Start `pipeline/fixture-e2e-gap004` immediately.
- Start `silver/news-rss-article-records` and `silver/stats-worldbank-eurostat`
  in parallel.
- Start KSH XLSX parsing after the first stats parser branch establishes shared
  fixture conventions.

## 2026-06-22 - Owner Recommendation Follow-Up

Status: done for planning clarification; no source behavior changed.

Research:
- Local files reviewed: `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`,
  `.planning/coursework/research/bigdata/current-state-next-plan-2026-06-22.md`,
  plus `rg` over docs/source/tests for GAP-004, GAP-006, GAP-007, RSS, World
  Bank, Eurostat, Gold Parquet, and Spark.
- No new external docs were needed because this answer assigns ownership based
  on current repo gaps and previously recorded evidence.

Findings:
- The user should own `pipeline/fixture-e2e-gap004` because it is the main
  dependency for closing the first vertical slice.
- Classmates are not blocked from working on Silver parser fixtures in parallel.
- Spark/report/presentation remain blocked on generated Gold Parquet evidence.

Evidence:
- No tests, source edits, live collectors, MinIO, Ollama, Spark jobs, or long
  historical backfills were run for this clarification.

Next:
- Start GAP-004 branch and define the fixture/input-output contract for the
  parallel Silver parser branches.

## 2026-06-22 - GAP-005 Scheduler Decision

Status: done for planning clarification; no source behavior changed.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/gap005-scheduler-decision-2026-06-22.md`.
- Local files reviewed: `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`,
  `src/railway_lakehouse/bronze/run.py`, current planning notes, and `rg`
  search results for GAP-005/scheduler/source-adapter references.
- No new external docs were needed because this is an internal scheduling and
  ownership decision based on current repo state.

Findings:
- Defer GAP-005 from the user's critical path; GAP-004 remains the main owner
  task.
- GAP-005 can run in parallel if assigned to someone else as a narrow
  Bronze-only PR.
- Historical GDELT must not be wired into automatic scheduled runs.

Evidence:
- No source code, tests, live collectors, scheduler, MinIO, Ollama, Spark jobs,
  or long historical backfills were run.

Next:
- Primary owner starts GAP-004.
- Optional parallel owner can wire KSH, Statistik Austria, and UIC public PDFs
  into `bronze/run.py` with mocked unit tests.

## 2026-06-22 - GAP-004 Fixture Pipeline E2E

Status: done for deterministic fixture-backed pipeline reads.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/pipeline-fixture-e2e-gap004-2026-06-22.md`.
- Local files read first: `AGENTS.md`, `README.md`, `docs/GAP_REGISTER.md`,
  `docs/VERIFICATION.md`, `docs/NEXT_SESSION_HANDOFF.md`,
  `docs/DATA_CONTRACTS.md`, `src/railway_lakehouse/pipeline.py`, Bronze
  lander/source files, Silver stats/news modules, Gold build/run modules, and
  related tests.
- No external docs were needed because this change used repo-local contracts and
  did not make new Spark/API claims.

Changed:
- Added fixture-backed Bronze readers and local `--bronze-root` execution to
  `src/railway_lakehouse/pipeline.py`.
- Replaced the GAP-004 strict xfail with integration assertions in
  `tests/test_pipeline_gaps.py`.
- Added stable tiny Bronze fixtures under `tests/fixtures/bronze/**`.
- Generated `output/evidence/fixture-e2e/railway_ml.parquet` and
  `output/evidence/fixture-e2e/crosswalk_cache.json`.
- Updated gap, verification, progress, and current-state docs.
- Fixed the independent reviewer's low-risk `--news 0` edge case with a
  regression test.

Evidence:
- RED before implementation: `python -m pytest -q tests\test_pipeline_gaps.py`
  failed for the expected missing readers/CLI API.
- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 3 passed.
- `python -m pytest -q -m integration` passed: 4 passed, 52 deselected.
- `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction`
  passed and wrote a 4-row, 3-column Gold Parquet artifact plus the
  crosswalk cache.
- `python -m pytest -q` passed: 56 passed.
- `python -m compileall src tests` passed.
- `git diff --check` exited 0.

Boundaries:
- GAP-004 is closed for deterministic fixture-backed Bronze reads.
- Live MinIO, live collectors, Ollama service extraction, Silver persistence,
  Gold storage loading, Spark, report, and presentation evidence remain open.

Next:
- Define minimal Silver/Gold persisted artifact contracts for GAP-006/GAP-007.
- Use the generated Gold Parquet as the handoff input when starting Spark
  evidence work.

## 2026-06-22 - Active Silver Branch Gap Mapping

Status: done for documentation; no source behavior changed.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/active-silver-branch-gap-map-2026-06-22.md`.
- Local files reviewed: `docs/GAP_REGISTER.md`, `docs/WORKSTREAMS.md`,
  `docs/WORK_SPLIT.md`, `docs/NEXT_SESSION_HANDOFF.md`, and
  `docs/DATA_CONTRACTS.md`.
- No external docs were needed because this is repo-local gap ownership mapping.

Findings:
- `silver/news-rss-article-records` is GAP-006, Silver News/RSS article-record
  slice.
- `silver/stats-worldbank-eurostat` is GAP-006, Silver Stats World
  Bank/Eurostat slice.
- Both can feed GAP-010 with bounded live evidence, but neither closes GAP-007
  without Gold storage loading and Gold row/column evidence.

Next:
- Validate teammate PRs against GAP-006 closure criteria.
- Keep GAP-007 as the follow-up integration point after Silver outputs persist.

## 2026-06-22 - Ollama Model Selection

Status: superseded by the later Qwen 3.5 runtime-config decision below.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/ollama-model-selection-2026-06-22.md`.
- Local files reviewed first: `src/railway_lakehouse/silver/config.py`,
  `src/railway_lakehouse/silver/ollama_client.py`,
  `src/railway_lakehouse/silver/stats/merge.py`,
  `src/railway_lakehouse/silver/news/extract.py`,
  `src/railway_lakehouse/pipeline.py`, `docs/SILVER_DESIGN.md`,
  `docs/ARCHITECTURE.md`, and `docs/WORK_SPLIT.md`.
- External docs checked: official Ollama pages for `llama3.1:8b`,
  `qwen3:8b`, `qwen3.5`, `gemma3`, and `gemma4`.

Decision:
- Default Ollama model is now `qwen3:8b`.
- `qwen3.5:9b` is documented as the higher-quality local override when
  6.6 GB model memory is acceptable.
- Gemma is documented as an explicit experiment or low-memory alternative.

Evidence:
- `python -m pytest -q tests\test_silver_characterization.py tests\test_pipeline_gaps.py`
  passed: 8 passed.
- `python -m pytest -q` passed: 56 passed.
- `python -m compileall src tests` passed.
- `git diff --check` exited 0.

Boundary:
- No live Ollama service, model download, live extraction, MinIO, Spark, or
  live collector run was executed for this model-selection update.

Next:
- Record live Ollama model pull/run evidence under `output/evidence/` before
  claiming live extraction quality.

## 2026-06-22 - Qwen 3.5 Ollama Runtime Config

Status: done for MCP-backed model/runtime selection.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/qwen35-ollama-runtime-config-2026-06-22.md`.
- Local files reviewed first: `src/railway_lakehouse/silver/config.py`,
  `src/railway_lakehouse/silver/ollama_client.py`,
  `src/railway_lakehouse/silver/stats/merge.py`,
  `src/railway_lakehouse/silver/news/extract.py`,
  `tests/test_silver_characterization.py`, and `docs/SILVER_DESIGN.md`.
- MCP providers used: Tavily, Exa, and Firecrawl. Ref was attempted but
  credit-blocked.

Decision:
- Default Ollama model is now `qwen3.5:9b-q8_0`.
- `OLLAMA_MODEL=qwen3.5:9b-q4_K_M` is the documented lower-memory fallback.
- Ollama remains the default runtime; vLLM is deferred until the project needs
  high-throughput serving.
- The client now uses `/api/chat`, JSON schema `format`, top-level
  `think: false`, `temperature=0`, `OLLAMA_NUM_CTX=8192`, and
  `OLLAMA_NUM_PREDICT=1024`.

Evidence:
- `python -m pytest -q tests\test_silver_characterization.py` passed:
  7 passed.
- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 3 passed.
- `python -m pytest -q` passed: 58 passed.
- `python -m compileall src tests` passed.
- `git diff --check` exited 0.

Boundary:
- No live Ollama service, model download, live extraction, MinIO, Spark, or
  live collector run was executed for this runtime-config update.

Next:
- Record live Ollama pull/run evidence under `output/evidence/` before claiming
  live Qwen extraction quality.

## 2026-06-22 - PR #8 Review Follow-Up

Status: done; actionable automated-review nits applied.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/pr8-review-followup-2026-06-22.md`.
- Local files reviewed first: PR #8 review comment,
  `src/railway_lakehouse/pipeline.py`, `tests/test_pipeline_gaps.py`,
  `docs/VERIFICATION.md`, `docs/PIPELINE.md`, and `docs/GAP_REGISTER.md`.
- No external docs were needed; this was repo-local review follow-up.

Changed:
- Hardened Bronze path parsing errors.
- Added `--crosswalk-path` and updated evidence commands.
- Normalized missing article bodies, fallback IDs, and flexible dates.
- Updated fixture pipeline tests and docs.

Evidence:
- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 5 passed.
- `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction`
  passed.
- Parquet readback passed: `(4, 3)`.
- `output/evidence/fixture-e2e/crosswalk_cache.json` contains
  `Rail passengers total -> rail_passengers`.
- `python -m pytest -q` passed: 60 passed.
- `python -m pytest -q -m integration` passed: 6 passed, 54 deselected.
- `python -m compileall src tests` passed.

Boundary:
- No live collectors, MinIO service, live Ollama model, Spark job, report, or
  presentation output was executed for this review follow-up.

## 2026-06-23 - PR #9 / PR #10 Rebase Fixes

Status: done; both PR branches pushed and mergeable.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/pr9-pr10-rebase-fixes-2026-06-23.md`.
- Local files reviewed first in both PR worktrees, including Silver stats
  loaders/tests, Silver news parsers/tests, pipeline fixture tests, and the
  prior `.ship/pr/9` and `.ship/pr/10` review reports.
- No external docs were needed; this was local PR repair and verification.

Changed:
- PR #10 local commit `a6e3f8272665f8dbddc2a412f1fa69537c5b660a` fixes
  World Bank country-code normalization so Austria is `AT`, not `AU`.
- PR #9 local commit `d674cbaea034560bd64200cba3a3dd67ff03910c` wires RSS
  XML parser output into the fixture pipeline, adds stable URL-less article
  IDs, and makes the ArticleRecord extraction bridge reusable for RSS/GDELT.
- PR #9 parser tests now live in `tests/test_silver_news_parsers.py`, avoiding
  conflict with PR #10's stats characterization tests.

Evidence:
- PR #10 targeted tests passed: 3 passed.
- PR #10 full suite passed: 66 passed.
- PR #10 `python -m compileall -q src tests` passed and
  `git diff --check origin/main...HEAD` exited 0.
- PR #9 focused parser/pipeline tests passed after red/green repair: 8 passed.
- PR #9 full suite passed: 68 passed.
- PR #9 `python -m compileall -q src tests` passed and
  `git diff --check origin/main...HEAD` exited 0.

Boundary:
- No live collectors, MinIO service, live Ollama model, Spark job, report, or
  presentation output was executed for this PR follow-up.
- Initial remote PR branch update failed from `cul8err`, and the GitHub
  connector write path failed with `Unknown tool({"name":"github_update_file"})`.
  Switching GitHub CLI to `pol3et` allowed the branch pushes, and the active
  account was switched back to `cul8err` afterward.
- GitHub reports PR #10 as `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`.
- GitHub reports PR #9 as `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`.

Next:
- Merge PR #10 and PR #9 when ready, watching normal repository checks if
  branch protection requires them.

## 2026-06-23 - Main Sync And Documentation Refresh For PR #9 / PR #10

Status: done; `main` pushed and PR #9 / PR #10 are marked merged by GitHub.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/main-doc-sync-pr9-pr10-2026-06-23.md`.
- Local files reviewed first: `docs/GAP_REGISTER.md`,
  `docs/WORK_SPLIT.md`, `docs/WORKSTREAMS.md`,
  `docs/NEXT_SESSION_HANDOFF.md`, `docs/PARSER_WORK_LOG.md`,
  `docs/CODEMAP.md`, `docs/VERIFICATION.md`, `README.md`,
  `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`, and PR state
  from `gh pr view`.
- No external docs were needed; this was repository-state documentation sync.

Changed:
- Merged `origin/silver/stats-worldbank-eurostat` into local `main`.
- Merged `origin/silver/news-parsers` into local `main`.
- Updated canonical docs to reflect merged Silver Stats and Silver News
  fixture slices instead of active PR branches.
- Added the current verification result and narrowed remaining GAP-006 work.
- Pushed `main`; remote `origin/main` now matches local
  `09bb9df3d75b7049d11bc051565bf1c15c1b32b7`.
- GitHub reports PR #9 and PR #10 as `MERGED`.

Evidence:
- `python -m pytest -q` passed: 74 passed.
- `python -m compileall -q src tests` passed.
- `git diff --check` exited 0.

Boundary:
- No live collectors, MinIO service, live Ollama model, Spark job, report, or
  presentation output was executed for this documentation sync.

Next:
- Continue with remaining GAP-006 parsers/persistence or GAP-007 Gold loading
  from persisted Silver outputs.

## 2026-06-23 - All PR Ship-PR Review

Status: done for read-only PR review.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/all-pr-ship-pr-review-2026-06-23.md`.
- Local files reviewed first: PR metadata, existing `.ship/pr/*` reports,
  `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/DATA_CONTRACTS.md`,
  `docs/WORKSTREAMS.md`, `docs/VERIFICATION.md`, and PR worktree source/tests.
- User corrected scope to **no Linear**; final analysis uses no Linear evidence.

Findings:
- Current open PRs are #11 and #12; both are same-repo and mergeable by GitHub, but no GitHub checks are configured.
- PR #11 verdict: FAIL. The test suite fails on Windows, and the persistence contract is broader than the implementation.
- PR #12 verdict: FAIL. The code path is reproducible and full tests pass, but evidence/docs need repair before the task can be marked done safely.
- PR #8 verdict: PASS. The merged GAP-004 fixture E2E matches its repo-local intent and passes local checks.
- Cross-repo PRs #2, #3, #6, and #7 are out of scope for `ship-pr` v1.

Evidence:
- Reports written under `.ship/pr/8/`, `.ship/pr/11/`, and `.ship/pr/12/`.
- PR #11 local verification: 1 failed, 79 passed full suite; 9 integration tests passed; compileall and diff-check passed.
- PR #12 local verification: 77 passed full suite; 9 integration tests passed; compileall and diff-check passed; temp live reproduction regenerated 2,139 x 3 Gold output.
- PR #8 local verification: 60 passed full suite; compileall and diff-check passed.

Boundary:
- No PR comments, reviews, Linear writes/search-derived intent, MinIO, Ollama, Spark, report, or presentation outputs were performed.

Next:
- Repair PR #11 and PR #12 before merge.

## 2026-06-23 - Open PR Fix, Dashboard Rebase, And Merge

Status: done; all currently open PRs are merged.

Research:
- Required local research note updated:
  `.planning/coursework/research/bigdata/all-pr-ship-pr-review-2026-06-23.md`.
- Local files reviewed first: PR #11/#12 reports, PR worktrees, updated
  `AGENTS.md`, dashboard workflow/template, `docs/index.html`,
  `docs/TASKS.md`, `docs/GAP_REGISTER.md`, `docs/VERIFICATION.md`,
  `README.md`, and `docs/STATE_AND_ROADMAP.md`.
- No Linear context was used.

Changed:
- Fixed and force-with-lease pushed `silver/persist-outputs`.
- Fixed, rebased after #11, and force-with-lease pushed
  `bronze/local-stats-landing`.
- Synced both PRs with the new dashboard rule by updating `docs/TASKS.md` and
  `docs/index.html`.
- Updated local research/progress logs.

Findings:
- PR #11 was about local Silver Parquet persistence. Its blockers were a
  Windows path test, empty-news Parquet physical schema drift, and overbroad
  docs around same-day history, MinIO/S3, and news failure accounting.
- PR #12 was about bounded Eurostat/World Bank local Bronze landing and first
  real stats-only Gold evidence. Its blockers were undocumented counts
  generation, clean-checkout raw Bronze reproduction, Eurostat overclaiming,
  and stale roadmap/dashboard status.
- Final dashboard state: Silver local Parquet persistence done; local stats
  Bronze landing and first real stats-only Gold done; Gold load from persisted
  Silver, MinIO/S3 writes, news failure accounting, Spark, and report remain.

Evidence:
- PR #11: focused Silver persistence tests passed with 6 passed; full suite
  passed with 80 passed; compileall and diff-check passed; GitHub dashboard
  reminder passed.
- PR #12 after rebasing on merged #11: full suite passed with 83 passed;
  integration marker suite passed with 10 passed, 73 deselected; compileall,
  diff-check, and committed evidence JSON validation passed.
- Bounded temp reproduction for #12 landed 4 Eurostat/World Bank artifacts /
  14,996,995 bytes and regenerated 2,139 x 3 Gold counts under
  `output/runtime/pr12-reverify/`.
- PR #11 merged at `9489aa737412474ffcc377bec0d48ebb0c916595`.
- PR #12 merged at `4ae2984f5807b87a07fa994c5dfdedfada2638a0`.
- `gh pr list --state open` returned `[]`.

Boundary:
- No MinIO, Ollama, Spark, report, or presentation output was executed.

Next:
- Start GAP-007: wire `gold/run.py` to load persisted Silver and record Gold
  counts, then proceed to Spark evidence.

## 2026-06-23 - PR #13 Rebase, Dashboard Sync, And Merge

Status: done; PR #13 is fixed, rebased, pushed, and merged.

Research:
- Required local research note created:
  `.planning/coursework/research/bigdata/pr13-minio-storage-review-2026-06-23.md`.
- Local files reviewed first: PR metadata, `AGENTS.md`, dashboard workflow/template,
  `README.md`, `docker-compose.yml`, `.env.example`, `scripts/minio_smoke.py`,
  `tests/test_infra_minio.py`, `output/evidence/minio-smoke/manifest.json`,
  `docs/TASKS.md`, `docs/index.html`, `docs/VERIFICATION.md`,
  `docs/STATE_AND_ROADMAP.md`, `docs/GAP_REGISTER.md`, and relevant
  Bronze/Silver config/storage code.
- No Linear context was used.

Findings:
- No Linear context was used.
- "Integration blocked" split into two issues: deterministic pytest integration
  was not blocked and passed locally; live Docker/MinIO smoke was blocked by the
  local Docker Desktop backend.
- PR #13 implements a local MinIO object-store smoke for GAP-010, but does not
  wire full Bronze/Silver/Gold through MinIO.
- PR #13 was rebased onto current `origin/main`, fixed for dashboard/docs
  consistency, and merged.
- Fixed `.env` handling so `scripts/minio_smoke.py` loads `.env` before
  importing Bronze/Silver config constants.
- Docker Desktop could not start its Linux engine in this shell:
  `backend.error.json` reports `Access is denied` opening
  `\\.\pipe\dockerBackendApiServer`, which Docker says usually means another
  Windows user/session already started Docker Desktop.

Evidence:
- PR #13 branch head after rebase/fix:
  `3548abbc4379f1535d45e76361b05ad840fa878c`.
- `tests/test_infra_minio.py`: 4 passed.
- Integration marker suite: 10 passed, 77 deselected.
- Full suite: 87 passed.
- Compileall: passed.
- `git diff --check origin/main...HEAD`: passed before push.
- `gh pr checks 13`: `remind` passed after push.
- GitHub reported PR #13 `MERGEABLE` / `CLEAN` before merge.
- PR #13 merged at `ad45a4ffc8689da159f67c533fd4eea8d093c082`.
- Post-merge local `main` verification: full suite passed with 87 passed;
  integration marker suite passed with 10 passed, 77 deselected; compileall
  exited 0; local `HEAD` equals `origin/main` at
  `ad45a4ffc8689da159f67c533fd4eea8d093c082`; `gh pr list --state open`
  returned `[]`.
- Fresh Docker check still failed: `com.docker.service` stayed `Stopped`,
  `docker info` could not find `//./pipe/dockerDesktopLinuxEngine`, and Docker
  Desktop's backend error file reports access denied on
  `\\.\pipe\dockerBackendApiServer`.
- Docker live smoke could not be rerun locally after bounded recovery attempts;
  no new live MinIO claim was added beyond the committed smoke manifest.

Boundary:
- No GitHub comments/reviews were posted; no PR branch was changed; no Linear,
  Spark, Ollama, or live collector runs were used.

Next:
- Continue with GAP-007 Gold loading from persisted Silver, then Spark evidence.
- Rerun `docker compose up -d` and `python scripts/minio_smoke.py` from a
  Windows session that owns Docker Desktop if new live MinIO evidence is
  required.

## 2026-06-24 - Live re-audit + data inventory + undocumented-gap hunt

Skill: research-orchestrator (Context7, Tavily, Exa, Ref) via two background workflows
(railway-state-audit 21 agents; undocumented-gap-hunt 38 candidates -> 19 gaps).
Research log: .planning/coursework/research/bigdata/state-reaudit-tests-inventory-2026-06-23.md

Done:
- Ran all local tests: full suite 87 passed (77 unit + 10 integration); -m live/-m spark = 0;
  compileall clean. Env Python 3.14.0 / pandas 3.0.3 / pyarrow 24.0.0.
- Live tests: docker compose up -d + scripts/minio_smoke.py -> live 32B s3fs round-trip OK
  (first live MinIO run; prior session's Docker engine was down). Live WB Bronze->Silver->Gold
  -> Gold 2,968x4 (151 geos, 1995-2021, AT/HU). Eurostat flaked (transient RemoteDisconnected).
- Added a data inventory with real sample rows to the dashboard (docs/index.html), refreshed
  metrics, added an Open-risks section.
- Verified 8 load-bearing claims (all confirmed) + found 19 undocumented gaps (GAP-012..030),
  written into docs/GAP_REGISTER.md, STATE_AND_ROADMAP.md, TASKS.md.

Evidence:
- output/evidence/inventory-live-2026-06-23/ (bronze, railway_ml.parquet, counts.json, silver/, inventory_samples.json)
- output/evidence/minio-smoke/manifest.json (roundtrip_ok=true)

Boundary:
- No secrets printed; MinIO used local dev defaults only. No Ollama/Spark run (both absent).
- Live MinIO stack left running; docker compose down to stop.

Next:
- GAP-012 (regen recipe) + GAP-013 (live MinIO WB) before relying on the live path; then
  GAP-007 Gold<-persisted Silver, GAP-009 Spark (Spark 4.1 stack + JDK 17/21), report.

## 2026-06-24 - GAP-012 Regen Recipe Guard

Status: done.

Research:
- Required local research note:
  `.planning/coursework/research/bigdata/gap-012-bronze-gold-regen-recipe.md`.
- Approved implementation plan:
  `.planning/coursework/plans/bigdata/gap-012-bronze-gold-regen-recipe.md`.
- Local files reviewed first: `src/railway_lakehouse/bronze/live_check.py`,
  `src/railway_lakehouse/pipeline.py`, `src/railway_lakehouse/silver/stats/load.py`,
  `src/railway_lakehouse/gold/run.py`, `tests/test_bronze_live_check.py`,
  `tests/test_pipeline_gaps.py`, `docs/VERIFICATION.md`, `docs/GAP_REGISTER.md`,
  `docs/TASKS.md`, and `docs/index.html`.
- No external docs were needed because the change is repo-local and makes no new
  framework/API claims.

Changed:
- Added a local `--bronze-root` existence/type guard in `pipeline.py`.
- Added a local empty-input guard in `pipeline.py` so missing/empty local Bronze
  cannot write an empty Gold parquet.
- Added deterministic GAP-012 integration tests using `tmp_path` and fake
  live-check collectors only.
- Updated the regen recipe to use `output/evidence/local-stats-bronze-regen`
  consistently, and synced `GAP_REGISTER.md`, `TASKS.md`, and the dashboard.

Evidence:
- RED reproduction: scratch command against a non-existent nested Bronze root
  wrote 0-row Gold before the fix.
- Corrected live regen passed: 4 raw artifacts, 14,996,995 bytes, then Gold
  counts `rows=2139`, `columns=3`, `rail_network_length_km`, `contains_AT=true`,
  `contains_HU=true`, `year_min=1995`, `year_max=2021`.
- Missing-root CLI check now exits non-zero with a `FileNotFoundError` mentioning
  `--bronze-root` and `live_check`; no parquet is written.
- `python -m pytest -q -m integration`: 13 passed, 77 deselected.
- `python -m pytest -q -m unit`: 77 passed, 13 deselected.
- `python -m pytest -q`: 90 passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.

Boundary:
- Raw Bronze landing semantics were not changed.
- Numeric stat merging remains deterministic; no LLM rewrites numeric rows.
- New tests use only `tmp_path`/fixtures and do not depend on coursework/output data.
- Generated live regen raw Bronze remains under `output/evidence/**/bronze/`,
  which is intentionally gitignored.

Next:
- Open the PR for GAP-012. Continue with GAP-017/018 and GAP-020 after review/merge.
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

## 2026-06-24 - GAP-017 Spark Stack Pin

Status: done for static pin/guard/docs; no live Spark run was executed.

Research:
- Required note updated:
  `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`.
- `research-orchestrator` was used with local files first, then Context7 / official web docs for
  Spark, Delta, and Hadoop S3A compatibility.

Changed:
- `pyproject.toml`
- `tests/test_spark_stack_pins.py`
- `README.md`
- `.env.example`
- `docs/STATE_AND_ROADMAP.md`
- `docs/index.html`
- `docs/TASKS.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`

Findings:
- Live env remains Python 3.14.0 / pandas 3.0.3 / pyarrow 24.0.0 / numpy 2.4.4, with Java
  1.8.0_491 and no `JAVA_HOME`.
- GAP-017 adopted Stack B: PySpark 4.1.x + Delta 4.1.x + S3A Maven packages
  `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6` + JDK
  17/21. Stack A would require a runtime downgrade.
- `hadoop-aws` is a Maven/JVM S3A connector, so the pip dry-run resolves PySpark and
  Delta while docs record the matching S3A/AWS SDK v2 coordinate for the future Spark session.

Evidence:
- `python -m pip install --dry-run ".[spark]"` resolved `pyspark-4.1.2` and `delta-spark-4.1.0`.
- `python -m pytest -q tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pytest -q -m unit tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pytest -q` -> 88 passed.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed (line-ending warnings only).

Next:
- GAP-009 Spark evidence job after JDK 17/21 + `JAVA_HOME` are available.

## 2026-06-24 - GAP-017 PR Review Fix

Status: done for PR #15 request_changes follow-up.

Research:
- Required note updated:
  `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`.
- Used `research-orchestrator` with Context7 Hadoop docs; Ref search was attempted but unavailable due
  credits, so exact coordinates were verified from Apache Hadoop 3.4.1 docs and Maven Central POMs.

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
- `docs/PROGRESS_LOG.md`
- `.planning/coursework/research/bigdata/spark4-vs-35-stack-2026-06-24.md`

Findings:
- Removed the fake `hadoop-aws` pip dependency from `[spark]`; the extra now contains only
  `pyspark==4.1.*` and `delta-spark==4.1.*`.
- Added `railway_lakehouse.spark_config.SPARK_S3A_PACKAGES` with
  `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6` for future
  `spark.jars.packages` use.
- Updated GAP-009/GAP-017 task contracts in `docs/GAP_TASKS.md` to Spark 4.1 / Delta 4.1 /
  JDK 17 or 21 / Maven S3A packages.

Evidence:
- `python -m pytest -q tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pytest -q -m unit tests/test_spark_stack_pins.py` -> 1 passed.
- `python -m pip install --dry-run ".[spark]"` -> would install `pyspark-4.1.2`,
  `delta-spark-4.1.0`, `py4j-0.10.9.9`; no `hadoop-aws` pip package.
- `python -m pytest -q` -> 88 passed.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed (line-ending warnings only).

Next:
- Push the PR #15 update and keep it mergeable; GAP-009 can use the new Spark config constants.

## 2026-06-24 - GAP-007 Gold Load From Persisted Silver

Status: done.

Research:
- Required note written at `.planning/coursework/research/bigdata/gap-007-gold-load-from-silver.md`.
- Local files were researched first: `gold/run.py`, `silver/persist.py`, `pipeline.py`,
  `tests/test_silver_persist_integration.py`, `docs/DATA_CONTRACTS.md`, and the
  dashboard/status docs. No external research was needed.

Changed:
- `gold.run` is no longer a placeholder: it accepts `--silver-root`, `--out`,
  `--counts-out`, `--ingest-date`, `--year-min`, and `--year-max`.
- `gold.build.write_gold_counts` now owns the shared counts JSON writer; `pipeline.py`
  imports it, preserving GAP-010 counts behavior.
- Added `tests/test_gold_load_from_silver.py`, an integration test that persists fixture-derived
  Silver to `tmp_path`, runs the Gold CLI entrypoint, and verifies Gold + counts.
- Added `pythonpath = ["src"]` to pytest config so exact pytest commands verify this checkout
  rather than whichever editable worktree is globally installed.

Evidence:
- RED test observed before implementation: old `main()` rejected `argv`.
- `python -m pytest -q -m unit` -> 89 passed, 14 deselected.
- `python -m pytest -q -m integration` -> 14 passed, 89 deselected.
- `python -m pytest -q` -> 103 passed.
- `python -m compileall -q src tests` -> passed.
- Local CLI smoke under `output/runtime/gap-007-cli-smoke/` wrote Gold 4x4 counts with
  AT/HU present and `rail_passenger_km`.

Next:
- PR #18 is open and mergeable for `impl/gap-007`; after merge, continue with GAP-009 Spark evidence.
## 2026-06-24 - GAP-009 Spark Evidence Job

Status: done

Research:
- Required note written:
  `.planning/coursework/research/bigdata/spark-evidence-job.md`.
- Used `research-orchestrator` with local files first, Context7 for Spark 4.1.1 PySpark API docs, Ref attempted but unavailable due credits, and Firecrawl for the native Windows Hadoop helper source.

Changed:
- `src/railway_lakehouse/spark_jobs/__init__.py`
- `src/railway_lakehouse/spark_jobs/coverage.py`
- `tests/test_spark_coverage.py`
- `tests/test_spark_stack_pins.py`
- `output/evidence/spark/manifest.json`
- `output/evidence/spark/coverage_by_geo_year/`
- `README.md`
- `docs/VERIFICATION.md`
- `docs/TASKS.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/index.html`
- `.planning/coursework/plans/bigdata/gap-009-spark-evidence-job.md`
- `.planning/coursework/research/bigdata/spark-evidence-job.md`

Findings:
- The Spark job imports without PySpark because Spark imports are deferred into runtime helpers.
- Missing input and 0-row input fail loudly before any successful evidence is claimed.
- The successful evidence run used the real inventory-live Gold Parquet, not the nonexistent `output/evidence/live/railway_ml.parquet`.
- Manifest: Spark 4.1.2, JDK 21.0.11, input 2,968 x 4, output 2,968 x 5, one partition/part-file plus `_SUCCESS`, status `passed`.

Evidence:
- `python -m pytest -q -m "unit or integration"` -> 103 passed, 2 deselected.
- `python -m pytest -q -m spark` -> 2 passed, 103 deselected.
- `python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/inventory-live-2026-06-23/railway_ml.parquet --out output/evidence/spark/` -> passed.
- `python -m pytest -q` -> 105 passed.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with line-ending warnings only.

Next:
- GAP-011 can draft the report from the committed Spark evidence plus existing Gold counts.
## 2026-06-24 - GAP-013 live World Bank wiring

Status: closed (Codex implemented; orchestrator verified + shipped)

- Orchestration: `/research-orchestrator` research (`gap013-live-minio-worldbank-stats-2026-06-24.md`) → spec/prompt (`output/evidence/orch/gap-013/`) → Codex agent on worktree `impl/gap-013` (thread `019efa7b-4d50-…`).
- The Codex agent added `_read_bronze_worldbank` + `_read_bytes` and the live Eurostat+World Bank combination in `src/railway_lakehouse/pipeline.py` (local `bronze_root` branch unchanged), plus the deterministic `memory://` integration test. Its exec sandbox could not spawn processes (`CreateProcessAsUserW failed: 5`), so it could not verify/commit/push/PR and correctly reported `blocked` without fabricating evidence.
- Orchestrator verification + closure: `pytest -q -m integration tests/test_pipeline_live_stats_worldbank.py` → 2 passed; full `pytest -q` (JAVA_HOME=jdk-21) → 123 passed, 1 skipped (known Windows Spark/winutils skip); `compileall` clean. Updated `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`; PR opened against `main`.

## 2026-06-24 - PR 24 KSH XLSX reader review fixes

Status: done for review fixes.

Changed:
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `tests/test_silver_stats_ksh.py`
- `tests/test_env_versions.py`
- `constraints.txt`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/STATE_AND_ROADMAP.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `README.md`
- `.planning/coursework/research/bigdata/pr24-ksh-xlsx-reader-review-fix-2026-06-24.md`
- `output/evidence/pr24-ksh-live-check-after-fix/manifest.json`

Findings:
- PR #24's original reader fit only the simple label-before-year fixture and missed live KSH year-first, regional-total, and sectioned single-year workbook shapes.
- Broad label rules could map road-network rows into rail features and confuse passenger/freight km metrics with count/tonnage metrics.
- Dashboard/task docs were inconsistent about whether KSH XLSX parsing existed.

Evidence:
- `python -m pytest -q tests/test_silver_stats_ksh.py` -> 9 passed.
- `python -m pytest -q tests/test_silver_stats_ksh.py tests/test_env_versions.py` -> 14 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/pr24-ksh-live-check-after-fix --max-artifacts 6 --timeout-seconds 60` -> 6 artifacts, 92,509 bytes, 0 failures.
- Live parse over `output/evidence/pr24-ksh-live-check-after-fix/bronze` -> 6 KSH frames parsed, unified Silver output 382 rows x 8 columns, and 0 road-network rows mapped into Silver features.
- `python -m pytest -q -m integration` -> 16 passed, 121 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 136 passed, 1 skipped.
- `python -m compileall -q src tests` -> passed.

Next:
- Keep GAP-005 open until KSH is scheduled through `src/railway_lakehouse/bronze/run.py`.
- Add KSH-to-Gold real-data evidence when persisted Silver/Gold runs include KSH rows.

## 2026-06-24 - PR 25 broad stats pipeline review

Status: done.

Changed:
- Review fixes for Eurostat/World Bank production selectors, bounded live checks,
  unknown World Bank label handling, path-safe remote IDs, Bronze volume counting,
  and docs/dashboard sync.
- Required research note:
  `.planning/coursework/research/bigdata/pr25-bigdata-stats-pipeline-review-2026-06-24.md`.

Findings:
- Production ingestion now uses the same bounded selector helpers as live checks.
- Unknown World Bank IDs are recorded as `worldbank_unmapped:<id>` so broad
  non-rail indicators cannot map through English substring rules.
- Bounded local live evidence proves the broader stats net can land Eurostat and
  World Bank together and build a stats-only Gold matrix, but the full
  MinIO/Ollama/news/Spark E2E path remains open.

Evidence:
- Focused review suite: 69 passed.
- Unit/integration/full: 144 unit passed; 16 integration passed; 161 passed, 1
  known Spark/Windows skip in the full suite.
- Spark marker: 1 passed, 1 known Windows skip.
- Bounded live Eurostat/World Bank: 9 artifacts, 23,209,819 bytes; World Bank
  partial only for a no-series discovered indicator.
- Bronze volume: 9 datasets/artifacts, 99,937 observations.
- Stats-only live Bronze-to-Gold smoke: 3,548 rows x 9 columns.
- Live MinIO smoke against existing `railway-minio`: 32 B round-trip passed.

Next:
- Push PR #25 branch, let GitHub checks settle, merge PR #25.

## 2026-06-24 - PR #21 Eurostat pipeline review

Status: done.

Research:
- Required note written at `.planning/coursework/research/bigdata/pr21-eurostat-pipeline-review-2026-06-24.md`.
- Local files were researched first in the detached PR worktree `Halo-Skills-pr-21`.
- External checks were bounded to Eurostat TOC / SDMX endpoint probes needed to verify PR claims.

Changed:
- `.ship/pr/21/report.md`
- `.ship/pr/21/mode.json`
- `.ship/pr/21/sources.json`
- `.planning/coursework/research/bigdata/pr21-eurostat-pipeline-review-2026-06-24.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Evidence:
- PR review report posted to https://github.com/pol3et/railway-bigdata/pull/21#issuecomment-4789471429.
- Targeted Eurostat tests: 14 passed, 10 deselected.
- Full suite in PR worktree: 121 passed, 1 skipped.
- Unit-marker probe: 1 passed, 23 deselected.
- Live bounded seed probe: `tran_r_rago` and `tran_r_rapa` produced zero Silver rows.

Next:
- Wait for PR #21 author updates or decide whether to merge with the documented Major findings accepted.

## 2026-06-24 - News feature integration scan (state + options research)

Status: done for read-only analysis/research; no source code changed.

Research:
- `research-orchestrator` used. Routed MCP providers (via the workflow sub-agents): Tavily, Exa,
  Context7, WebFetch/WebSearch fallback, plus primary sources (GDELT GKG codebook, HuggingFace model
  cards, spaCy/Spark NLP/sbert docs, pdfplumber/Camelot/Docling, Databricks).
- Notes: `.planning/coursework/research/bigdata/news-feature-integration-scan-2026-06-24.md` (umbrella)
  + sub-notes `local-llm-feature-extraction-role-2026-06-24.md`,
  `nonllm-nlp-news-features-2026-06-24.md`, `images-nontext-pdf-mining-2026-06-24.md`.
- Method: dynamic multi-agent workflow (4 codebase explorers + 5 routed research agents + synthesis).

Findings (verified against source this session):
- Parsers work and are tested, but GDELT is queried via DOC 2.0 ArtList (`gdelt.py:43-56`) which cannot
  return GKG themes/tone/persons/orgs/locations; `gdelt_passthrough()` (`extract.py:86`) has zero callers;
  GKG zips land unparsed. Richest free structured signal is discarded.
- `NewsFeature` = 15 fields (`schema.py:39-54`); the LLM prompt asks for all of them incl. sentiment +
  confidence (broader than recommended). The LLM news path has NEVER run live (all tests mock it).
- Gold `aggregate_news()` (`gold/build.py:82`) wires ~20 news columns on (geo,year) but never aggregates
  rail_lines/language/confidence; real production Gold is stats-only (news_rows=[]).
- Besides news text: numeric stats only (WB/Eurostat/KSH). StatAustria ODS + UIC PDFs landed raw,
  unparsed. No image/OCR/PDF code anywhere in `/src`.

Recommendation:
- Keep "extract-wide-in-Silver, filter-in-Spark"; multi-tool role split (LLM for generative slice only;
  XLM-R sentiment; huBERT/German NER + gazetteer for entities if required; LaBSE embeddings for
  dedup+MLlib clustering; wire GKG passthrough). Never call models row-wise inside Spark.
- Do NOT process news images; only worthwhile non-text add is deterministic pdfplumber table extraction
  of the UIC PDFs into numeric StatFacts.
- Priority: (1) GKG passthrough, (2) run LLM news pass for real once + persist, (3) LaBSE + MLlib cluster
  job, (4) XLM-R sentiment, (5) widen Gold aggregation.

Evidence:
- No source edits, tests, live collectors, MinIO, Ollama, or Spark runs were executed for this analysis.
- Code claims verified by grep/read: dead `gdelt_passthrough`, `NewsFeature` 15 fields, `aggregate_news`
  column set.

Next:
- If approved, start with GAP candidate "GDELT GKG passthrough" (free signal) and a real one-time LLM
  news extraction run that persists `NewsFeature` rows under `output/evidence/`.

## 2026-06-24 - PR #26 UIC PDF reader ship-pr review

Status: done for read-only review; no PR comments posted.

Research:
- Required note written at `.planning/coursework/research/bigdata/pr26-uic-pdf-reader-review-2026-06-24.md`.
- Local files were researched first in detached worktree `Halo-Skills-pr-26`.
- External checks used Context7 pdfplumber/Camelot docs, Tavily PDF extraction research, and a Ref attempt that was unavailable due credits.

Changed:
- `.ship/pr/26/report.md`
- `.ship/pr/26/mode.json`
- `.ship/pr/26/sources.json`
- `.planning/coursework/research/bigdata/pr26-uic-pdf-reader-review-2026-06-24.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

Evidence:
- PR #26 review report: `.ship/pr/26/report.md`.
- Merge-tree check failed with conflicts against `origin/main`.
- Targeted UIC PDF tests: 4 passed.
- Focused stats/gold suite: 14 passed.
- Full suite in PR worktree: 135 passed, 1 skipped.
- Real UIC PDF probe over the two landed UIC PDFs produced zero Silver rows and zero unified `build_silver_stats` rows.

Next:
- Rebase PR #26, resolve stale KSH overlap, and replace the UIC line-regex parser with table-aware PDF extraction plus a realistic fixture before changing UIC status to done.

## 2026-06-24 - PR 26 UIC PDF reader review fixes

Status: done for review fixes.

Research:
- Required note written at `.planning/coursework/research/bigdata/pr26-uic-pdf-reader-fix-2026-06-24.md`.
- Local research inspected the current UIC public PDFs and showed the Synopsis PDF has extractable table rows; OCR is not required for that artifact.
- External docs check used Context7 for `pdfplumber` `Page.extract_tables()` behavior.

Changed:
- Rebased/rebuilt PR branch on current `main` to remove stale KSH overlap.
- Added deterministic UIC PDF table extraction in `src/railway_lakehouse/silver/stats/load.py`.
- Added UIC label crosswalk rules in `src/railway_lakehouse/silver/stats/merge.py`.
- Added PDF table, real UIC table-shape, decimal-comma, false-`at`, and `build_silver_stats` tests in `tests/test_silver_stats_uic_pdf.py`.
- Added `pdfplumber` runtime dependency and constraint pins.
- Updated dashboard/status docs and report caveats.
- Added `output/evidence/pr26-uic-pdf-silver-probe/manifest.json`.

Evidence:
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py` -> 6 passed.
- Real UIC PDF probe: Synopsis -> 39 rows, Traffic Trends -> 0 rows, unified Silver -> 39 rows and 9 mapped features.

Next:
- PR #26 is merged; keep GAP-005 open until UIC is scheduled through the Bronze runner and add UIC-to-Gold evidence in a future persisted run.

## 2026-06-25 - PR 27 Spark analysis review fixes

Status: done for review fixes.

Research:
- Required note written at `.planning/coursework/research/bigdata/pr27-spark-analysis-review-fixes-2026-06-25.md`.
- Local review inspected Gold/Spark contracts, dashboard/task docs, and the
  committed analysis artifact paths before editing.
- External docs check used Context7 for PySpark correlation, Parquet writer, and
  `percent_rank` window behavior.

Changed:
- Removed the unsupported constant `terrain_complexity` Gold feature.
- Hardened Spark correlation/regional jobs with existing default input paths,
  required-column guards, non-empty result guards, and mode-specific correlation
  output paths.
- Fixed by-country Spearman ranks to partition by `geo` and variable.
- Moved analysis CSV/JSON snapshots to `output/evidence/analysis-artifacts/` and
  updated manifests to avoid claiming uncommitted input/output paths.
- Added deterministic import/helper guards and Spark-marked job tests.
- Updated `docs/TASKS.md`, `docs/index.html`, and `docs/VERIFICATION.md`.

Evidence:
- Focused verification: 19 passed, 2 skipped for missing Windows
  `HADOOP_HOME`/`winutils.exe`.
- Compileall passed.
- `git diff --check` passed with CRLF normalization warnings only.

Next:
- Push PR #27 fixes, wait for GitHub checks, merge PR #27, and clean up the PR
  worktree.
## 2026-06-25 - News multi-model preprocessing: spec + 14-task pack + adversarial review

Status: done for design/planning; no source code changed (docs only; git left to the owner).

Research:
- `research-orchestrator` used. Routed MCP providers (via workflow sub-agents): Tavily, Exa, Context7, Ref, WebFetch.
- Note: `.planning/coursework/research/bigdata/news-model-spec-task-pack-2026-06-25.md` (+ the 2026-06-24 scan + sub-notes).
- Method: dynamic workflow (1 spec author + 14 task-spec authors + 5 independent reviewers + 1 synthesis = 21 agents).

Changed (docs only):
- Added `docs/SPEC_NEWS_PREPROCESSING.md` (design + eval strategy + single-box Ryzen 1600/GTX 1060 6GB sequential-pass plan + 8 must-fix review blockers + MVP build order + open decisions).
- Appended 14 pick-up-cold specs (GAP-031…044) to `docs/GAP_TASKS.md`.
- Added GAP-031…044 rows to `docs/GAP_REGISTER.md`; Wave 6 to `docs/TASKS.md`; WAVE 6 chips + footer to `docs/index.html`.

Findings:
- PDF decision recorded: capture everything (widen UIC geo, stage unmapped rows, mine traffic-trends text) but map deliberately → GAP-041.
- Owner constraint: single box, no hosted infra, sequential model passes (6 GB VRAM); torch CPU-only on Py3.14, Ollama uses the GPU.
- Review blockers (must-fix before build): torch CPU-only on Py3.14; GDELT/RSS = snippets not full-text; GKG absent for live DOC rows; LaBSE→e5/bge-m3; Spark KMeans non-deterministic (separate artifact, not Gold); NER ids were base LMs; cache-key/identity unsound; golden-set stats (TUNE/TEST split, collapsed taxonomy, CIs, N≥20).

Evidence:
- No source edits, tests, live collectors, MinIO, Ollama, or Spark runs. Spec claims grounded in agent file:line reads.

Next:
- Owner resolves the open decisions in the spec; then build MVP-first: GAP-039 (wide contract + sound cache key) → GAP-033 (first live LLM run) → P1 encoders/Gold/eval.

## 2026-06-25 - Full roadmap (news→EDA→report) + compute/embedder/feature research + GAP-045…050

Status: done for planning/roadmap; no source code changed (docs only; git left to the owner).

Research:
- `research-orchestrator` workflow `roadmap-research-and-eda-design` (3 research + 1 design agent; HU-sentiment agent failed structured-output cap — answered from small-corpus reasoning). Note: `.planning/coursework/research/bigdata/roadmap-compute-eda-2026-06-25.md`.

Changed (docs only):
- Added `docs/ROADMAP_NEWS_TO_REPORT.md` — Sessions A/B/C, Waves 6-7, Contracts D/E/F, EDA-first (hypotheses formed FROM artifacts in GAP-048), compute plan, data-location, investment finding.
- Appended GAP-045…050 specs to `docs/GAP_TASKS.md` (with GAP-047/048 framing overrides). Added GAP-045…050 rows to `docs/GAP_REGISTER.md`; Wave 7 + GAP-050 to `docs/TASKS.md`; WAVE 7 + GAP-050 chips + footer to `docs/index.html`. Folded embedder/sidecar decision into `docs/SPEC_NEWS_PREPROCESSING.md`.

Findings / decisions (owner-confirmed):
- Embedder DEFAULT = `multilingual-e5-base` (short snippet texts; dedup quality is algorithm-dominated; model is a config knob; bge-m3 swappable). torch via Py3.12+cu126 GPU sidecar (sm_61) or CPU; sequential passes; kill idle MCP servers.
- Investment X = Eurostat `rail_investment` (dense, deterministic); news money secondary. 9/12 teammate correlates already collected; only IS.VEH.PCAR.P3 + PA.NUS.PPP new (GAP-045); terrain/coords-speeds deferred (new source).
- Hypotheses formed FROM EDA (GAP-048), NOT pre-listed (owner decision). All data local (MinIO volume + output/).
- New GAP-050: LLM prompt-engineering design (prompt-master + research-orchestrator), precedes the live run GAP-033.

Evidence:
- No source edits, tests, or live runs. Research cites source URLs (PyTorch #169929, uv #14742 sm_61/cu126, WB indicator pages, Eurostat, MMTEB).

Next:
- Owner picks the embedder (e5-base confirmed) + resolves remaining spec decisions; then orchestrate Wave 6a: GAP-039 → GAP-050 → GAP-033 via `scripts/orch/codex_impl.sh`.

## 2026-06-25 - GAP-039 wide NewsFeature contract + cache

Status: done; shipping via PR.

Research:
- `research-orchestrator` record written at `.planning/coursework/research/bigdata/newsfeature-wide-contract.md`.

Changed:
- Added the 43-field article-grain `NewsFeature` contract, validation/coercion, content-hash/model-digest cache, cached extraction wrappers, failure accounting helper, persisted wide schema support, focused unit/integration tests, and docs/dashboard sync.

Evidence:
- Targeted unit: 10 passed.
- Targeted integration: 1 passed.
- Compileall passed.
- Full suite was already green before ship: 183 passed, 3 skipped.

Next:
- PR `impl/gap-039` to `main`; downstream unblocked tasks are GAP-031-GAP-038 and GAP-040, with live LLM prompt/run work continuing in GAP-050/GAP-033.

## 2026-06-25 - GAP-039 PR review fixes

Status: done; pushed to PR #28.

Research:
- Local review only; the existing GAP-039 research record was updated with review-fix notes.

Changed:
- Wired `FileSystemCache` into `pipeline.run_pipeline()` and `silver.run.run_news()`.
- Preserved GDELT/GKG metadata through `_normalize_article()`.
- Fixed zero-tone passthrough and added focused regressions.

Evidence:
- Focused regressions: 4 passed.
- Compileall passed.
- Full suite: 187 passed, 3 skipped.

Next:
- Monitor PR #28 mergeability/checks and proceed to GAP-050/GAP-033 after merge.

## 2026-06-25 - GAP-033 live qwen3:4b NewsFeature evidence

Status: done; shipping via PR.

Research:
- `research-orchestrator` record written at `.planning/coursework/research/bigdata/silver-news-llm-extraction-live.md`.
- Local implementation plan written and approved at `.planning/coursework/plans/bigdata/gap-033-news-llm-extraction-live.md`.

Changed:
- Added a live-marked regression smoke test for real Ollama extraction.
- Landed a bounded real RSS+GDELT Bronze sample locally under ignored `output/evidence/news-extraction-sample-bronze/`.
- Ran the GAP-050 production `silver.run.run_news(...)` path with `qwen3:4b`, persisted 40 real `NewsFeature` rows, the run manifest, the empty failure sidecar, a news-only Gold traceability Parquet, and a human evidence manifest under `output/evidence/news-extraction-sample/`.
- Synced `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, and `docs/LLM_EXTRACTION_DESIGN.md`.

Evidence:
- Live smoke: 1 passed.
- Live extraction: 40 processed, 40 succeeded, 0 permanent failures.
- Parquet readback: `(40, 43)`, rail-related `True=21`, `False=19`.
- Unit marker suite: 171 passed, 30 deselected.
- Full suite: 195 passed, 6 skipped.
- Compileall: passed.

Next:
- GAP-043 should quantify the qwen3:4b quality caveat observed on sparse GDELT snippets; GAP-040/GAP-022 should improve news aggregation/date coverage before final report usage.

## 2026-06-25 - GAP-044 parser correctness audit
## 2026-06-25 - GAP-036 Silver news embeddings and dedup markers

Status: done; PR preparation.

Changed:
- Added `silver/news/embeddings.py` with cached sentence-transformers model loading, normalized `text_embedding` population, and deterministic local near-duplicate grouping.
- Reused the GAP-039 wide contract fields `text_embedding_model`, `text_embedding`, and `cross_lingual_dedup_id`; added `is_duplicate`.
- Changed persisted `text_embedding` Arrow type to `list<float32>` and proved old Parquet backfill still reindexes.
- Synced docs/dashboard: `docs/DATA_CONTRACTS.md`, `docs/SILVER_DESIGN.md`, `docs/STATE_AND_ROADMAP.md`, `docs/TASKS.md`, `docs/index.html`, `docs/GAP_REGISTER.md`, `README.md`.

Findings:
- Research-orchestrator record: `.planning/coursework/research/bigdata/labse-embeddings-dedup.md`.
- Approved plan: `.planning/coursework/plans/bigdata/gap-036-news-embeddings-dedup.md`.
- Refined model choice: `intfloat/multilingual-e5-base` default, BGE-M3 swappable, LaBSE not default.
- Dedup threshold: cosine similarity `0.95`; group ids are deterministic across shuffled input.

Evidence:
- `python -m pytest -q tests/test_silver_news_embeddings.py -v` -> 10 passed.
- `python -m pytest -q -m integration tests/test_silver_persist_integration.py tests/test_gold_load_from_silver.py tests/test_silver_news_embeddings_integration.py -v` -> 2 passed, 1 skipped (`sentence_transformers` not installed).
- `python -m pytest -q -m unit` -> 181 passed, 31 deselected.
- `python -m pytest -q -m integration` -> 23 passed, 1 skipped, 188 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 208 passed, 4 skipped.
- `python -m compileall -q src tests` -> passed.
- Docs grep and schema smoke passed.

Next:
- Open PR from `impl/gap-036`; next implementation gap is GAP-037 Spark clustering/count enforcement or GAP-040 Gold news widening/filtering.

## 2026-06-25 - GAP-036 PR review fixes

Status: done; PR #39 updated.

Changed:
- Wired `cluster_near_duplicates(...)` into production Silver news extraction after embeddings are present.
- Added a production-entrypoint regression test through `silver.run.run_news(...)` with mocked embeddings; no GPU/network required.
- Added an embedding-availability gate regression test.
- Synced docs/dashboard wording so GAP-036 closure now explicitly says production local dedup markers run in Silver extraction.

Evidence:
- RED check before the fix: production-entrypoint dedup regression failed because `cross_lingual_dedup_id` stayed null.
- Targeted news tests: 22 passed.
- Integration subset: 7 passed, 1 skipped (`sentence_transformers` not installed).
- Full suite with `JAVA_HOME` set: 210 passed, 4 skipped.
- Compileall: passed.

Next:
- PR #39 review/CI can proceed; Spark-scale count enforcement remains GAP-037/GAP-040.
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
- The old AT/HU-only UIC parser gate is removed from Silver parsing; the live Synopsis PDF parses to 738 golden rows across 80 geos with deterministic label/value parsing.
- The Traffic Trends PDF still has no country-level synopsis table, but its extractable text is staged as text chunks; live staging evidence contains 747 rows total and 476 text chunks.
- The Silver `uic_staging` Parquet contract is documented and covered by a tmp_path round-trip test.

Evidence:
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py` -> 10 passed.
- `python -m pytest -q tests/test_silver_stats_uic_pdf.py::test_uic_staging_roundtrip_persists_and_reloads -v` -> 1 passed.
- `python -m pytest -q` -> 199 passed, 6 skipped.
- `python -m compileall -q src tests` -> clean.
- `python -m html.parser docs/index.html` -> clean.
- UIC live check under `output/evidence/uic-proof-of-widen-2026-06-25/` -> 2 PDF artifacts, 2,109,240 bytes, passed.

Next:
- Open the PR for `impl/gap-041` and keep the dashboard/docs status synced through review.
## 2026-06-25 - GAP-040 Gold news aggregation widened
## 2026-06-25 - GAP-045 World Bank macro indicators

Status: done; shipping via PR.

Research:
- `research-orchestrator` record: `.planning/coursework/research/bigdata/parser-correctness-audit.md`.
- Self-approved implementation plan: `.planning/coursework/plans/bigdata/gap-044-parser-correctness-audit.md`.

Changed:
- Added deterministic parser golden fixtures under `tests/fixtures/silver/` for RSS, GDELT, World Bank, Eurostat, KSH, and UIC.
- Hardened RSS/GDELT parsing and Gold news aggregation for GAP-022, GAP-025, and GAP-026.
- Added parser-focused unit tests and field-coverage artifacts in `docs/PARSER_FIELD_COVERAGE.md` and `.json`.
- Synced `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, and `README.md`.
- Added `.gitattributes` binary guards for fixture formats such as PDF, XLSX, GZ, ODS, and Parquet.

Findings:
- `NewsFeature` is currently a 43-field dataclass; the draft spec's 15-field Pydantic assumption was stale.
- No committed raw KSH/UIC bytes were present under `output/evidence/`; those fixtures are self-contained parser-shape samples and tests do not reach live services.
- RSS malformed feeds now log/skip; GDELT bad JSON/articles log/skip; Gold date parsing handles ISO, GDELT compact, and RFC-822 values and tolerates missing optional dict fields.

Evidence:
- Focused parser verify: 21 passed.
- Full suite: 216 passed, 6 skipped.
- Compileall: passed.
- Parser coverage JSON smoke: passed.
- `git diff --check`: passed with line-ending warnings only.

Next:
- Push `impl/gap-044` and open a PR against `main`.
- `research-orchestrator` record written at `.planning/coursework/research/bigdata/silver-sentiment-encoder.md`.
- Local implementation plan written and self-approved at `.planning/coursework/plans/bigdata/gap-034-sentiment-encoder.md`.

Changed:
- Added lazy, pinned CardiffNLP XLM-R sentiment wrapper with CPU-only inference and optional-dependency failure guards.
- Moved sentiment/confidence ownership out of the LLM path and into a post-validation encoder pass.
- Populated both legacy (`sentiment`, `confidence`) and wide (`sentiment_label`, signed `sentiment_score`, `sentiment_confidence`) fields.
- Included sentiment model id/revision in the news extraction cache digest.
- Updated Gold to prefer numeric `sentiment_score` while retaining label-map fallback for legacy/GDELT rows.
- Synced `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`, `docs/GAP_TASKS.md`, `docs/TASKS.md`, and `docs/index.html`.

Findings:
- Draft spec was stale against live code because GAP-050 had already narrowed the LLM prompt away from sentiment.
- Current HF revision is `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8`; the draft's `59b7eda` pin was not current.
- The pinned model artifact is about 1.04 GiB; Hungarian is not in the sentiment fine-tune language set and remains a transfer/evaluation caveat.

Evidence:
- `python -m pytest -q tests/test_silver_sentiment_encoder.py` -> 7 passed.
- `python -m pytest -q tests/test_silver_news_parsers.py` -> 7 passed.
- Targeted GAP-034/import/parser suite -> 15 passed.
- Affected news/gold slice -> 41 passed.
- Full suite -> 204 passed, 6 skipped.
- `python -m compileall -q src tests` -> passed.
- `git diff --check` -> passed with line-ending warnings only.

Next:
- GAP-035 should add deterministic language ID; GAP-043 should evaluate XLM-R sentiment quality on held-out multilingual news, especially HU transfer behavior.

## 2026-06-25 - GAP-034 PR #31 long-text sentiment review fix

Status: done; PR #31 update pending push.

Changed:
- Added a regression test for articles well over the XLM-R 512-token limit.
- Updated `SentimentEncoder.encode()` to call the Hugging Face pipeline with `truncation=True` and `max_length=512`.
- Updated GAP-034 test-evidence rows in `docs/GAP_REGISTER.md`.

Evidence:
- RED: long-text regression failed before the fix because encode returned `None`.
- Focused regression: 1 passed.
- Sentiment encoder unit file: 8 passed.
- GAP-034/import/parser suite: 16 passed.
- Affected news/gold slice: 41 passed.
- Full suite: 205 passed, 6 skipped.
- Compileall: passed.

Next:
- Commit and push the PR #31 review fix.
- `research-orchestrator` record and approved local plan written at `.planning/coursework/research/bigdata/gold-widen-news.md`.
- Context7 covered pandas groupby/pivot/explode/cut patterns; Firecrawl covered ISO 639 and GDELT GKG docs after Ref returned no credits.

Changed:
- Widened `aggregate_news()` with canonical language columns, confidence stats/bins, rail-line unique/list rollups, bounded GKG tone/token rollups, canonical event/operator reindexing, optional `year-month` grain, mixed date parsing, and missing optional dict-field defaults.
- Added unit coverage for the widened aggregation, deterministic schemas, mixed dates, and year-month buckets.
- Added integration coverage proving persisted Silver NewsFeature list/GKG fields reload into widened Gold columns through the Gold CLI.
- Synced `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/GAP_REGISTER.md`, and `docs/index.html`.

Evidence:
- Red focused tests failed before implementation: 4 unit failures and 1 integration failure.
- Focused unit: 9 passed.
- Focused integration: 2 passed.
- Full unit marker suite: 175 passed, 31 deselected.
- Integration marker suite: 24 passed, 182 deselected.
- Full suite: 200 passed, 6 skipped.
- Compileall: passed.
- Diff check: passed with line-ending warnings only.

Next:
- GAP-043 remains the quality/eval gate before report-grade news claims.
- GAP-031/GDELT backfill can add deeper GKG parsing or canonical theme pivots later; GAP-040 only aggregates already persisted fields.
- `research-orchestrator` record written at `.planning/coursework/research/bigdata/macro-indicators-gap045.md`.
- Local implementation plan written and self-approved at `.planning/coursework/plans/bigdata/macro-indicators-gap045-plan.md`.
- Tavily/DataBank/API checks refined the subagent spec: `PA.NUS.PPP` has live AT/HU coverage; `IS.VEH.PCAR.P3` has metadata and lands through the current API but no AT/HU non-null rows; `IS.VEH.NVEH.P3` remains excluded.

Changed:
- Added `IS.VEH.PCAR.P3` and `PA.NUS.PPP` to the World Bank curated selector.
- Added canonical `cars_per_1000` and `ppp_conversion_factor` keys and deterministic World Bank source-id mapping.
- Added unit and integration tmp_path tests for World Bank macro indicators.
- Wrote bounded live evidence under `output/evidence/macro-indicators-gap045/`.
- Synced `README.md`, `docs/STATE_AND_ROADMAP.md`, `docs/GAP_REGISTER.md`, `docs/GAP_TASKS.md`, `docs/TASKS.md`, and `docs/index.html`.

Evidence:
- New test file red before implementation, then green: 2 passed.
- Bounded live World Bank: 13 artifacts, 49,874,290 bytes.
- Bronze -> Gold from that live Bronze: 14,903 rows x 12 columns.
- Coverage summary: PPP AT/HU 36 rows each; cars_per_1000 AT/HU 0 rows.
- Unit verify: 172 passed, 31 deselected.
- Integration: 24 passed, 179 deselected.
- Full suite: 197 passed, 6 skipped.
- Compileall and diff check passed.

Next:
- Downstream EDA must use PPP for AT/HU and explicitly mark World Bank car ownership as uncovered for AT/HU in the current live API.

## 2026-06-25 - GAP-044 PR #35 merge conflict resolution

Status: done; pushed to PR #35.

Changed:
- Merged `origin/main` into `impl/gap-044`.
- Resolved conflicts in `src/railway_lakehouse/gold/build.py` and `src/railway_lakehouse/silver/news/extract.py`.
- Kept both GAP-044 parser audit guards and current main news behavior for language ID, sentiment, GKG passthrough, embeddings, and dedup.
- Updated GAP-044 schema guard/docs from 43 to 44 `NewsFeature` fields after main added `is_duplicate`.

Evidence:
- Focused conflict regression: 86 passed.
- Schema/focused guard rerun: 25 passed.
- Full suite: 289 passed, 7 skipped.
- Compileall: passed.

Next:
- Watch PR #35 for refreshed mergeability/checks.
