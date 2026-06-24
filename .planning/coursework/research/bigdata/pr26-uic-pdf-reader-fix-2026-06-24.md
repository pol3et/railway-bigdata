# PR #26 UIC PDF Reader Fix Research

Date: 2026-06-24

## Scope

Fix PR #26 after review found that the line-based UIC PDF reader produced zero rows from the real public UIC PDFs and left docs/dependency state inconsistent.

## Local Findings

- The existing UIC Bronze evidence tree contains two public PDFs from `output/evidence/uic-live-check-2026-06-22/manifest.json`.
- `uic_railway_statistics_synopsis_2025.pdf` is not a scanned image: `pdfplumber` extracts text and a 176-row, 25-column country/operator table on page 4.
- `uic_traffic_trends_2024.pdf` contains extractable text but no country-level Synopsis table, so it should be skipped by the Silver stats reader.
- The original line heuristic failed because UIC table headers and country/operator values are separated into different cells/rows; country, feature, year, and value do not appear together on one text line.

## External Docs

- Context7 `pdfplumber` docs confirmed `Page.extract_tables()` returns `table -> row -> cell` lists and is the appropriate API for table-shaped PDF content.
- Source: https://github.com/jsvine/pdfplumber/blob/stable/README.md

## Implementation Decision

- Use `pdfplumber` table extraction, not OCR, for the public Synopsis PDF.
- Parse only recognized UIC country/operator table shapes and exact AT/HU country codes for this project scope.
- Preserve original UIC column labels in `source_column`; map them deterministically in the crosswalk.
- Do not parse the Traffic Trends PDF by narrative heuristics because it has no country-level Synopsis table and would risk fabricated stats.

## Evidence

- `python -m pytest -q tests/test_silver_stats_uic_pdf.py` -> 6 passed.
- Real UIC probe with `PYTHONPATH=src` over the existing raw UIC evidence tree:
  - `uic_railway_statistics_synopsis_2025.pdf` -> 39 Silver rows, AT/HU, 2020-2024.
  - `uic_traffic_trends_2024.pdf` -> 0 rows, expected skip.
  - `build_silver_stats(...)` -> 39 unified rows across 9 mapped UIC features.
- Committed evidence manifest: `output/evidence/pr26-uic-pdf-silver-probe/manifest.json`.

## Remaining Boundary

- This does not claim OCR coverage, subscribed RAILISA CSV/Excel/API access, all-country extraction, or a Gold rerun including UIC.
- Statistik Austria ODS remains the pending extra stats parser under GAP-006.
