# PR 24 KSH XLSX reader review/fix - 2026-06-24

## Scope

Review PR #24 (`silver/stats-ksh-xlsx-reader`) against the repository goal: KSH Bronze XLSX artifacts should become deterministic Silver `StatFact` rows without parsing raw data in Bronze or using LLMs to rewrite numeric rows.

## Local files researched first

- `README.md`
- `TASK.md`
- `docs/PROGRESS_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/STATE_AND_ROADMAP.md`
- `docs/DATA_CONTRACTS.md`
- `docs/CODEMAP.md`
- `docs/WORKSTREAMS.md`
- `src/railway_lakehouse/bronze/sources/ksh.py`
- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/silver/stats/merge.py`
- `tests/test_silver_stats_ksh.py`
- `tests/test_env_versions.py`
- `constraints.txt`

## External docs

- Context7 pandas docs for `pandas.read_excel`: confirmed `engine="openpyxl"` is the intended engine for `.xlsx` files and that `header=None`/`dtype=object` are valid for layout-sensitive workbook parsing.

## Review findings

- Original PR parsed simple label-before-year workbooks, but current KSH STADAT files also use:
  - year-first tables with metric columns (`Year`, then road/rail feature columns);
  - regional tables where the useful national value is the `Country, total` row;
  - sectioned one-year tables where a section label must not override the metric label.
- Original mapping rules were too broad:
  - road-network rows could map into rail features;
  - `Passenger kilometres` could map to passenger count instead of passenger-km;
  - `Freight tonne-kilometres` could map to freight tonnes instead of tonne-km;
  - section labels could cause passenger rows to map as freight.
- Dashboard state was inconsistent: `docs/TASKS.md` marked KSH Silver done, while `docs/index.html` still showed "no XLSX reader".
- Original KSH tests did not exercise the live KSH workbook shapes found by bounded live collection.

## Changes made

- Hardened `load_ksh_frame` to parse:
  - year-first feature-column workbooks;
  - regional country-total workbooks;
  - sectioned single-year workbooks;
  - per-row units and title-level bracket units.
- Tightened deterministic label rules in `merge.py` so KSH labels map by the final metric segment before the broader label and road rows remain unmapped unless rail-specific.
- Added fixtures that model the live layouts and tests for units, country totals, section context, and canonical feature mapping.
- Added `openpyxl==3.1.5` and `et-xmlfile==2.0.0` to `constraints.txt`, plus dependency guard assertions.
- Updated dashboard/status docs and added live evidence manifest at `output/evidence/pr24-ksh-live-check-after-fix/manifest.json`.

## Evidence

- `python -m pytest -q tests/test_silver_stats_ksh.py` -> 9 passed.
- `python -m pytest -q tests/test_silver_stats_ksh.py tests/test_env_versions.py` -> 14 passed.
- `python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/pr24-ksh-live-check-after-fix --max-artifacts 6 --timeout-seconds 60` -> 6 artifacts, 92,509 bytes, 0 failures.
- Live parse over `output/evidence/pr24-ksh-live-check-after-fix/bronze` -> 6 KSH frames parsed; unified Silver output 382 rows x 8 columns; 0 road-network rows mapped into Silver features.
- `python -m pytest -q -m unit tests/test_silver_stats_ksh.py tests/test_env_versions.py` -> 14 passed.
- `python -m pytest -q -m integration` -> 16 passed, 121 deselected.
- `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q` -> 136 passed, 1 skipped.
- `python -m compileall -q src tests` -> passed.

## Boundary

- KSH is now a deterministic Silver parser, not a scheduled Bronze source. GAP-005 remains open until KSH/Statistik Austria/UIC are wired into `bronze/run.py`.
- KSH-to-Gold real-data evidence remains pending; the live validation here proves Bronze live collection and Silver parsing/mapping of current KSH artifacts.
- Statistik Austria ODS and UIC PDF readers remain separate GAP-006 work.
