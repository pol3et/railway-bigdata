# PR #21 Eurostat Pipeline Review Research - 2026-06-24

## Scope

Read-only ship-pr review of GitHub PR #21, `fix/eurostat-pipeline`, head `fe7b43492415aae583428e2fdadbec2258001d7e`.

## Local Research First

- Read `AGENTS.md` hard rules and workflow requirements.
- Read changed files in the detached PR worktree:
  - `src/railway_lakehouse/bronze/live_check.py`
  - `src/railway_lakehouse/bronze/sources/eurostat.py`
  - `src/railway_lakehouse/silver/config.py`
  - `src/railway_lakehouse/silver/stats/merge.py`
  - `tests/test_bronze_live_check.py`
  - `tests/test_eurostat_hardening.py`
  - `tests/test_eurostat_silver_reader.py`
- Read supporting contracts/status docs:
  - `docs/DATA_CONTRACTS.md`
  - `docs/GAP_REGISTER.md`
  - `docs/TASKS.md`
  - `docs/index.html`
  - `docs/VERIFICATION.md`
  - `docs/STATE_AND_ROADMAP.md`

## External Checks

- Fetched Eurostat TOC with a review User-Agent to verify live column shape: first columns are `title`, `code`, `type`.
- Checked representative Eurostat SDMX TSV endpoints:
  - `tran_r_rago`
  - `tran_r_rapa`
  - `enpe_rail_go`
  - `rail_pa_total`
  - `rail_go_total`
  - `rail_if_electri`
  - `rail_ac_catvict`
  - `rail_eq_locon`

## Verification Output

- `python -m pytest -q tests/test_eurostat_hardening.py tests/test_eurostat_silver_reader.py tests/test_bronze_live_check.py -k eurostat` -> 14 passed, 10 deselected.
- `python -m pytest -q` -> 121 passed, 1 skipped.
- `python -m pytest -q -m unit tests/test_eurostat_hardening.py tests/test_eurostat_silver_reader.py tests/test_bronze_live_check.py -k eurostat` -> 1 passed, 23 deselected.
- Live bounded seed probe with `PYTHONPATH` pinned to the PR worktree:
  - default bounded codes: `tran_r_rago`, `tran_r_rapa`.
  - both produced `silver_rows=0` under `read_eurostat_tsv`.

## Findings Carried To Report

- Major: default bounded Eurostat live-check seeds are fetchable but produce zero Silver rows under the new reader.
- Major: new Eurostat Silver tests write to the default `silver/crosswalk_cache.json`.
- Major: PR changes source/parser state but does not update `docs/TASKS.md` and `docs/index.html`.
- Minor: new deterministic test modules are not marked `pytest.mark.unit`.
- Minor: `enpe_rail_go` retirement comment conflicts with today's endpoint and local evidence.

Full report: `.ship/pr/21/report.md`.
