# PR #26 UIC PDF Reader Review Research

Date: 2026-06-24

## Scope

Review PR #26, `silver/stats-uic-pdf-reader`, for the railway big-data coursework repo. The review follows the requested `research-orchestrator` and `ship-it:ship-pr` workflow in read-only mode.

## Local Research First

Read local project guidance and contracts:

- `AGENTS.md`
- `README.md`
- `TASK.md`
- `docs/CODEMAP.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/DATA_CONTRACTS.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/TASKS.md`
- `docs/PROGRESS_LOG.md`

Resolved PR:

- PR: https://github.com/pol3et/railway-bigdata/pull/26
- Title: Add UIC PDF Silver stats reader
- Head: `c90709ce25e39d3e3c93bb90f768ac0919c35a98`
- Worktree: `C:\Users\XxX360QUICKSCOPERXxX\Documents\tmp\ai-masters\coursework\bigdata\Halo-Skills-pr-26`
- GitHub state: open, conflicting.

Local evidence:

- Existing raw UIC PDFs were found under ignored evidence in the main checkout:
  - `output/evidence/uic-live-check-2026-06-22/bronze/stats/uic/uic_railway_statistics_synopsis_2025/ingest_date=2026-06-22/uic_railway_statistics_synopsis_2025.pdf`
  - `output/evidence/uic-live-check-2026-06-22/bronze/stats/uic/uic_traffic_trends_2024/ingest_date=2026-06-22/uic_traffic_trends_2024.pdf`

## External Research

Routed MCP providers:

- Context7: resolved `/jsvine/pdfplumber` and queried `pdfplumber` text/table extraction docs. Relevant URL: https://github.com/jsvine/pdfplumber/blob/stable/README.md
- Context7: resolved Camelot docs and queried table extraction modes. Relevant URL: https://camelot-py.readthedocs.io/en/master/
- Ref: attempted documentation search, but the account returned "Not enough credits."
- Tavily research: used for broad PDF extraction best-practice synthesis. Relevant source URLs included:
  - https://tabula.technology
  - https://camelot-py.readthedocs.io/en/master/
  - https://github.com/jsvine/pdfplumber/blob/stable/README.md

Research takeaway:

- `pdfplumber` supports both text extraction and table extraction. For statistical PDFs, table extraction or layout-aware extraction should be evaluated before relying on raw line regex.
- Camelot and Tabula are table-first tools. Camelot documents `lattice` for ruled tables and `stream` for whitespace/alignment tables, with parsing reports and DataFrame output.
- For this project, a table-aware UIC-specific adapter is more appropriate than a generic country/year/metric/value same-line regex.

## Commands And Results

PR metadata and diff:

```text
gh pr view 26 --json number,title,headRefName,headRefOid,baseRefName,body,state,mergedAt,url,commits,headRepository,headRepositoryOwner,reviews,comments,statusCheckRollup,mergeStateStatus,reviewDecision,mergeable
gh pr diff 26 --name-only
gh pr diff 26 --patch
```

Merge check:

```text
git merge-tree --write-tree origin/main HEAD
```

Result: exited 1 with conflicts in:

- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/TASKS.md`
- `pyproject.toml`
- `src/railway_lakehouse/silver/stats/load.py`
- `tests/test_silver_stats_ksh.py`

Dependency install:

```text
python -m pip install -e ".[test]" -c constraints.txt
```

Result: installed `pdfplumber-0.11.10`, `pdfminer.six-20260107`, `pypdfium2-5.10.1`, and the editable PR worktree.

Tests:

```text
python -m py_compile src/railway_lakehouse/silver/stats/load.py
python -m pytest -q tests/test_silver_stats_uic_pdf.py
python -m pytest -q tests/test_silver_stats_uic_pdf.py tests/test_silver_stats_ksh.py tests/test_silver_stats_integration.py tests/test_gold_characterization.py
python -m pytest -q
git diff --check origin/main...HEAD
python -m pip check
```

Observed:

- UIC PDF unit tests: 4 passed.
- Focused stats/gold suite: 14 passed.
- Full PR worktree suite: 135 passed, 1 skipped.
- `git diff --check origin/main...HEAD`: clean.
- `pip check`: no broken requirements found.

Real UIC PDF parsing probe:

```text
load_uic_frame(raw_pdf, dataset_id)
build_silver_stats(output/evidence/uic-live-check-2026-06-22/bronze, use_llm=False)
```

Observed:

- `uic_railway_statistics_synopsis_2025`: 1,517,491 bytes, 5 pages, 23,049 extracted text chars, tables per page `[1, 4, 6, 1, 0]`, `silver_rows=0`.
- `uic_traffic_trends_2024`: 591,749 bytes, 3 pages, 5,610 extracted text chars, tables per page `[0, 0, 0]`, `silver_rows=0`.
- Unified Silver output from the UIC Bronze root: 0 rows, shape `(0, 8)`.

Table inspection:

- Page 4 of `uic_railway_statistics_synopsis_2025.pdf` contains a 176-row extracted table.
- Headers include length of lines, electrified lines, passengers carried, passenger-kilometres, tonnes carried, and tonne-kilometres.
- AT/HU rows are present, for example `AT` / `GKB (2020)`, `ÖBB (2024)`, `HU` / `FOX (2021)`, `MAV (2024)`.

False-positive probe:

```text
stats_load._uic_rows_from_text("At 2024 passenger-km increased 7 percent compared with 2023.", "synthetic")
```

Observed: emitted `geo=AT`, `year=2024`, `value=7.0`, `source_column=rail_passenger_km`.

## Findings Summary

- BLOCKING: PR cannot merge cleanly with `origin/main`.
- BLOCKING: real UIC PDFs produce zero Silver rows.
- Major: bare `at` can fabricate AT rows.
- Major: decimal-comma values parse as wrong magnitudes.
- Major: docs/index.html and constraints.txt are stale for the claimed parser/dependency changes.
- Major: UIC `source_column` stores canonical feature keys instead of original provenance labels.

Full report: `.ship/pr/26/report.md`.

## Notes

No PR comments were posted. No source code was edited. The PR review worktree was retained for re-review per `ship-pr` Stage 9.
