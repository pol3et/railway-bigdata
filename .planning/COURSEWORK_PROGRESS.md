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
