# GAP-050 LLM Pipeline Engineering Implementation Plan

Goal: turn the current Silver news LLM loop into a deliberately engineered, cached, observable extraction runner for GAP-033, without widening scope beyond the existing GAP-039 `NewsFeature` contract.

Architecture: keep `generate_json()` as the mocked Ollama seam and keep `extract_batch()` backward-compatible. Add a small runner inside `silver/news/extract.py` that performs cache-skip, sequential batch processing, retry/backoff, typed failure accounting, optional warm-up/unload lifecycle hooks, and a run manifest. Tighten the prompt to the narrowed LLM-owned fields while preserving the existing `NewsFeature` validator and schema.

Tech stack: Python dataclasses, stdlib JSON/path/time/subprocess, existing `FileSystemCache`, existing `NewsFeature` validation, pytest with monkeypatch/tmp_path fixtures.

## Refined Spec

Local code review found the drafted spec stale in three places:

- GAP-039 already added content-hash cache, `extract_batch()` success/failure return values, and a JSON failure sidecar helper. GAP-050 should integrate and harden these, not rebuild them.
- `NewsFeature` does not contain `monetary_currency`; deterministic FX is explicitly deferred in `docs/SPEC_NEWS_PREPROCESSING.md`. GAP-050 will document the target but only persist existing fields: `monetary_raw` and `monetary_amount_eur`, with EUR populated only when the article explicitly states EUR/equivalent.
- GAP-043's collapsed event taxonomy is an evaluation-gate plan, not a current Silver storage contract. The extractor must continue writing the canonical `NEWS_EVENT_TYPES` enum and document later eval collapse as report-only/gated mapping.

## Files

- Modify `src/railway_lakehouse/silver/config.py`: add prompt/lifecycle config and change default `OLLAMA_NUM_CTX` to 4096 per owner GPU evidence.
- Modify `src/railway_lakehouse/silver/ollama_client.py`: pass `keep_alive` and optional `num_batch`.
- Modify `src/railway_lakehouse/silver/news/cache.py`: include `NEWS_EXTRACTION_PROMPT_VERSION` and new prompt/schema details in `model_digest_key()`.
- Modify `src/railway_lakehouse/silver/news/failures.py`: add optional raw payload field and run-manifest persistence helper.
- Modify `src/railway_lakehouse/silver/news/extract.py`: narrow prompt/schema, add runner, retry, manifest metrics, lifecycle hooks.
- Add `tests/test_silver_news_extract_prompt.py`: unit tests for prompt shape, digest invalidation, retries, failure raw, manifest.
- Extend `tests/test_silver_news_extraction_e2e.py`: integration-style tmp_path pipeline manifest/sidecar round trip with mocked `generate_json`.
- Add `docs/LLM_EXTRACTION_DESIGN.md`: design and operations documentation.
- Update `.planning/coursework/research/bigdata/llm-pipeline-engineering-gap050.md`, docs dashboard files, and progress logs.

## Tasks

1. Write failing unit tests for the narrowed prompt/schema: assert system/user split exists, prompt includes snippet/fulltext trust, schema excludes LLM-owned-out fields (`sentiment`, `language`, `operators`, `rail_lines`), and `NEWS_EXTRACTION_PROMPT_VERSION` affects `model_digest_key()`.
2. Write failing unit tests for runner behavior: mocked `generate_json` returns `None` then valid JSON, runner retries without live Ollama; persistent malformed output yields an `ExtractionFailure` with reason and raw; run manifest records processed/cache/failed/latency/prompt version.
3. Implement config and Ollama payload updates.
4. Implement prompt/schema rewrite and digest update.
5. Implement runner and keep `extract_article_cached()`, `extract_article()`, and `extract_batch()` return contracts intact.
6. Add integration test coverage with tmp_path cache/manifest/failure sidecar and mocked model.
7. Document the design, scope corrections, and source-backed API claims.
8. Sync `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/PROGRESS_LOG.md`, and `.planning/COURSEWORK_PROGRESS.md`.
9. Verify with `python -m pytest -q -m unit tests/test_silver_news_extract_prompt.py`, `python -m pytest -q`, `python -m compileall -q src tests`, then commit, push, and open a PR against `main`.

## Self-Review

Spec coverage: every GAP-050 DoD item maps to a task above. The live run itself is deliberately out of scope and remains GAP-033.

Placeholder scan: no TODO/TBD implementation placeholders are left in this plan.

Type consistency: runner returns `ExtractionRunResult(features, failures, manifest)` while legacy functions return their current values.

Approval: self-approved for implementation on 2026-06-25 after local code review and routed external research.
