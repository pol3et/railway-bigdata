# KSH STADAT Seed Correction Research - 2026-06-22

## Scope

Turn the patch at `C:\Users\XxX360QUICKSCOPERXxX\Downloads\Telegram Desktop\ksh-stadat.patch`
into a GitHub PR, using repo docs and code as the roadmap source. No Linear
ticket was used.

## Local Files Read First

- `README.md`
- `TASK.md`
- `docs/PROGRESS_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/CODEMAP.md`
- `docs/DATA_CONTRACTS.md`
- `docs/WORKSTREAMS.md`
- `docs/VERIFICATION.md`
- `docs/ARCHITECTURE.md`
- `WIRING.md`
- `.planning/COURSEWORK_PROGRESS.md`
- `src/railway_lakehouse/bronze/sources/ksh.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `tests/test_bronze_characterization.py`
- `tests/test_bronze_live_check.py`

## Patch Intake

`git apply --check` did not apply cleanly because the patch was based on older
contexts in `docs/PARSER_WORK_LOG.md` and `tests/test_bronze_characterization.py`.
The implementation intent was integrated manually into the current tree:

- replace mislabelled KSH STADAT seeds with six curated rail or rail-bearing tables;
- keep an audit trail for retired/mislabelled seeds;
- reject HTTP-200 responses that are empty or not XLSX bytes;
- add mocked unit coverage for KSH validation and ingest behavior;
- update the live-check collector for the new `KshTable` seed shape;
- add/update docs and committed evidence manifest.

## External Docs

No external documentation lookup was needed. The change used local roadmap docs,
the supplied patch, and a bounded current-code live check against the URLs already
encoded by the KSH source module.

## Evidence

- `python -m pytest -q tests\test_bronze_characterization.py` passed: 15 passed.
- `python -m pytest -q tests\test_bronze_live_check.py` passed: 8 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/runtime/ksh-live-check-validation --max-artifacts 6 --timeout-seconds 30` passed with `artifact_count=6`, `byte_count=92509`, KSH `passed`, and 0 failures.

## Open Follow-Up

- GAP-005 remains open because `src/railway_lakehouse/bronze/run.py` still does
  not schedule KSH.
- KSH Silver parsing remains Wave 3 work in `docs/PARSER_WORK_LOG.md`.
