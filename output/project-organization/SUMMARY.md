# Summary

Date: 2026-06-21

Task: create documentation structure and agent routing for `bigdata/course_proj`.

## What Was Done

- Added project-local `AGENTS.md` so future agents launched in this folder have immediate routing, hard rules, and module ownership guidance.
- Added `README.md` and `TASK.md` at the project root.
- Added a `docs/` documentation set:
  - `docs/INDEX.md`
  - `docs/CODEMAP.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DATA_CONTRACTS.md`
  - `docs/WORKSTREAMS.md`
  - `docs/AGENTIC_WORKFLOW.md`
  - `docs/VERIFICATION.md`
  - `docs/ORGANIZATION_PLAN.md`
  - `docs/PROGRESS_LOG.md`
- Added required research log at `.planning/coursework/research/bigdata/course-project-organization.md`.
- Added next-session planning docs:
  - `docs/NEXT_SESSION_HANDOFF.md`
  - `docs/TEST_FIRST_INTEGRATION_PLAN.md`
  - `docs/WORK_SPLIT.md`
  - `.planning/.continue-here.md`
  - `.planning/HANDOFF.json`
- Added repo hygiene and contributor files:
  - `pyproject.toml`
  - `.gitignore`
  - `CONTRIBUTING.md`
  - `docs/GAP_REGISTER.md`
- Added characterization tests under `tests/`.
- Migrated current code into one package root under `src/railway_lakehouse/`.
- Updated active docs for the new source layout and verification state.
- Added parser collaboration log:
  - `docs/PARSER_WORK_LOG.md`
- Ran a bounded real-data parser check and stored evidence under:
  - `output/evidence/parser-live-check-2026-06-21/`

## Current Project Read

- `src/railway_lakehouse/bronze/` is the consolidated Bronze ingestion package.
- `src/railway_lakehouse/silver/` contains Silver stats/news transformation logic.
- `src/railway_lakehouse/gold/` contains deterministic Gold feature-building logic.
- The end-to-end pipeline is not yet wired because `src/railway_lakehouse/pipeline.py` still has Bronze read stubs.
- Automated tests and dependency metadata now exist.
- Bounded live parser evidence now exists for selected Bronze sources.
- No live MinIO/Ollama or Spark evidence has been produced.

## Status

GitHub-ready scaffold and initial `src/railway_lakehouse` migration are complete. Parser collaboration state is documented in `docs/PARSER_WORK_LOG.md`. Runtime wiring is intentionally left as documented gaps. Next step: fix Wave 1 parsers and convert the bounded live probe into a repo command.

## Evidence

- `python -m pip install --no-cache-dir -e ".[test]"` passed.
- `python -m pytest -q -m unit` passed: 15 passed, 1 deselected.
- `python -m pytest -q` passed: 15 passed, 1 xfailed.
- `python -m pip check` passed.
- Bounded live parser manifest exists: `output/evidence/parser-live-check-2026-06-21/manifest.json`.
- Live-ok parser evidence: RSS Telex/Index feeds and one KSH STADAT XLSX.
- Partial/failed parser evidence is documented for Eurostat, World Bank, GDELT, Statistics Austria, UIC, and GDELT history.
