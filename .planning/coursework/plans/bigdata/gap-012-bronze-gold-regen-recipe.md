# GAP-012 Bronze to Gold Regen Recipe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use inline execution for this
> surgical plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the documented Bronze to Gold regeneration recipe reproducible
on a clean checkout and prevent missing local Bronze roots from silently writing
empty Gold.

**Architecture:** Preserve raw Bronze landing behavior and the existing
run-id nesting contract. Put validation at the pipeline boundary, where the
CLI knows a local `--bronze-root` was requested and can fail before the Gold
writer emits a 0-row headline artifact.

**Tech Stack:** Python, pytest, pandas/pyarrow parquet, existing
`railway_lakehouse` modules.

---

## File Structure

- Modify `tests/test_pipeline_gaps.py`: add deterministic GAP-012 tests using
  `tmp_path` and fake live-check collectors only.
- Modify `src/railway_lakehouse/pipeline.py`: validate local Bronze roots and
  raise on empty local inputs before Gold writing.
- Leave `src/railway_lakehouse/gold/run.py` behavior unchanged unless the
  pipeline guard proves insufficient.
- Modify `docs/VERIFICATION.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, and
  `docs/index.html`: align the recipe and dashboard state with the new regen
  directory and GAP-012 closure.
- Append `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

## Tasks

### Task 1: Regression Tests First

**Files:**
- Modify: `tests/test_pipeline_gaps.py`

- [ ] Add `test_pipeline_missing_bronze_root_raises_before_gold_write`.
      It should call `pipeline.run_pipeline()` with
      `bronze_root=tmp_path / "does-not-exist" / "bronze"`, `news=0`,
      `skip_news_extraction=True`, and a tmp output path. Expected RED before
      implementation: no exception and an empty parquet is written.
- [ ] Add `test_pipeline_empty_local_bronze_root_raises_before_gold_write`.
      It should create an empty tmp `bronze/` directory, run the same local
      pipeline path, and expect a clear `ValueError`.
- [ ] Add `test_live_check_nesting_contract_means_parent_bronze_is_absent`.
      It should create `<tmp>/local-stats-bronze/manifest.json`, run
      `run_live_check()` with a fake collector that lands one raw artifact, and
      assert the manifest is under `<out>/<run_id>/manifest.json`,
      `<out>/bronze` is absent, and `<out>/<run_id>/bronze` exists.
- [ ] Run the new focused tests and confirm the missing/empty root tests fail
      for the current behavior.

### Task 2: Pipeline Guard

**Files:**
- Modify: `src/railway_lakehouse/pipeline.py`

- [ ] Add `_validate_local_bronze_root(bronze_root: Path) -> Path` that raises
      `FileNotFoundError` if the path does not exist and `NotADirectoryError` if
      it is not a directory. The error must include `--bronze-root`, the path via
      `as_posix()`, and a hint to run
      `python -m railway_lakehouse.bronze.live_check ... --out <dir>` then pass
      `<dir>/bronze`.
- [ ] In `run_pipeline()`, call the validator before constructing the local
      lander.
- [ ] Read Bronze articles before Gold writing and call
      `_validate_non_empty_local_inputs()` when local Bronze mode is used.
      Raise `ValueError` when both the stats frame list and article list are
      empty.
- [ ] Keep Gold builder semantics unchanged so library callers can still build
      empty frames deliberately.
- [ ] Run the focused tests until they pass.

### Task 3: Documentation and Dashboard Sync

**Files:**
- Modify: `docs/VERIFICATION.md`
- Modify: `docs/GAP_REGISTER.md`
- Modify: `docs/TASKS.md`
- Modify: `docs/index.html`

- [ ] Rewrite the verification recipe to use
      `output/evidence/local-stats-bronze-regen` for live-check `--out`.
- [ ] Point pipeline `--bronze-root` at
      `output/evidence/local-stats-bronze-regen/bronze` while keeping
      `--max-artifacts 1 --timeout-seconds 60`,
      `--skip-news-extraction --news 0`, `--crosswalk-path`, and `--counts-out`.
- [ ] Keep the observed contract: 2,139 rows x 3 columns, columns
      `[geo, year, rail_network_length_km]`, AT and HU present, year range
      1995-2021.
- [ ] Explain that the committed `manifest.json` is an audit snapshot and raw
      Bronze is gitignored.
- [ ] Update the GAP_REGISTER command row and TASKS recipe references so paths
      cannot drift.
- [ ] Update the dashboard GAP-012 signal from urgent open blocker to closed
      guard/recipe status.

### Task 4: Verification, Live Evidence, and Handoff

**Files:**
- Modify: `docs/PROGRESS_LOG.md`
- Modify: `.planning/COURSEWORK_PROGRESS.md`

- [ ] Run `python -m pytest -q -m integration`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Run `git diff --check`.
- [ ] Run the documented clean-checkout regen using the new
      `local-stats-bronze-regen` directory and inspect `counts.json`.
- [ ] Run the negative CLI check against a missing `--bronze-root` and confirm
      non-zero exit without writing the target parquet.
- [ ] Record command outputs and any network caveats in the progress logs and
      verification docs.
- [ ] Commit, push `impl/gap-012`, and open a PR against `main`.

## Self-Review

- Spec coverage: every GAP-012 DoD item maps to a task above. The live-check
  nesting contract is preserved, the docs use a fresh regen directory, and the
  pipeline no longer silently emits empty Gold for a missing local root.
- Placeholder scan: no `TBD`/`TODO` placeholders remain in this plan.
- Scope check: no Bronze lander semantics, numeric merge logic, or LLM behavior
  changes are planned.

Approved for implementation by the implementing agent on 2026-06-24.
