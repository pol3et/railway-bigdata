# Organization Plan

This plan turns the current dump into a clean course-project repo without losing work.

## Phase 0 - Documentation Scaffold

Status: in progress.

Deliverables:

- `AGENTS.md`
- `README.md`
- `TASK.md`
- `docs/`
- `output/project-organization/`

No code moves in this phase.

## Phase 1 - Freeze Current Behavior

Goal: make the existing state testable before reorganizing.

Tasks:

- Add dependency manifest.
- Add compile/test command.
- Add tests for pure Silver/Gold logic.
- Add a tiny fixture path for Bronze/Silver/Gold smoke.
- Capture current import failures or missing dependencies.

## Phase 2 - Consolidate Bronze

Goal: one Bronze package, not two competing locations.

Tasks:

- Done 2026-06-21: existing Bronze code moved into `src/railway_lakehouse/bronze`.
- Wire KSH, Statistik Austria, UIC, and historical GDELT modules into the scheduler.
- Preserve `RawArtifact`/`RawLander` contract.
- Update imports and docs.

Requires explicit plan before file moves.

## Phase 3 - Wire Storage Boundaries

Goal: wire storage boundaries in the end-to-end driver.

Tasks:

- Done 2026-06-22: implement deterministic fixture-backed Bronze reads for Eurostat/raw stats.
- Done 2026-06-22: implement deterministic fixture-backed Bronze reads for JSON news records.
- Write Silver outputs to a documented storage path.
- Let Gold load from Silver storage.
- Produce a small reproducible smoke output.

## Phase 4 - Add Big Data / Spark Jobs

Goal: satisfy the Big Data technology requirement with real evidence.

Tasks:

- Add Spark job entrypoints.
- Read Gold/Silver Parquet.
- Generate analysis outputs and row-count evidence.
- Keep jobs small enough for local smoke and scalable enough for course story.

## Phase 5 - Report And Presentation

Goal: final student-facing deliverables grounded in generated outputs.

Tasks:

- Write short report.
- Build presentation.
- Include data source counts, row counts, feature coverage, charts/tables, and practical findings.

## Phase 6 - Final Audit

Goal: verify no unsupported claims remain.

Tasks:

- Run documented checks.
- Compare deliverables against `TASK.md`.
- Ensure `docs/PROGRESS_LOG.md` links evidence.
- Ensure no secrets or runtime scratch files are in public docs.
