# Contributing

This repository is the standalone Big Data course project root. Work from `bigdata/course_proj`.

## Setup

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

Use Python 3.12 or newer.

## Test Policy

- Run deterministic unit tests before opening or merging a change:

```bash
python -m pytest -q -m unit
```

- Live collectors, Spark jobs, MinIO, and Ollama checks must be opt-in with `live`, `spark`, `integration`, or `slow` markers.
- Do not run long live collectors until the deterministic fixture E2E path exists.
- An expected failure must reference a gap ID from `docs/GAP_REGISTER.md`.

## Gap Workflow

Every gap needs:

- gap ID,
- owner workstream,
- expected behavior,
- files likely to change,
- closure criteria,
- verification command.

Close a gap only after the verification command has run and the result is recorded in `docs/GAP_REGISTER.md` and `docs/PROGRESS_LOG.md`.

## Evidence Rules

- Do not claim real data, Spark, MinIO, or Ollama works unless the command was actually run.
- Public evidence belongs under `output/evidence/`.
- Runtime scratch data belongs under `output/runtime/` and is ignored.
- Do not commit secrets. Mention environment variable names only.

## Architecture Boundaries

- Bronze lands raw source bytes and metadata only.
- Silver parses, validates, normalizes, and records provenance.
- Gold produces analysis-ready feature matrices.
- Spark jobs and report/presentation claims must use generated evidence.
