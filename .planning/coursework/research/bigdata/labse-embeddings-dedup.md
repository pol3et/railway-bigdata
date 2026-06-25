# GAP-036 Research - News Embeddings and Cross-Lingual Dedup

Date: 2026-06-25

Skill / routing:
- Used `research-orchestrator` as required by `AGENTS.md`.
- Local files first: `src/railway_lakehouse/silver/schema.py`, `src/railway_lakehouse/silver/persist.py`, `src/railway_lakehouse/silver/news/extract.py`, `docs/DATA_CONTRACTS.md`, `docs/SPEC_NEWS_PREPROCESSING.md`, `docs/ROADMAP_NEWS_TO_REPORT.md`, `docs/GAP_REGISTER.md`.
- Routed MCP providers: Context7 for `sentence-transformers` API docs; Tavily research for model-card/model-choice facts. Ref was attempted for Hugging Face docs, but the provider returned an account-credit error, so Tavily supplied the model-card URLs.

Queries:
- Context7: `sentence-transformers SentenceTransformer encode text to embeddings, normalize_embeddings, get_sentence_embedding_dimension`
- Tavily: `Verify current facts for railway project GAP-036 embedding model choice and API. Need concise cited facts: sentence-transformers SentenceTransformer.encode supports normalize_embeddings and float32 embeddings; intfloat/multilingual-e5-base Hugging Face model dimensions, languages, required query/passsage prefixes; BAAI/bge-m3 dimensions/long context and license; LaBSE languages/dimension and whether it is older/bitext-focused.`

Sources:
- Sentence Transformers API: https://www.sbert.net/docs/package_reference/sentence_transformer/SentenceTransformer.html
- Sentence Transformers normalize utility: https://www.sbert.net/docs/package_reference/util/tensor.html
- Hugging Face `intfloat/multilingual-e5-base` model card: https://huggingface.co/intfloat/multilingual-e5-base
- BGE-M3 model docs: https://bge-model.com/bge/bge_m3.html
- Google LaBSE background: https://research.google/blog/language-agnostic-bert-sentence-embedding
- LaBSE paper reference returned by Tavily: https://arxiv.org/pdf/2211.00046

Confirmed local-code facts:
- GAP-039 already widened `NewsFeature` to a 43-field article-grain contract. Embedding/dedup placeholders already exist as `text_embedding_model`, `text_embedding`, `cluster_id`, and `cross_lingual_dedup_id`; adding a second `embedding`/`dedup_group_id` pair would duplicate the live contract.
- `NEWS_FEATURE_COLUMNS` is derived from `NewsFeature.__dataclass_fields__`, and `persist.load_news()` reindexes old Parquet files to the current field list, so backwards compatibility is already an established pattern.
- Existing docs and GAP register reject LaBSE as the default embedder for this project. The current owner decision in `docs/ROADMAP_NEWS_TO_REPORT.md` is `multilingual-e5-base` as default, with BGE-M3 swappable if clustering needs sharper vectors.

API facts used:
- `SentenceTransformer.encode()` computes sentence embeddings and supports `normalize_embeddings=True`; its default output can be a NumPy array, and the API has a `precision` parameter defaulting to `float32`.
- `SentenceTransformer.get_embedding_dimension()` reports model output dimensionality.
- `intfloat/multilingual-e5-base` produces 768-dimensional embeddings and the model card instructs using `query: ` / `passage: ` prefixes; for article/document embeddings this GAP uses `passage: `.
- BGE-M3 is a viable multilingual alternative with 1024-dimensional dense vectors and long-context support, but the existing roadmap keeps it as a config-level swap because the local news snippets are short.
- LaBSE produces 768-dimensional multilingual sentence embeddings and supports 100+ languages, but the repo's reviewed model spec rejects it as the default for this task because it is weaker for the planned clustering deliverable than the current e5/BGE direction.

Refined GAP-036 decision:
- Default model: `intfloat/multilingual-e5-base`.
- Public helper name remains generic: `load_embedding_model(model_name=DEFAULT_EMBEDDING_MODEL)`.
- Storage field: use existing `text_embedding` as `list<float32>` and `text_embedding_model` as the model identifier.
- Dedup group field: use existing `cross_lingual_dedup_id`.
- New field to add: `is_duplicate: Optional[bool] = None`, because the current wide contract has a group id but no canonical/non-canonical marker.
- Dedup algorithm in this GAP is local deterministic connected-components over normalized embeddings for small fixture/offline batches. Spark-scale clustering/enforcement remains GAP-037.

## PR #39 Review-Fix Research Addendum

Date: 2026-06-25

Skill / routing:
- Used `research-orchestrator` as required by `AGENTS.md`.
- Local files first: `src/railway_lakehouse/silver/news/extract.py`, `src/railway_lakehouse/silver/news/embeddings.py`, `src/railway_lakehouse/silver/run.py`, `src/railway_lakehouse/pipeline.py`, `tests/test_silver_news_extraction_e2e.py`, `docs/DATA_CONTRACTS.md`, `docs/GAP_REGISTER.md`.
- No external MCP/web research was needed for this review fix; the issue was a production callsite omission in local code, and the existing embedding/dedup API facts above remain unchanged.

Confirmed local-code facts:
- Both production entrypoints (`silver.run.run_news(...)` and the higher-level pipeline path) flow through `run_extraction_pipeline(...)`.
- Before the PR review fix, `run_extraction_pipeline(...)` called `compute_embeddings(...)` but did not call `cluster_near_duplicates(...)`.
- The regression belongs at the production entrypoint with mocked embeddings so CI does not import or download sentence-transformer weights.

Decision:
- Call `cluster_near_duplicates(...)` inside `run_extraction_pipeline(...)` after embedding population, only when at least one row already has `text_embedding`.
- Gate `compute_embeddings(..., use_model=...)` on import availability for `sentence_transformers`; cached or mocked embeddings can still be clustered without loading a model.
