# GAP-033 Silver News LLM Extraction Live Research

Date: 2026-06-25

Skills used:

- `research-orchestrator`: mandatory course workflow; local files first, then routed MCP providers.
- `ship-it`: workflow discipline without Linear, per GAP-033 instructions.
- `superpowers:writing-plans`: one scoped implementation plan before edits.
- `superpowers:test-driven-development`: add the live regression guard before running the evidence pass.

## Local Research

Files read:

- `AGENTS.md`
- `docs/LLM_EXTRACTION_DESIGN.md`
- `docs/DATA_CONTRACTS.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`
- `docs/index.html`
- `src/railway_lakehouse/pipeline.py`
- `src/railway_lakehouse/silver/run.py`
- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/news/failures.py`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/ollama_client.py`
- `src/railway_lakehouse/silver/persist.py`
- `src/railway_lakehouse/silver/schema.py`
- `src/railway_lakehouse/gold/build.py`
- `tests/test_silver_news_extract_prompt.py`
- `tests/test_silver_news_extraction_e2e.py`
- `tests/test_pipeline_gaps.py`

Local findings:

- The static GAP-033 spec is stale after GAP-050. The old bare `extract_batch()` loop is no longer the production path. Current production entrypoints call `run_extraction_pipeline(...)` with warm-up, manifest writing, retry/backoff accounting, cache metrics, and typed failure records.
- `src/railway_lakehouse/silver/run.py::run_news()` is a production entrypoint that returns real `NewsFeature` rows while writing the run manifest and failure sidecar. It is the best fit for GAP-033 because the task also requires persisting canonical Silver `news_feature.parquet`.
- `src/railway_lakehouse/pipeline.py::run_pipeline()` also calls the GAP-050 runner, but it does not currently persist the canonical Silver news feature table. GAP-033 should not widen production pipeline scope to add that behavior unless evidence generation requires it.
- The production model default is already `qwen3:4b` in `silver.config.OLLAMA_MODEL`. The older `qwen3.5:9b-q8_0` references in the static spec are invalid for this host and must not be used.
- Current LLM-owned fields are intentionally narrower than the stale spec. Per `docs/LLM_EXTRACTION_DESIGN.md`, the LLM classifies/extracts fields such as `is_rail_related`, `country`, `event_type`, `summary_en`, `monetary_raw`, `monetary_amount_eur`, and confidence values. Sentiment, language, operators, and rail lines are retained on `NewsFeature` but are not owned by the GAP-050 LLM prompt.
- `persist.persist_news(...)` writes canonical Silver Parquet under `root/news/news_feature/ingest_date=YYYY-MM-DD/news_feature.parquet`. `persist.persist_news_failures(...)` writes typed failure sidecars under `root/news/news_extraction_failures/ingest_date=YYYY-MM-DD/failures.json`.
- `build_from_silver(...)` can build a Gold Parquet from an empty stats frame plus real news rows, which is enough for GAP-033 traceability. Numeric stat merges remain untouched.
- `pipeline --bronze-root` reads an existing local Bronze root; it does not land a local Bronze sample. A bounded local sample must be landed separately with existing Bronze source code, and raw Bronze must remain ignored/uncommitted.

## Routed External Research

Provider: Context7

- Query: Ollama chat API structured output, JSON schema format, temperature options.
- Source URL: `https://github.com/ollama/ollama/blob/main/docs/api.md`
- Finding: Ollama `/api/chat` supports a JSON schema in the `format` field and returns the assistant content as a JSON string. Callers still need to parse and validate the response.
- Finding: Ollama request `options` include generation controls such as `temperature`, `num_ctx`, and `num_predict`; `keep_alive` can keep a model resident across requests.

Provider: Tavily

- Query: Ollama structured outputs JSON schema temperature deterministic.
- Source URL: `https://docs.ollama.com/capabilities/structured-outputs`
- Finding: Official Ollama guidance recommends providing a JSON schema to `format`, validating the response with a schema library, and using a low temperature such as `0` for more deterministic output.
- Source URL: `https://ollama.com/blog/structured-outputs`
- Finding: Ollama positions structured outputs as schema-constrained generation for classification and data extraction workflows, but downstream validation remains the safe contract.

Provider: Firecrawl

- Source URL: `https://qwenlm.github.io/blog/qwen3`
- Finding: Qwen3 includes a 4B dense open-weight model, supports thinking and non-thinking modes, and is positioned for local inference through tools including Ollama. The 4B size is the model family compatible with this host's bounded GPU run.
- Source URL: `https://qwen.readthedocs.io/en/latest/framework/function_call.html`
- Finding: Qwen documentation shows explicit thinking-mode controls and warns implementers to handle protocol-following failures. GAP-033 should keep `think=false` and preserve retry/failure sidecar evidence rather than assuming perfect structured output.

Provider: Ref

- Query: Ollama structured output API and Qwen structured extraction.
- Result: Provider returned "Not enough credits". No Ref claims are used.

Provider: Exa

- Query: qwen3 4b Ollama structured output extraction.
- Source URL: `https://huggingface.co/Qwen/Qwen3-4B`
- Finding: Qwen3-4B is a current open model with native long context and non-thinking mode support; use as model-family context only. Runtime evidence for this repo must come from the local Ollama API and persisted artifacts.

## Live Environment Probe

Commands and observed facts:

- `GET http://localhost:11434/api/version` returned Ollama `0.30.9`.
- `GET http://localhost:11434/api/tags` returned installed model `qwen3:4b`.
- Model digest: `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- Model details: GGUF, family `qwen3`, parameter size `4.0B`, quantization `Q4_K_M`, size `2497293931` bytes.
- `GET http://localhost:11434/api/ps` showed the loaded model with `context_length=4096` and `size_vram=3403593809`.
- `railway_lakehouse.silver.ollama_client.health_check()` returned `True` with the repo default `OLLAMA_MODEL=qwen3:4b`.

## Refined GAP-033 Scope

- Use `qwen3:4b` exactly as configured; do not pull or override a 9B model.
- Keep `OLLAMA_NUM_PARALLEL=1` for the evidence run and do not change server flash-attention or GPU fallback settings.
- Use the GAP-050 production runner through `railway_lakehouse.silver.run.run_news(...)` so the live run creates the real run manifest and failure sidecar while returning rows for canonical Silver persistence.
- Persist returned features with `persist.persist_news(...)`, then build the requested traceability Gold Parquet with `gold.build.build_from_silver(...)`.
- Land a bounded real Bronze sample under `output/evidence/news-extraction-sample-bronze/bronze/` using existing Bronze source code. If network sources fail, use only existing landed real Bronze or a smaller live subset and record the limitation in the evidence manifest and progress log.
- The evidence manifest must report actual counts and distributions from persisted Parquet plus the run manifest/failure sidecar. Do not fabricate counts, sample rows, or quality claims.
- Temperature `0` should be described as a reproducibility aid, not an absolute guarantee. The durable audit controls are model digest, prompt/schema digest in the cache/run manifest, validation, retry/failure accounting, and persisted output.
