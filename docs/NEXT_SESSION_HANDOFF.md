# Next Session Handoff

Last updated: 2026-06-22

## Mission

Continue from the GitHub-ready scaffold and single-package migration.

The deterministic fixture E2E path is now implemented. The next useful session should define persisted Silver/Gold artifact contracts before Spark work:

1. Let active teammate branches finish their GAP-006 slices:
   `silver/news-rss-article-records` and `silver/stats-worldbank-eurostat`.
2. Decide where their fixture Silver stats/news outputs should be written.
3. Wire Gold loading from persisted Silver for GAP-007.
4. Keep live MinIO/Ollama/Spark checks opt-in until evidence commands are explicit.

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
- Full pytest passes with no expected xfail.
- GAP-004 fixture-backed Bronze reads are closed and evidenced at `output/evidence/fixture-e2e/railway_ml.parquet`.

Still open:

- GAP-005: KSH/Statistik Austria/UIC/history adapters are not scheduled by Bronze runner.
- GAP-006: Silver persistence/storage boundary is not wired.
- GAP-007: Gold storage loading boundary is not wired.
- GAP-009: no Spark job exists yet.
- GAP-010: fixture evidence exists; full live Bronze/Silver/Gold evidence is not complete.
- GAP-011: report and presentation are not started.

Active teammate branch mapping:

- `silver/news-rss-article-records`: GAP-006 Silver News/RSS article-record slice.
- `silver/stats-worldbank-eurostat`: GAP-006 Silver Stats World Bank/Eurostat slice.
- Neither branch closes GAP-007 unless it also wires Gold loading and records Gold evidence.

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

- 56 passed.

## Do Not Start With

- Do not run long live collectors.
- Do not claim real data, MinIO, Ollama, or Spark works without executed evidence.
- Do not close a gap without updating `docs/GAP_REGISTER.md` and `docs/PROGRESS_LOG.md`.

## Next Action

Continue with minimal persistence work:

```bash
python -m pytest -q -m integration
```

The current fixture E2E uses tiny local fixtures and mocked Ollama output in tests. The CLI evidence run uses `--skip-news-extraction` to stay service-free.
