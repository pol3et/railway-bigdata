# Coursework Progress

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
