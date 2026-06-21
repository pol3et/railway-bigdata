# Next Session Handoff

Last updated: 2026-06-21

## Mission

Continue from the GitHub-ready scaffold and single-package migration.

The next useful session should build the deterministic fixture E2E path before any long live collectors:

1. Implement fixture-backed Bronze reads for `src/railway_lakehouse/pipeline.py`.
2. Add an integration test that exercises Bronze fixture -> Silver -> Gold.
3. Write fixture evidence under `output/evidence/fixture-e2e/` only after the command runs.
4. Keep live MinIO/Ollama/Spark checks opt-in.

## Current State

Project root:

```text
bigdata/course_proj/
```

Current package root:

```text
src/railway_lakehouse/
```

Done:

- `pyproject.toml`, `.gitignore`, and `CONTRIBUTING.md` exist.
- `docs/GAP_REGISTER.md` exists and maps test failures to gap IDs.
- Bronze, Silver, Gold, and pipeline code were migrated under `src/railway_lakehouse`.
- Characterization tests exist for Bronze, Silver, and Gold.
- Editable install passes.
- Unit tests pass.
- Full pytest passes with one strict expected failure for GAP-004.

Still open:

- GAP-004: pipeline Bronze read stubs are not wired.
- GAP-005: KSH/Statistik Austria/UIC/history adapters are not scheduled by Bronze runner.
- GAP-006: Silver persistence/storage boundary is not wired.
- GAP-007: Gold storage loading boundary is not wired.
- GAP-009: no Spark job exists yet.
- GAP-010: no generated fixture/live dataset evidence yet.
- GAP-011: report and presentation are not started.

## Required Reading

1. `AGENTS.md`
2. `README.md`
3. `docs/GAP_REGISTER.md`
4. `docs/VERIFICATION.md`
5. `docs/CODEMAP.md`
6. `docs/DATA_CONTRACTS.md`
7. `docs/PROGRESS_LOG.md`
8. `.planning/coursework/research/bigdata/course-project-organization.md`

## Verification To Run First

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

Expected current result:

- 15 passed.
- 1 xfailed: `tests/test_pipeline_gaps.py::test_pipeline_storage_read_stubs_are_not_wired` for GAP-004.

## Do Not Start With

- Do not run long live collectors.
- Do not claim real data, MinIO, Ollama, or Spark works without executed evidence.
- Do not close a gap without updating `docs/GAP_REGISTER.md` and `docs/PROGRESS_LOG.md`.

## Next Action

Create a deterministic fixture E2E for GAP-004:

```bash
python -m pytest -q -m integration
```

The test should use tiny local fixtures and mocked Ollama output, not live services.
