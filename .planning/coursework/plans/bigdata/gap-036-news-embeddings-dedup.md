# GAP-036 News Embeddings + Dedup Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: use the TDD cycle. Write RED tests before production code. This plan is scoped to GAP-036 only.

Date: 2026-06-25
Status: approved by implementing agent after self-review

## Refined Spec

The user-supplied draft was stale against the live repo:

- `NewsFeature` is not a 15-field dataclass anymore. GAP-039 already widened it to 43 fields with `text_embedding_model`, `text_embedding`, `cluster_id`, and `cross_lingual_dedup_id`.
- The current reviewed docs reject LaBSE as the default embedder. The project default is `intfloat/multilingual-e5-base`, with BGE-M3 swappable later.
- Adding duplicate `embedding` and `dedup_group_id` columns would conflict with the existing DATA_CONTRACTS field list.

Implementation target:

- Populate existing `text_embedding_model` and `text_embedding`.
- Change `text_embedding` Arrow storage from `list<float64>` to `list<float32>`.
- Add `is_duplicate: Optional[bool] = None` at the end of `NewsFeature`.
- Use `cross_lingual_dedup_id` as the deterministic near-duplicate group id.
- Keep Gold numeric/stat logic unchanged. Dedup enforcement in Gold/Spark remains GAP-037/GAP-040 follow-up.

## Files

Create:
- `src/railway_lakehouse/silver/news/embeddings.py`
- `tests/test_silver_news_embeddings.py`
- `tests/test_silver_news_embeddings_integration.py`

Modify:
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/silver/persist.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `pyproject.toml`
- `tests/test_silver_news_wide_contract.py`
- `tests/test_silver_persist.py`
- `tests/test_silver_persist_integration.py`
- `tests/test_gold_load_from_silver.py`
- `docs/DATA_CONTRACTS.md`
- `docs/SILVER_DESIGN.md`
- `docs/STATE_AND_ROADMAP.md`
- `docs/TASKS.md`
- `docs/index.html`
- `docs/GAP_REGISTER.md`
- `docs/PROGRESS_LOG.md`
- `.planning/COURSEWORK_PROGRESS.md`

## Work Plan

### Task 1: RED Tests

Write unit tests for:
- embedding model loader cache using a fake `SentenceTransformer` module injected into `sys.modules`;
- `embed_text()` returns a float list, prefixes article text with `passage: ` for e5, and handles `None`/empty text;
- `compute_embeddings()` skips rows that already have `text_embedding`, skips when `use_model=False`, and writes `text_embedding_model`;
- `cluster_near_duplicates()` groups identical vectors, is shuffle-invariant, sets `cross_lingual_dedup_id`, and marks only non-canonical rows as `is_duplicate=True`;
- missing SciPy degradation returns rows unchanged with dedup fields null and logs a warning.

Write integration tests for:
- real `sentence_transformers` import is gated with `pytest.importorskip`;
- a tiny HU/DE/EN translated-story fixture embeds and clusters when the dependency/model is available.

Run expected RED command:
- `python -m pytest -q tests/test_silver_news_embeddings.py -v`

### Task 2: Schema + Persistence

Implement:
- Add `is_duplicate` to `NewsFeature`.
- Validate/coerce `text_embedding_model`, `text_embedding`, `cross_lingual_dedup_id`, `is_duplicate`.
- Change `NEWS_FEATURE_ARROW_SCHEMA` `text_embedding` to `pa.list_(pa.float32())`.
- Add `is_duplicate` as `pa.bool_()`.
- Preserve old-Parquet backfill through existing `load_news().reindex(...)`.

Verify with:
- `python -m pytest -q tests/test_silver_news_wide_contract.py tests/test_silver_persist.py -v`

### Task 3: Embedding Helper + Extraction Wiring

Implement `silver/news/embeddings.py`:
- `DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-base"`
- `load_embedding_model(model_name=DEFAULT_EMBEDDING_MODEL)` with `functools.lru_cache`.
- `embed_text(text, model)` with empty-input guard, `passage: ` prefix for e5 models, `normalize_embeddings=True`, and Python `float` list output.
- `compute_embeddings(news_rows, use_model=True, model_name=DEFAULT_EMBEDDING_MODEL)` that handles dataclasses and dicts without changing object type.
- `cluster_near_duplicates(news_rows, threshold=0.95)` using SciPy if available and deterministic connected components over sorted article ids.

Wire:
- In `extract_batch()`, call `compute_embeddings(result.features, use_model=True)` after extraction.
- Gracefully skip embeddings if the optional dependency/model is unavailable, logging a warning rather than failing extraction.

Verify with:
- `python -m pytest -q tests/test_silver_news_embeddings.py tests/test_silver_news_parsers.py -v`

### Task 4: Docs + Dashboard

Update:
- `docs/DATA_CONTRACTS.md` with embedding/dedup semantics and float32 storage.
- `docs/SILVER_DESIGN.md` with e5-base embedding note.
- `docs/STATE_AND_ROADMAP.md`, `docs/TASKS.md`, `docs/index.html`, and `docs/GAP_REGISTER.md` to mark GAP-036 closed/in progress with evidence.
- Append handoff entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

### Task 5: Verification + PR

Run:
- `python -m pytest -q tests/test_silver_news_embeddings.py -v`
- `python -m pytest -q -m integration tests/test_silver_news_embeddings_integration.py -v`
- `python -m pytest -q -m integration tests/test_silver_persist_integration.py -v`
- `python -m pytest -q`
- `python -m compileall -q src tests`
- `python -c "from railway_lakehouse.silver.schema import NewsFeature; nf = NewsFeature(article_id='a1', source='test', url='', published_date=None, language=None, is_rail_related=False, country=None, event_type='other'); assert hasattr(nf, 'text_embedding') and hasattr(nf, 'cross_lingual_dedup_id') and hasattr(nf, 'is_duplicate')"`

Then:
- Commit all scoped changes.
- Push branch `impl/gap-036`.
- Open PR against `main`.
- Confirm mergeability with `gh pr view`.

## Self-Review

Spec coverage:
- Embedding storage, model loading, idempotent embedding fill, deterministic dedup, backwards Parquet compatibility, docs/dashboard sync, and verification commands are covered.

Scope guard:
- No Bronze changes.
- No Gold numeric/stat merge changes.
- No Spark implementation in this gap.
- No extra columns beyond `is_duplicate`; existing GAP-039 fields are reused.

Type consistency:
- `text_embedding` is the persisted list field.
- `cross_lingual_dedup_id` is the group id.
- `is_duplicate` is the duplicate marker.

Approval:
- Approved for implementation as the scoped GAP-036 contract.
