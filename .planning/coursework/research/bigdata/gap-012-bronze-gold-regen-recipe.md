# GAP-012 Bronze to Gold Regen Recipe Research

Date: 2026-06-24

Scope: repo-local research for GAP-012 only. No external API/library claims were
needed; the work uses current repository code, docs, tests, and bounded command
output.

## Local Files Checked

- `src/railway_lakehouse/bronze/live_check.py`
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/stats/load.py`
- `src/railway_lakehouse/gold/run.py`
- `src/railway_lakehouse/gold/build.py`
- `tests/test_bronze_live_check.py`
- `tests/test_pipeline_gaps.py`
- `docs/VERIFICATION.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `.gitignore`
- `output/evidence/local-stats-bronze/manifest.json`

## Findings

- `.gitignore` ignores `output/evidence/**/bronze/`, but not the committed
  `output/evidence/local-stats-bronze/manifest.json`.
- `git ls-files output/evidence/local-stats-bronze/*` returns only
  `output/evidence/local-stats-bronze/manifest.json`.
- `live_check._resolve_run_output_dir()` keeps the output root only when neither
  `<out>/manifest.json` nor `<out>/bronze` exists. If either exists it writes a
  new run directory under `<out>/<run_id>/`.
- `tests/test_bronze_live_check.py::test_run_live_check_uses_run_subdirectory_when_output_already_has_evidence`
  pins that nesting behavior, so the fix must not change Bronze landing
  semantics.
- `pipeline.run_pipeline()` currently accepts any local `--bronze-root`, builds
  frames through `silver.stats.load.frames_from_bronze()`, and proceeds even when
  that path does not exist.
- `silver.stats.load.frames_from_bronze()` skips missing source directories and
  returns an empty list for a missing root.
- `gold.run.build_from_silver()` only logs a warning for an empty Gold table.
  The pipeline boundary needs to prevent the documented recipe from writing an
  empty headline parquet; the pure Gold builder can remain importable and
  permissive.

## Red-State Evidence

Scratch clean-checkout simulation:

- Copied the committed manifest into
  `output/runtime/gap-012-red/local-stats-bronze/manifest.json`.
- First bounded live check showed the same nesting contract but hit a transient
  Eurostat failure. The output path was
  `output/runtime/gap-012-red/local-stats-bronze/live-check-20260623-234825/manifest.json`.
- A bounded retry passed with Eurostat and World Bank:
  `python -m railway_lakehouse.bronze.live_check --sources eurostat,worldbank --out output/runtime/gap-012-red/local-stats-bronze --max-artifacts 1 --timeout-seconds 60`
  wrote 4 artifacts, 14,996,995 bytes, and manifest
  `output/runtime/gap-012-red/local-stats-bronze/live-check-20260623-234844/manifest.json`.
- Running the old hardcoded pipeline path against the non-existent
  `output/runtime/gap-012-red/local-stats-bronze/bronze` exited 0 and wrote
  `output/runtime/gap-012-red/empty-gold/counts.json` with:
  `rows=0`, `columns=0`, `column_names=[]`.

## Decision

Keep the `live_check` run-id nesting semantics. Fix the documented recipe to use
a fresh regeneration directory, `output/evidence/local-stats-bronze-regen`, so
the live-check writes directly to `<regen>/bronze` and the pipeline reads that
same path.

Add a durable pipeline guard so a missing local `--bronze-root` raises before
Gold writing, and a local root that yields no stats frames and no news articles
also raises instead of emitting an empty parquet.
