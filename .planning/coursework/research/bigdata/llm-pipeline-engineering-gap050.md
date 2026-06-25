# GAP-050 LLM Pipeline Engineering Research

Date: 2026-06-25

Skills used:

- `research-orchestrator`: mandatory course workflow; local files first, then routed MCP providers.
- `prompt-master`: applied for Ollama/Qwen prompt structure and compact local-model prompting constraints.
- `senior-prompt-engineer`: applied production-pipeline principles: cache, batch, retries, observability, failure accounting.
- `ship-it`: used as workflow discipline without Linear per user instruction; repo-local plan is `.planning/coursework/plans/bigdata/gap-050-llm-pipeline-engineering.md`.

## Local Research

Files read:

- `src/railway_lakehouse/silver/news/extract.py`
- `src/railway_lakehouse/silver/news/cache.py`
- `src/railway_lakehouse/silver/news/failures.py`
- `src/railway_lakehouse/silver/config.py`
- `src/railway_lakehouse/silver/ollama_client.py`
- `src/railway_lakehouse/silver/schema.py`
- `tests/test_silver_news_wide_contract.py`
- `tests/test_silver_news_extraction_e2e.py`
- `docs/DATA_CONTRACTS.md`
- `docs/SILVER_DESIGN.md`
- `docs/SPEC_NEWS_PREPROCESSING.md`
- `docs/ROADMAP_NEWS_TO_REPORT.md`
- `docs/GAP_REGISTER.md`
- `docs/TASKS.md`

Local findings:

- The draft spec's "no caching/no failure accounting" context is stale after GAP-039. Current code has `FileSystemCache`, content-sensitive keys, model-digest cache dirs, `extract_batch()` returning `(successes, failures)`, and `persist_news_failures()`.
- The current prompt is still broad: it asks the LLM for language, sentiment, operators, and rail lines even though later deterministic/NER passes own those fields.
- `model_digest_key()` hashes system text and schema but not an explicit prompt version, so reviewable prompt semver is not recorded.
- `NewsFeature` has no `monetary_currency` field. FX conversion is deferred in `docs/SPEC_NEWS_PREPROCESSING.md`; GAP-050 should not widen the schema.
- `OLLAMA_NUM_CTX` defaults to 8192 despite the owner GPU-load note grounding 4096 as safer on the GTX 1060.

## Routed External Research

Provider: Context7

Queries and URLs:

- Ollama structured output, chat API, `keep_alive`, `num_ctx`, `num_batch`, and concurrency:
  - `Context7 /ollama/ollama`: source `https://github.com/ollama/ollama/blob/main/docs/api.md`
  - `https://github.com/ollama/ollama/blob/main/docs/faq.mdx`
  - `https://github.com/ollama/ollama/blob/main/ollama/api/types.go`
  - `https://github.com/ollama/ollama/blob/main/ollama/envconfig/config.go`
- LangChain batch/concurrency behavior:
  - `Context7 /websites/langchain_oss_python_langchain`: source `https://docs.langchain.com/oss/python/langchain/models`
- Qwen thinking/non-thinking and structured output guidance:
  - `Context7 /websites/qwen_readthedocs_io_en`: sources `https://qwen.readthedocs.io/en/latest/getting_started/quickstart.html`, `https://qwen.readthedocs.io/en/latest/inference/transformers.html`, `https://qwen.readthedocs.io/en/latest/deployment/sglang.html`

Findings used:

- Ollama `/api/chat` accepts a JSON schema in `format`; returned content is a JSON string that still must be parsed and validated.
- Ollama request options include `num_ctx`, `num_predict`, and runner options including `num_batch`; docs show setting `num_ctx` under `options`.
- Ollama exposes `OLLAMA_NUM_PARALLEL`, `OLLAMA_MAX_LOADED_MODELS`, and `OLLAMA_MAX_QUEUE`; the single 6 GB GPU plan should keep `OLLAMA_NUM_PARALLEL=1`.
- Ollama `keep_alive` is an advanced chat/generate parameter; GAP-050 uses it to keep Qwen resident during the pass and reserves unload for GPU handoff.
- LangChain `batch()` is client-side parallelization and supports `max_concurrency`; this does not help the VRAM-bound single-GPU case, so the default runner is a sequential cached pass.
- Qwen docs distinguish thinking and non-thinking mode. For JSON extraction with Qwen3 through Ollama, keep `think:false` and use a compact role/system prompt plus schema-constrained output.

## Refined Implementation Decisions

- Use one structured Ollama call per article for v1. The schema is now small enough that decomposition would double model calls and failure points before GAP-043 measures quality.
- Keep `event_type` as the existing `NEWS_EVENT_TYPES` storage enum. GAP-043 can collapse it for gates later.
- Do not add `monetary_currency` to the persisted schema in GAP-050. The prompt asks the model to keep currency visible in `monetary_raw`; `monetary_amount_eur` is only for explicit EUR/equivalent values.
- Default batch policy is sequential with a batch interface and metrics. Any future parallelism must be opt-in and capped by `OLLAMA_NUM_PARALLEL`.
- Warm-up and unload are lifecycle hooks in the runner. Unit/CI tests keep them disabled or mocked; GAP-033 can enable them for the live pass.
