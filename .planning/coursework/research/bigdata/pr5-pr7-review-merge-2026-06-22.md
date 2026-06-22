# PR #5-#7 Review, Fix, And Merge

Date: 2026-06-22

## Local Research First

- Read `AGENTS.md` workflow requirements and the current repo state from
  `README.md`, `TASK.md`, `docs/PROGRESS_LOG.md`,
  `.planning/COURSEWORK_PROGRESS.md`, `docs/CODEMAP.md`,
  `docs/DATA_CONTRACTS.md`, and `docs/VERIFICATION.md`.
- Queried live GitHub state with `gh pr list` and `gh issue list`: PR #5,
  PR #6, and PR #7 were open; no open GitHub issues were returned.
- Created detached worktrees:
  - `../Halo-Skills-pr-5`
  - `../Halo-Skills-pr-6`
  - `../Halo-Skills-pr-7`

## Review Routing

- PR #5 was reviewed with `ship-it:ship-pr` in rigorous mode.
  - Local report: `../Halo-Skills-pr-5/.ship/pr/5/report.md`
  - Verdict before fixes: FAIL, with one Major and one Minor finding.
- PR #6 and PR #7 initially halted under `ship-it:ship-pr` because they were
  cross-repo fork PRs, which v1 marks out of scope.
- Per user instruction to review forks anyway, ran fork-compatible read-only
  fallback reviews in separate subagents.
- CodeRabbit review was not used: `coderabbit` was not installed and the
  documented installer path failed in this Windows shell because `sh` is not
  available.

## GitHub Collaboration

- Switched `gh` from read-only active account `cul8err` to admin account
  `pol3et`.
- Invited `alyonaprikhodko` and `Soomphik` as write collaborators on
  `pol3et/railway-bigdata` so future branches can be created directly in the
  base repository.
- Both fork PRs had `maintainerCanModify=true`, so fix commits were pushed to
  their fork branches before merging.

## Findings And Fixes

PR #5 `[codex] harden GDELT and refresh UIC sources`:

- Fixed historical GDELT safety: programmatic `past_recordings.ingest()` and
  backfill helpers now default to one page/file attempt unless an explicit
  unbounded value is supplied.
- Added a regression test proving default `ingest()` attempts only one
  historical DOC page.
- Removed a trailing blank-line diff-check failure in the UIC research note.

PR #6 `Add RSS feed health evidence`:

- Fixed malformed `docs/PARSER_WORK_LOG.md` parser-inventory row so the RSS
  row preserves the seven-column table shape.
- Rebased/merged onto PR #5's merged main and reconciled shared
  `docs/PARSER_WORK_LOG.md` and `tests/test_bronze_characterization.py`
  additions.

PR #7 `Statistik Austria: fix OGD API path + reject empty-200, land real rail .ods`:

- Fixed a Major review finding: Statistik Austria ingestion now rejects
  non-ODS/HTML HTTP-200 bodies instead of treating any non-empty 200 as a real
  `.ods` artifact.
- Added mocked regression tests for empty, HTML, and non-ODS HTTP-200 bodies.
- Rebased/merged onto main after PR #5 and PR #6 and reconciled shared
  docs/tests.

## Merge Results

- PR #5 merged at `53287a11bf8b91160b2f1af36c9c5bb6c50e5792`.
- PR #6 merged at `3fa4c899247a3c0c058f133a3a1e80345d3fe18c`.
- PR #7 merged at `8f69200b151a2989c9f7f5d665e61f6eeb81deb7`.
- `gh pr list --state open` returned `[]` after the merges.

## Final Verification On Merged Main

- `python -m pytest -q` passed: 53 passed, 1 xfailed for documented GAP-004.
- `python -m compileall src tests` passed.
- `python -m json.tool` passed for the GDELT, UIC, RSS, and Statistik Austria
  evidence manifests.
- `git diff --check` passed.

## Remaining Boundaries

- GAP-004 remains expected xfail: pipeline Bronze storage reads are still not
  wired.
- GDELT live collection remains not live-ok from this environment; the merged
  work provides retry/safety behavior and failed live evidence, not successful
  GDELT artifacts.
- UIC CSV/Excel/API remains access/subscription-bound; merged UIC scope is
  public PDF Bronze collection.
