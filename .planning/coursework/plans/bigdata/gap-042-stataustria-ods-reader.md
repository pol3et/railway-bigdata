# GAP-042 Statistik Austria ODS Reader Implementation Plan

Status: approved
Date: 2026-06-25

Goal: Build a deterministic Statistik Austria ODS reader that emits Silver `StatFact` long rows with `geo="AT"` and register it in the Bronze stats loader.

Architecture: Use pandas `read_excel(..., engine="odf")` backed by `odfpy`. Keep parsing in Silver only. Convert ODS bytes to a tidy `(label, year, value, unit)` frame, then pass through the existing `read_tabular_long()` contract and source registry.

Tech stack: Python 3.12-3.14, pandas 3.0.x, odfpy 1.4.x, pytest.

Global constraints:
- Raw Bronze is immutable; do not write under any `bronze/` source path.
- Numeric values are parsed deterministically; no LLM rewrites numbers.
- Tests use generated `tmp_path` ODS fixtures, not `coursework/` data.
- Outputs and ad hoc inspection artifacts stay under `output/`.
- Dashboard sync is mandatory when parser/gap state changes: update `docs/TASKS.md` and `docs/index.html`.

## Refined Spec Notes

- The drafted spec was right that `odfpy` plus pandas `engine="odf"` is the right dependency path.
- The drafted spec was thin on actual file layout. Real freight ODS uses report-year rows (`Berichtsjahr 2025`) and measure rows (`Tonnen`, `1 000 tkm Inland`) with totals in `Insgesamt`, not a standard year-header row.
- Real rolling-stock ODS files use year columns, sometimes with repeated table headers in one sheet. The reader must scan multiple header rows and preserve title/section provenance.
- `docs/GAP_REGISTER.md` already contains a GAP-042 row; update it instead of adding a duplicate.
- Current suite counts are stale in the spec; record actual observed counts after verification.

## Files

- Modify `pyproject.toml`: add `odfpy>=1.4,<2` as a core dependency with a comment.
- Modify `src/railway_lakehouse/silver/stats/load.py`: add ODS helpers, `load_stataustria_frame`, docstring update, and `_SOURCES` registration.
- Modify `src/railway_lakehouse/silver/stats/merge.py`: add deterministic German rule mapping for the new Statistik Austria labels.
- Add `tests/test_silver_stats_stataustria.py`: generated ODS unit tests plus one routing integration test.
- Modify `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`.
- Add this plan and the research record.

## Task 1 - Tests First

- [ ] Add `tests/test_silver_stats_stataustria.py` with:
  - empty/non-ODS rejection assertions;
  - rolling-stock year-column ODS fixture;
  - freight report-year ODS fixture with unit override;
  - deterministic German crosswalk test using `use_llm=False`;
  - integration test proving `frames_from_bronze()` routes `.ods`.
- [ ] Run `python -m pytest -q tests/test_silver_stats_stataustria.py`.
- [ ] Expected RED: failure because `load_stataustria_frame` is not implemented or the source is not registered.

## Task 2 - Dependency And Loader

- [ ] Add `odfpy>=1.4,<2` to `pyproject.toml`.
- [ ] Implement helpers in `load.py`:
  - ZIP/ODS guard via `zipfile.is_zipfile(io.BytesIO(raw))`;
  - ODS read via `pd.read_excel(io.BytesIO(raw), sheet_name=0, engine="odf", header=None, dtype=object)`;
  - report-year freight total extraction;
  - multi-header rolling-stock extraction;
  - German number cleanup for blanks, dashes, spaces, decimal comma, and thousands dot;
  - per-row units.
- [ ] Implement `load_stataustria_frame()` with `read_tabular_long(..., geo="AT")`, `source_system="statistik_austria"`, `_LONG_COLS` ordering, warnings, and `_empty()` on failure.
- [ ] Register `_SOURCES["statistik_austria"] = (load_stataustria_frame, (".ods",))`.
- [ ] Run the new test file and fix until green.

## Task 3 - Crosswalk And Integration

- [ ] Add German deterministic mapping in `merge.py` for:
  - `transportaufkommen` -> `rail_freight_tonnes`;
  - `transportleistung` / `tkm` -> `rail_freight_tonne_km`;
  - folded rolling-stock total labels such as `lokomotivbestande ... insgesamt`, `schienenguterwagenbestande ... insgesamt`, `schienentriebfahrzeugbestande ... insgesamt`, and `schienenpersonenwagenbestande ... insgesamt`.
- [ ] Keep rules narrow so rolling-stock detail rows do not all collapse into Gold totals.
- [ ] Run `python -m pytest -q tests/test_silver_stats_stataustria.py`.

## Task 4 - Docs And Progress

- [ ] Mark GAP-042 closed in `docs/GAP_REGISTER.md` with evidence from the new tests and verification.
- [ ] Update `docs/TASKS.md` from 4/5 to 5/5 stats readers and mark `silver/stats-parsers-extra` done.
- [ ] Update `docs/index.html` Statistik Austria source chip and wave/task text from no ODS reader to done.
- [ ] Append handoff entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

## Task 5 - Verification And Shipping

- [ ] Run `python -m pip install -e ".[test]"`.
- [ ] Run `python -m pytest -q tests/test_silver_stats_stataustria.py`.
- [ ] Run `python -m pytest -q -m unit`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Run `git diff --check`.
- [ ] Commit, push branch `impl/gap-042`, open PR against `main`, and confirm mergeability.

## Self-Review

- Spec coverage: dependency, loader, registration, unit tests, integration routing test, docs/dashboard sync, progress logs, verification, and PR are covered.
- Scope control: no Bronze mutation, no live collector, no scheduler wiring, no UIC/KSH reader edits.
- Stale-spec corrections: actual ODS freight layout and existing GAP-042 row are accounted for.
- Approval: plan approved for implementation by the agent on 2026-06-25.
