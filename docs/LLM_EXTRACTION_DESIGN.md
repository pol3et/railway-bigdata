# LLM News Extraction Design (GAP-050)

Status: implemented for the pre-live pipeline scaffold. GAP-033 owns the first live Ollama run and evidence.

## Scope

The LLM owns only the generative slice of `NewsFeature`:

- `is_rail_related`
- `country` (`HU`, `AT`, `other`) for current Gold routing
- `event_type` using the existing `NEWS_EVENT_TYPES` storage enum
- `summary_en`
- `monetary_raw`
- `monetary_amount_eur`, only when the article explicitly states EUR or an EUR equivalent
- confidence fields already present in the GAP-039 wide contract

It does not produce sentiment, language, operators, or rail lines. Those remain owned by deterministic language/sentiment/NER passes in later gaps. `monetary_currency` is a target design field, but it is not in the current GAP-039 schema; GAP-050 therefore keeps the original currency phrase in `monetary_raw` and does not perform FX conversion.

## Prompt Strategy

The call uses a system/user split:

- System: fixed extractor role, no invention, JSON-only, out-of-scope fields forbidden.
- User prompt: source, URL, input trust (`snippet_only` vs `full_text_or_rss_description`), article title/body, field rules, and synthetic HU/DE/EN few-shot examples held out from any future golden set.

GAP-050 chooses one structured call per article for v1. A decomposed gate -> typed extraction chain may improve a weak model, but it doubles local GPU passes and failure points before GAP-043 has metrics. The v1 schema is intentionally narrow enough for one call.

The Ollama request uses a JSON schema via `format`, `temperature=0`, `think=false`, and `num_ctx=4096`. The explicit `NEWS_EXTRACTION_PROMPT_VERSION` is included in the model digest, so a prompt edit invalidates the GAP-039 cache and forces downstream re-evaluation.

Sources: Ollama chat/structured output API (`https://github.com/ollama/ollama/blob/main/docs/api.md`), Ollama context-window FAQ (`https://github.com/ollama/ollama/blob/main/docs/faq.mdx`), Qwen thinking-mode docs (`https://qwen.readthedocs.io/en/latest/getting_started/quickstart.html`).

## Batch And Cache Policy

`run_extraction_pipeline()` is the GAP-050 batch interface. It preserves the existing `extract_batch()` contract for callers that only need `(successes, failures)`.

Default execution is sequential. On this GTX 1060 6 GB box, LangChain-style `batch()` would parallelize client calls, but Ollama still has to serve them through the same VRAM-bound runner. Keep `OLLAMA_NUM_PARALLEL=1`; any future concurrency must be opt-in and capped by the lower of `NEWS_EXTRACTION_CONCURRENCY` and `OLLAMA_NUM_PARALLEL`.

Cache lookup happens before any LLM call:

```text
(article content hash, model+prompt digest) hit -> replay NewsFeature
miss -> call Ollama -> validate -> cache write
```

GDELT rows carrying GKG fields continue to use deterministic passthrough and do not call the LLM.

Sources: LangChain batch/concurrency docs (`https://docs.langchain.com/oss/python/langchain/models`), Ollama environment config source for `OLLAMA_NUM_PARALLEL` (`https://github.com/ollama/ollama/blob/main/ollama/envconfig/config.go`).

## Failure Accounting

Malformed JSON, transport/CUDA/timeout exceptions surfaced through `generate_json`, and invalid article inputs become typed `ExtractionFailure` rows. Failures include `article_id`, source, URL, title, date, reason, model digest, timestamp, and raw malformed payload when available.

No row is silently dropped:

- `run_extraction_pipeline()` returns both successful features and failures.
- `persist_news_failures()` writes the JSON sidecar under `silver/news/news_extraction_failures/ingest_date=.../failures.json`.
- Re-runs are cheap because successful rows replay from the content-hash cache.

## Lifecycle

`OllamaLifecycle` keeps lifecycle actions behind explicit runner options:

- `warm_up=True` issues a tiny JSON call before a live batch to absorb cold-run faults.
- `unload_after=True` calls `ollama stop <model>` and then probes `nvidia-smi` when available.
- CI disables or mocks lifecycle work; no live Ollama is required for tests.

Unload discipline is VRAM-only. CPU-resident encoders should stay warm and may overlap with the GPU LLM pass; do not kill CPU models or MCP servers for RAM.

## Throughput And Observability

There is no cloud cost. Local cost is GPU wall-clock:

```text
uncached_articles * observed_avg_llm_latency * attempts
```

The run manifest records the values needed to compute this after the first live run:

- prompt version, model digest, Ollama model and runtime settings
- processed/succeeded/failed counts
- cache hits/misses/writes
- LLM attempts and retry attempts
- GDELT passthrough count
- failure rate
- latency totals and max article latency
- lifecycle results and cache stats

The owner GPU test already established the operational defaults used here: warm up once, `num_ctx=4096`, classify model/transport/JSON failures as retryable during the pass, and persist stubborn failures for investigate -> fix -> re-run.
