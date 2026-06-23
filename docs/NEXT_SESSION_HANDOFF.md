# Next Session Handoff

Last updated: 2026-06-23

## Mission

Continue from the GitHub-ready scaffold, single-package migration, and merged
PR #9 / PR #10 Silver fixture slices.

The deterministic fixture E2E path is implemented. The next useful session
should finish the remaining Silver persistence/parser boundaries before Spark
work:

1. Decide the canonical persisted Silver stats/news output paths.
2. Wire Gold loading from persisted Silver for GAP-007.
3. Implement remaining GAP-006 parsers if needed: KSH XLSX, Statistik Austria
   `.ods`, and UIC public PDF/subscribed export.
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
- PR #10 Silver Stats slice is merged: Eurostat TSV(.gz) and World Bank JSON
  Bronze fixtures become `StatFact` rows with Parquet persistence,
  provenance, unmapped-label visibility, and correct `AUT -> AT`
  normalization.
- PR #9 Silver News slice is merged: RSS XML and GDELT ArtList JSON become
  `ArticleRecord` rows with stable IDs, and RSS XML fixtures are wired into
  local `_read_bronze_news()`.

Still open:

- GAP-005: KSH/Statistik Austria/UIC/history adapters are not scheduled by Bronze runner.
- GAP-006: remaining persisted Silver boundary and non-Eurostat/World Bank
  stats parsers are not complete.
- GAP-007: Gold storage loading boundary is not wired.
- GAP-009: no Spark job exists yet.
- GAP-010: local MinIO object-storage path is verified by `output/evidence/minio-smoke/manifest.json`; full persisted Bronze/Silver/Gold through MinIO is still not complete.
- GAP-011: report and presentation are not started.

Merged teammate slices:

- PR #9 `silver/news-parsers`: GAP-006 Silver News/RSS+GDELT article-record slice.
- PR #10 `silver/stats-worldbank-eurostat`: GAP-006 Silver Stats World Bank/Eurostat slice.
- Neither merged slice closes GAP-007 because Gold still must load persisted
  Silver outputs and record Gold evidence.

Ollama model decision:

- Default local model is `qwen3.5:9b-q8_0`, replacing both the older
  `llama3.1:8b` placeholder and the interim `qwen3:8b` choice.
- Use `OLLAMA_MODEL=qwen3.5:9b-q4_K_M` when the 11 GB Q8_0 model is too large.
- The Ollama client uses `/api/chat` with schema `format`, deterministic
  options, and top-level `think: false` by default.
- LLM use remains bounded to cached label mapping and validated article
  extraction; numeric rows stay deterministic.

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

- `python -m pytest -q` passed: 74 passed.
- `python -m compileall -q src tests` passed.
- `git diff --check` passed.

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
