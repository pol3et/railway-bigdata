# GAP-045 Macro Indicators Implementation Plan

Status: self-reviewed and approved on 2026-06-25.

Goal: Add the two requested World Bank macro indicator ids to the Bronze selector and deterministic Silver/Gold mapping, while recording the live API coverage caveat for `IS.VEH.PCAR.P3`.

Architecture:

- Bronze remains immutable and only lands raw World Bank JSON.
- Silver keeps numeric values verbatim; only source indicator ids map by deterministic dictionary to canonical keys.
- Gold remains the existing long-to-wide pivot; no feature engineering or LLM is added.

Approved spec refinements:

- `PA.NUS.PPP` is active and has AT/HU coverage in the live World Bank V2 API.
- `IS.VEH.PCAR.P3` is present in World Bank metadata but current V2 API data for the repository's collection URL has no AT/HU observations; DataBank says the data were removed from external publication pending IRF licensing review. The live evidence will report this coverage gap instead of claiming car values for AT/HU.
- `IS.VEH.NVEH.P3` is not added.
- Existing Eurostat canonical keys `cars_per_1000_inhabitants` and `ppp_factor` are left untouched; the requested World-Bank-specific keys `cars_per_1000` and `ppp_conversion_factor` are added.

Tasks:

1. Add tests first.
   - Create `tests/test_macro_indicators.py`.
   - Unit test: build tiny World Bank JSON fixtures for `IS.VEH.PCAR.P3` and `PA.NUS.PPP`, pass them through `load_worldbank_frame`, `build_crosswalk`, and `merge_sources`, and assert numeric AT/HU rows map to `cars_per_1000` and `ppp_conversion_factor`.
   - Integration test: write the same fixtures into a tmp_path Bronze tree, run `build_silver_stats`, build Gold, and assert both columns exist with AT/HU values. This is deterministic and uses no live network.
   - Run the new tests before production changes and confirm they fail because mappings/features are missing.

2. Implement the minimal mapping changes.
   - Add `IS.VEH.PCAR.P3` and `PA.NUS.PPP` to `EU_STATS_INDICATORS`.
   - Add `cars_per_1000` and `ppp_conversion_factor` to `CANONICAL_FEATURES`.
   - Add both ids to `_WB_INDICATOR_FEATURE`.
   - Do not touch Eurostat rules, rail indicators, raw Bronze semantics, or numeric parsing.

3. Verify deterministic tests.
   - Run the new test file.
   - Run the task verify command.
   - Run `python -m pytest -q -m unit`, `python -m pytest -q`, and `python -m compileall -q src tests`.

4. Run bounded live evidence.
   - Run World Bank-only live check into `output/evidence/macro-indicators-gap045/` with enough artifacts to include the new indicators.
   - Run the pipeline from that local Bronze root to `output/evidence/macro-indicators-gap045/railway_ml.parquet`.
   - Write an evidence summary JSON under the same output directory with column names and AT/HU non-null counts for `cars_per_1000` and `ppp_conversion_factor`.
   - Treat `cars_per_1000` AT/HU count `0` as an upstream coverage fact, not a successful AT/HU signal.

5. Update docs/dashboard.
   - Update `README.md`, `docs/STATE_AND_ROADMAP.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`, and if needed `docs/GAP_TASKS.md` to reflect the implemented mapping and live coverage caveat.

6. Publish.
   - Inspect `git diff` and `git status`.
   - Stage only this gap's files, commit, push `impl/gap-045`, and open a PR against `main`.
   - Verify PR mergeability with `gh pr view`.

Self-review:

- Scope is limited to GAP-045.
- The plan includes the required research record, tests, live evidence, docs/dashboard sync, progress logs, and PR.
- The only spec change is a narrowing forced by live World Bank API evidence for `IS.VEH.PCAR.P3`; no alternate source or new analysis path is introduced.
