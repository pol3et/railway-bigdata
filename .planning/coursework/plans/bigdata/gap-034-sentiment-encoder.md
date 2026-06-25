# GAP-034 Sentiment Encoder Implementation Plan

Status: self-reviewed and approved on 2026-06-25.

Goal: replace LLM-derived news sentiment with a deterministic, pinned CardiffNLP XLM-R sentiment post-pass while preserving the existing `NewsFeature` field order and cache/persist contracts.

Refined scope after live-code review:

- GAP-050 already removed `sentiment`, `language`, `operators`, and `rail_lines` from the LLM prompt/schema. GAP-034 will not redo that work.
- The stale draft revision `59b7eda` is wrong. The verified model revision is `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8`.
- The model is multilingual and fine-tuned on EN/DE plus six other languages; HU is a transfer use case. No HU quality claim will be made without a later evaluation gap.
- The current wide contract already has `sentiment_label`, `sentiment_score`, and `sentiment_confidence`. GAP-034 will populate those fields and legacy `sentiment`/`confidence` without adding new dataclass fields.
- Gold will prefer signed `sentiment_score` and fall back to the label map for historical rows.

Files:

- Create `src/railway_lakehouse/silver/news/sentiment_encoder.py`: lazy `SentimentEncoder`, pinned model constants, `encode`, `health_check`, singleton.
- Modify `src/railway_lakehouse/silver/news/extract.py`: remove LLM-owned `confidence`, strip any returned sentiment/confidence, add post-validation sentiment enrichment.
- Modify `src/railway_lakehouse/silver/schema.py`: document new confidence semantics and keep missing sentiment/confidence optional.
- Modify `src/railway_lakehouse/silver/news/cache.py`: include sentiment model id/revision in the extraction digest so future sentiment-model changes invalidate cached rows.
- Modify `src/railway_lakehouse/gold/build.py`: prefer `sentiment_score`, retain `_SENTIMENT_MAP` fallback.
- Modify `pyproject.toml`: add `transformers>=4.40,<5`.
- Add `tests/test_silver_sentiment_encoder.py`: mocked encoder unit tests and extraction integration test.
- Add `tests/test_silver_news_sentiment_imports.py`: import guard for missing transformers.
- Update existing extraction tests that still assume LLM confidence/sentiment.
- Update `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`, `docs/GAP_TASKS.md`, `docs/TASKS.md`, `docs/index.html`, `docs/PROGRESS_LOG.md`, and `.planning/COURSEWORK_PROGRESS.md`.

Tasks:

1. Add RED tests.
   - Test `SentimentEncoder` with a mocked pipeline returning positive, negative, and neutral labels/scores.
   - Test pipeline-load failure returns `None`.
   - Test import succeeds while `transformers` import is simulated as unavailable.
   - Test `extract_article` consumes LLM JSON without sentiment/confidence and populates sentiment fields from a mocked encoder.
   - Test Gold aggregation prefers `sentiment_score` over label mapping.

2. Implement the encoder.
   - Constants: model name `cardiffnlp/twitter-xlm-roberta-base-sentiment`, revision `f2f1202b1bdeb07342385c3f807f9c07cd8f5cf8`, `device=-1`.
   - Lazy load inside `encode`/`health_check`; no heavy import at module import.
   - Normalize labels to `negative`, `neutral`, `positive`; return `{"label": label, "score": float}` or `None`.

3. Wire extraction.
   - Remove `confidence` from LLM schema required/properties and few-shot outputs.
   - Before validation, strip `sentiment`, `sentiment_label`, `sentiment_score`, `sentiment_confidence`, and `confidence` if a mocked/legacy LLM response includes them.
   - After validation, call `_add_sentiment_and_confidence(feature, title, body)`.
   - Set `sentiment`, `confidence`, `sentiment_label`, `sentiment_confidence`, and signed `sentiment_score`.
   - Leave those fields `None` if the encoder is unavailable.

4. Update Gold and schema docs.
   - `_sentiment_score` helper prefers numeric `sentiment_score`; otherwise maps `sentiment`.
   - Schema comments explain `confidence` as XLM-R max softmax for GAP-034 rows, with `sentiment_confidence` mirroring it in the wide contract.

5. Update project docs and dashboard.
   - Record the research.
   - Mark GAP-034 closed only after verification passes.
   - Sync `docs/TASKS.md` and `docs/index.html` because pipeline state changes.
   - Append progress handoff entries.

6. Verify and ship.
   - Run targeted RED before implementation where possible.
   - Run `python -m pytest -q tests/test_silver_sentiment_encoder.py tests/test_silver_news_sentiment_imports.py tests/test_silver_news_parsers.py tests/test_silver_news_extract_prompt.py`.
   - Run `python -m pytest -q`.
   - Run `python -m compileall -q src tests`.
   - Run `git diff --check`.
   - Commit, push `impl/gap-034`, open PR against `main`, and check mergeability.

Self-review:

- Scope matches GAP-034 only: no Bronze changes, no live HF download, no language-id/NER/embedding work.
- The plan corrects stale claims instead of widening the model pipeline.
- Tests are deterministic and use mocks/tmp paths only.
- Dashboard sync is included in the same change.

Approved: yes.
