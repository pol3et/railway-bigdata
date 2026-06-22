# PR 4 Review Fixes Research - 2026-06-22

## Scope

Fix the read-only PR #4 review findings for the KSH STADAT seed correction,
verify with local integration tests, push the branch, and merge after GitHub
reports no failing checks.

## Local Files Read First

- `docs/PARSER_WORK_LOG.md`
- `docs/VERIFICATION.md`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `.planning/coursework/research/bigdata/ksh-stadat-seeds-2026-06-22.md`
- `src/railway_lakehouse/bronze/sources/ksh.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`
- `tests/test_pipeline_gaps.py`

## Review Findings Addressed

- Historical `output/evidence/live-bronze/manifest.json` KSH evidence is now
  labelled pre-correction and explicitly superseded for current KSH claims.
- Current KSH live-check evidence is now committed at
  `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`.
- KSH XLSX validation now checks the ZIP workbook container members instead of
  only the `PK` magic prefix.
- `docs/VERIFICATION.md` now lists `tests/test_bronze_live_check.py` and the
  new integration fixture test.

## External Docs

No external documentation lookup was needed. The fixes used local PR review
artifacts, repo code, and repo documentation. The only live network command was
the bounded KSH collector run recorded below.

## Evidence

- `python -m pytest -q tests\test_bronze_characterization.py tests\test_bronze_live_check.py tests\test_bronze_live_check_integration.py` passed: 24 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/ksh-live-check-2026-06-22-current --max-artifacts 6 --timeout-seconds 30` passed with `artifact_count=6`, `byte_count=92509`, KSH `passed`, and 0 failures.
- `python -m pytest -q -m integration` passed: 1 passed, 33 deselected, 1 xfailed for documented GAP-004.
- `python -m pytest -q` passed: 34 passed, 1 xfailed for documented GAP-004.
- `python -m compileall src tests` passed.
- `python -m json.tool output\evidence\ksh-live-check-2026-06-22-current\manifest.json` passed.

## Open Follow-Up

- GAP-005 remains open because KSH is not yet scheduled through
  `src/railway_lakehouse/bronze/run.py`.
- KSH Silver XLSX parsing remains Wave 3 work in `docs/PARSER_WORK_LOG.md`.
