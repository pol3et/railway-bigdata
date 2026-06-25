# GAP-042 Research - Statistik Austria ODS StatFact Reader

Date: 2026-06-25

Skill: `research-orchestrator`

Routed providers:
- Context7: pandas ODS IO documentation.
- Ref: attempted `odfpy` documentation search; blocked by account credits.
- Firecrawl/Tavily: odfpy package/source lookup and Statistik Austria source-page lookup.
- Local files first: `AGENTS.md`, `docs/GAP_TASKS.md`, `docs/TASKS.md`, `docs/GAP_REGISTER.md`, `docs/PARSER_WORK_LOG.md`, `docs/DATA_CONTRACTS.md`, `src/railway_lakehouse/silver/stats/load.py`, `src/railway_lakehouse/silver/stats/merge.py`, `src/railway_lakehouse/bronze/sources/statistik_austria.py`, existing KSH/UIC stats tests.

Queries:
- `pandas read_excel engine odf ODS OpenDocument Spreadsheet support dependencies odfpy`
- `odfpy Python package ODS OpenDocument spreadsheet official documentation GitHub PyPI 1.4`
- `Statistik Austria Schienengueterverkehr_nach_Verkehrsbereich_2025 ODS layout header years unit`

External findings:
- pandas documents `pd.read_excel(..., engine="odf")` for `.ods` files and states that `odfpy` must be installed. Source URLs: https://pandas.pydata.org/docs/user_guide/io.html and https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html.
- pandas also lists `python-calamine` as an alternative engine for `.ods`, but this project already uses pandas Excel readers and only needs deterministic ODS support. `odfpy` is the lighter direct backend for `engine="odf"` here.
- PyPI lists `odfpy` 1.4.1 and describes it as a Python API/tools package for OpenDocument files. Source URL: https://pypi.org/project/odfpy/.
- The odfpy source repository is `eea/odfpy`. Source URL: https://github.com/eea/odfpy.
- Statistik Austria's official rail freight page links the freight ODS download and states the 2025 transport volume/performance headline. Source URL: https://www.statistik.at/en/statistics/tourism-and-transport/freight-transport/rail-freight-transport.

Local code findings:
- `src/railway_lakehouse/bronze/sources/statistik_austria.py` lands five raw `.ods` rail files as `stats/statistik_austria/<dataset_id>/ingest_date=.../<file>.ods`; it validates non-empty ZIP-like ODS bytes before landing.
- `src/railway_lakehouse/silver/stats/load.py` currently registers `worldbank`, `eurostat`, `ksh`, and `uic` in `_SOURCES`; no `statistik_austria` entry exists, so `frames_from_bronze()` never routes ODS bytes.
- Existing KSH helpers are useful but not sufficient for all real Statistik Austria layouts.

Live-layout inspection:
- Command used a bounded direct download to ignored runtime output under `output/runtime/gap-042-layout/` and read each ODS with `pd.read_excel(..., engine="odf", header=None, dtype=object)`.
- The freight ODS is not a KSH-style year-header table. It has years down the first column as rows like `Berichtsjahr 2025`; the measure rows below them are `Tonnen` and `1 000 tkm Inland`; the `Insgesamt` column holds the total.
- Rolling-stock ODS files are year-header tables with 2023/2024 as columns, but some files have repeated table headers such as `Antriebsart` and `Spurweite` in one sheet. The parser should scan multiple year-header rows and preserve title/section context in `source_column`.

Refined implementation decisions:
- Add core dependency `odfpy>=1.4,<2` in `pyproject.toml`; use pandas `engine="odf"` for both reading and generated test fixtures.
- Implement `load_stataustria_frame(raw: bytes, dataset_id: str) -> pd.DataFrame` with a ZIP/ODS guard, pandas ODS read, deterministic tidy extraction, `geo="AT"`, per-row units, and `source_system="statistik_austria"`.
- Support two real layouts without widening scope: report-year freight totals and repeated year-header rolling-stock tables.
- Add small German deterministic crosswalk rules in `merge.py` for the labels the new reader emits. This keeps unit tests deterministic with `use_llm=False`; it does not change numeric parsing and does not touch KSH/UIC readers.
- Use generated ODS fixtures in `tmp_path`; no test reads `coursework/` or committed live raw data.

Implementation validation notes:
- TDD red command: `python -m pytest -q tests/test_silver_stats_stataustria.py` failed with missing `load_stataustria_frame` and missing `.ods` routing.
- Targeted green commands before docs sync:
  - `python -m pytest -q tests/test_silver_stats_stataustria.py` -> 5 passed.
  - `python -m pytest -q -m unit tests/test_silver_stats_stataustria.py` -> 4 passed, 1 deselected.
- Bounded runtime smoke over the five direct Statistik Austria ODS downloads under `output/runtime/gap-042-layout/` parsed all five files: freight 10 rows (2021-2025), locomotives 18 rows, railcars 14 rows, freight wagons 16 rows, passenger carriages 12 rows. This is local runtime evidence only; it is not committed raw Bronze and does not replace deterministic fixtures.
