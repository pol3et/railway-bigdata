# GAP-039 NewsFeature Wide Contract Research

Date: 2026-06-25

Workflow: `research-orchestrator` used as required by `AGENTS.md`. Local files were researched first, then routed MCP providers were used for external docs.

## Local Findings

- `src/railway_lakehouse/silver/schema.py` has a 15-field `NewsFeature` and a permissive `validate_news_feature()`.
- `src/railway_lakehouse/silver/news/extract.py` has the existing LLM prompt, `extract_article()`, dead `gdelt_passthrough()`, and `extract_batch()` that silently drops failed articles.
- `src/railway_lakehouse/silver/persist.py` writes explicit Arrow schemas for `StatFact` and `NewsFeature` but only the current 15 news fields.
- `src/railway_lakehouse/pipeline.py` expects `extract_batch()` to return a list, so GAP-039 must update that caller when the return value becomes `(successes, failures)`.
- `docs/SPEC_NEWS_PREPROCESSING.md` supersedes stale parts of the GAP-039 draft: current single-box default is Qwen3-4B, embedding fast-follow is e5/bge-m3 rather than LaBSE as a binding default, and failures should be visible without silently dropping rows.

## External Sources

- Context7, Apache Arrow/PyArrow: `pa.schema()` defines field names/types, `pa.list_()` defines list columns, and `pa.Table.from_pandas(..., preserve_index=False)` plus `pq.write_table()` is the documented path for schema-shaped Parquet writes. Source: https://github.com/apache/arrow/blob/main/docs/source/python/parquet.rst and https://github.com/apache/arrow/blob/main/docs/source/python/data.rst
- Firecrawl, GDELT GKG Codebook V2.1: GKG records codify themes, tone/emotions, people, organizations, locations, counts, and source/event context; the raw format is tab-delimited CSV and needs preprocessing. Source: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- Firecrawl, Hugging Face Transformers model outputs: sequence classification models expose `logits` through `SequenceClassifierOutput`, which is the stable source for later deterministic sentiment score/confidence calculations. Source: https://huggingface.co/docs/transformers/main_classes/output
- Firecrawl, Hugging Face Hub cache docs: `HF_HOME` / `HF_HUB_CACHE` configure local model cache placement; useful background for later encoder passes, but GAP-039 implements only the project extraction-result cache. Source: https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
- Exa, SentenceTransformers docs: `SentenceTransformer.encode()` creates fixed-size embeddings and `get_embedding_dimension()` reports the output dimension; GAP-039 reserves the column, while GAP-036 owns population. Source: https://www.sbert.net/docs/package_reference/sentence_transformer/model.html
- Ref MCP was attempted for Hugging Face documentation and returned: "Not enough credits." Fallback routed providers were Firecrawl and Exa.

## Spec Refinements Applied

- The draft's "28 fields" count conflicts with its own list. Implementation will preserve the 15 old fields and append the listed wide fields, with tests requiring at least 28 total fields and explicit named fields.
- Failure persistence is narrowed to in-memory failures plus JSON sidecar helper. No failure Parquet table is created in this gap.
- The cache key follows the supplied pitfall for this implementation: SHA-256 over `article_id`, title, body, URL, and published date so changed content or URL misses the cache.
- `model_digest_key()` reads `OLLAMA_MODEL` at call time and hashes the current config/prompt/schema identity. It is a cache invalidation key, not a binary-weight authenticity digest.
- Existing `rss_records_to_news_features()` compatibility is preserved by unwrapping successes from the new tuple-returning `extract_batch()`.

## PR Review Fix Notes

- Local review of PR #28 found the production callers were not passing the file-system cache to `extract_batch()`. The fix wires a configurable `FileSystemCache` into both `pipeline.run_pipeline()` and `silver.run.run_news()`.
- Local Bronze normalization now preserves known GDELT/GKG fields (`gkg_*`, `tone`, `sourcecountry`, `language`, `domain`, `socialimage`) so `extract_batch()` can select `gdelt_passthrough_cached()` for annotated rows.
- The GDELT tone resolver now selects by key presence rather than truthiness, preserving `gkg_tone=0` as a valid neutral tone.
- No new external research was needed for these review fixes; they were verified against local code paths and tests.
