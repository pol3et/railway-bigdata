# GAP-039 NewsFeature Wide Contract Implementation Plan

Status: self-reviewed and approved on 2026-06-25.

Goal: add the Silver news wide article-grain schema and idempotent extraction cache contract without running live models or widening the LLM prompt.

## Refined Scope

- Keep the old 15 `NewsFeature` fields backward-compatible and append the wide fields from the GAP-039 spec. The draft says "15 + 13 = 28" but also lists 28 new fields; the code will implement the listed fields and require `len(NewsFeature.__dataclass_fields__) >= 28`.
- Use current repo defaults from `silver/config.py`: `OLLAMA_MODEL` defaults to `qwen3:4b`, not the stale Qwen 9B wording in the draft.
- Respect `docs/SPEC_NEWS_PREPROCESSING.md`: embedding model names are placeholders for GAP-036 and should include the e5/bge-m3 direction, not make LaBSE binding.
- Do not calculate a real model weight digest. `model_digest_key()` hashes the model/config/prompt/schema identity string for cache invalidation only.
- Do not persist extraction failures as a Parquet table in this gap. Add typed failures, logging, and a JSON sidecar helper. Leave Parquet failure-table persistence to GAP-006/GAP-050.
- Do not add new requested fields to the LLM prompt. GAP-039 reserves schema columns and cache behavior; GAP-031 through GAP-038 populate model-specific fields later.
- Keep Bronze immutable. No Bronze parser edits except read-only use of existing fixtures.

## Tasks

1. Add RED tests in `tests/test_silver_news_wide_contract.py`.
   - Schema/backward-compat construction.
   - `validate_news_feature()` coercion for language/confidence/sentiment/GKG fields.
   - `extract_cache_key()` and `model_digest_key()`.
   - `FileSystemCache` manifest, hit/miss stats, JSON round-trip.
   - Cached extraction call counts and GDELT passthrough.
   - `extract_batch()` success/failure tuple.
   - Parquet round-trip using `persist.persist_news()` / `persist.load_news()`.

2. Add RED integration test in `tests/test_silver_news_extraction_e2e.py`.
   - Parse fixture RSS and GDELT records.
   - Run cached extraction into a `tmp_path` cache and persist to a `tmp_path` Silver root.
   - Assert first run calls mocked Ollama, second run reuses cache, new ingest date reuses unchanged article cache, and failure JSON sidecar can be written for failures.

3. Implement schema and validation in `src/railway_lakehouse/silver/schema.py`.
   - Append wide optional fields plus `confidence_schema_version="1.0"`.
   - Add validators for ISO 639-1, confidence clamps, signed sentiment score, GKG empty strings, embedding float lists, and legacy rows.

4. Implement cache and failures.
   - New `src/railway_lakehouse/silver/news/cache.py`: `extract_cache_key`, `model_digest_key`, `CacheBackend`, `NoOpCache`, `FileSystemCache`.
   - New `src/railway_lakehouse/silver/news/failures.py`: `ExtractionFailure`, `persist_news_failures()` JSON sidecar.
   - Add `.news_extraction_cache` to `.gitignore`.

5. Update `src/railway_lakehouse/silver/news/extract.py`.
   - Add `extract_article_cached(article, cache)` and `gdelt_passthrough_cached(gkg, cache)`.
   - Keep `extract_article()` wrapper for current tests and callers.
   - Change `extract_batch()` to return `(successes, failures)`.
   - Keep `article_records_to_news_features()` returning successes only for current `rss_records_to_news_features()` compatibility.

6. Update persistence and callers.
   - Extend `NEWS_FEATURE_ARROW_SCHEMA` and `_news_frame()` in `silver/persist.py`.
   - Add `persist_news_failures()` wrapper that delegates to the JSON sidecar helper.
   - Update `pipeline.py` and `silver/run.py` to unpack `(successes, failures)` and log failure counts.

7. Update docs and dashboard.
   - `.planning/coursework/research/bigdata/newsfeature-wide-contract.md`.
   - `docs/DATA_CONTRACTS.md` Silver News section with field order and cache contract.
   - `README.md` News Feature Extraction section and stale Ollama default correction.
   - `docs/TASKS.md`, `docs/index.html`, `docs/GAP_REGISTER.md`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`.

8. Verify and ship.
   - `python -m pytest -q -m unit tests/test_silver_news_wide_contract.py`
   - `python -m pytest -q -m integration tests/test_silver_news_extraction_e2e.py`
   - `python -m pytest -q`
   - `python -m compileall -q src tests`
   - Import/field-count check from the user spec.
   - Commit, push `impl/gap-039`, open PR against `main`, confirm mergeability.

## Self-Review

- Spec coverage: every GAP-039 DoD item is represented except the contradictory Parquet failure-table step, which is explicitly narrowed by the supplied pitfall.
- Scope guard: no live Ollama, no Spark job, no Gold aggregation widening, no Bronze parser widening, no new model extractors.
- Type consistency: tests target current dataclasses, `persist.py` Arrow schemas, and existing mocked `generate_json` seam.
- Approval: approved for implementation.
