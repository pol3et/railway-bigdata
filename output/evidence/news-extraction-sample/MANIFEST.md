# News LLM Extraction Evidence - GAP-033

## Run Details

- Date: 2026-06-25 05:16:06Z to 2026-06-25 05:22:56Z
- Operator: Codex local session on branch `impl/gap-033`
- Production entrypoint: `railway_lakehouse.silver.run.run_news(...)`
- Bronze sample root: `output/evidence/news-extraction-sample-bronze/bronze/` (raw Bronze is ignored and not committed)
- Evidence root: `output/evidence/news-extraction-sample/`
- Ollama host: `http://localhost:11434`
- Ollama version: `0.30.9`
- Ollama API model: `qwen3:4b`
- Ollama API model digest: `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`
- Model details from `/api/tags`: GGUF, family `qwen3`, parameter size `4.0B`, quantization `Q4_K_M`, size `2497293931` bytes
- Runtime context from `/api/ps`: `context_length=4096`, `size_vram=3403593809`
- Extraction manifest digest: `83d74a89b2f24fb44b3dede0983816490339d293cc807e345273f71bc48de66a`
- Prompt version: `gap050-news-v1`
- Settings: `OLLAMA_NUM_PARALLEL=1`, `num_ctx=4096`, `num_predict=1024`, `think=false`, `keep_alive=10m`

## Bronze Sample

- RSS live check: 7 feed artifacts landed, 1 feed failed (`hu_origo`, HTTP 404).
- GDELT bounded pull: 1 country artifact landed; the second country request returned HTTP 429.
- Parsed available article pool: 237 real articles (`gdelt=25`, `rss=212`).
- Selected bounded extraction sample: 40 articles (`gdelt=25`, `rss=15`).
- No synthetic or fabricated articles were used.

## Extraction Results

- Articles received: 40
- Articles processed: 40
- LLM attempted: 40
- Successful extractions: 40 (100.0%)
- Permanent failed extractions: 0 (0.0%)
- Cache hits: 0
- Cache misses: 40
- Cache writes: 40
- GDELT deterministic passthrough rows: 0
- Article-level runner retry attempts: 0
- Warm-up latency: 4.577 seconds
- Wall-clock duration from run manifest: 409.921 seconds
- Wrapper elapsed time: 411.973 seconds
- Average wall-clock per processed article: 10.25 seconds
- Total recorded LLM latency: 405.344 seconds
- Max single-article latency: 24.612 seconds

Command stderr showed 6 transient `Ollama HTTP 500 (attempt 1/3)` warnings from the lower-level Ollama client. All recovered inside the client retry loop; the GAP-050 runner recorded zero permanent failures and the failure sidecar is empty.

## Persisted Outputs

- Silver NewsFeature Parquet: `output/evidence/news-extraction-sample/silver/news/news_feature/ingest_date=2026-06-25/news_feature.parquet`
- Extraction run manifest: `output/evidence/news-extraction-sample/silver/news/news_extraction_runs/ingest_date=2026-06-25/manifest.json`
- Failure sidecar: `output/evidence/news-extraction-sample/silver/news/news_extraction_failures/ingest_date=2026-06-25/failures.json`
- Gold traceability Parquet: `output/evidence/news-extraction-sample/railway_ml.parquet`
- Gold counts summary: `output/evidence/news-extraction-sample/counts.json`

Failure sidecar contents:

```json
{
  "failure_count": 0,
  "failures": [],
  "ingest_date": "2026-06-25"
}
```

## LLM Output Quality

- Total NewsFeature rows persisted: 40
- Source distribution: `gdelt=25`, `rss=15`
- Rail-related rows: 21 (52.5%)
- Non-rail rows: 19 (47.5%)
- Rail-related by source: `gdelt=19/25`, `rss=2/15`
- Country distribution: `HU=21`, `other=19`
- Event type distribution: `other=29`, `service_change=6`, `policy=2`, `accident=1`, `line_opening=1`, `strike=1`
- Summary coverage: 40/40 rows have `summary_en`
- Monetary amount coverage: 0/40 rows
- Confidence stats: min `0.70`, max `0.99`, mean `0.887`, median `0.90`
- Sentiment distribution: 40 null values
- Language distribution: 40 null values
- Operators extracted: 0 rows
- Rail lines extracted: 0 rows

The null sentiment, language, operator, and rail-line fields are expected for this run. GAP-050 narrowed the LLM-owned contract to rail relevance, country, event type, summary, money, and confidence; deterministic language/sentiment/NER stages are separate future work.

## Gold Readback

- Gold rows: 1
- Gold columns: 12
- Gold country/year row: `HU`, `2026`
- `news_article_count`: 19
- Event count columns present: `news_n_accident=1`, `news_n_line_opening=1`, `news_n_other=10`, `news_n_policy=2`, `news_n_service_change=5`

The two rail-related RSS rows did not reach the Gold aggregate because their RSS parsed `published_date` values were null, and Gold requires a usable country and year.

## Sample Extraction

```json
{
  "article_id": "https://nepszava.hu/3326991_mav-dunakeszi-jarmujavito-ic-kocsik-halokocsik-fovizsgaztatas-ujrainditas-vitezy-david",
  "source": "gdelt",
  "url": "https://nepszava.hu/3326991_mav-dunakeszi-jarmujavito-ic-kocsik-halokocsik-fovizsgaztatas-ujrainditas-vitezy-david",
  "published_date": "2026-06-24",
  "language": null,
  "is_rail_related": true,
  "country": "HU",
  "event_type": "service_change",
  "operators": "[]",
  "rail_lines": "[]",
  "monetary_amount_eur": null,
  "monetary_raw": null,
  "summary_en": "MÁV restarted the inspection of IC and hálókocsik at Dunakeszi Railway Repair in Hungary.",
  "sentiment": null,
  "confidence": 0.9,
  "language_detected_code": null,
  "language_confidence": null,
  "sentiment_label": null,
  "sentiment_score": null,
  "sentiment_confidence": null,
  "is_rail_related_confidence": null,
  "event_type_confidence": null,
  "summary_en_source": "ollama",
  "operators_ner_model": null,
  "operators_confidence": null,
  "rail_lines_ner_model": null,
  "rail_lines_confidence": null,
  "monetary_raw_parsed_eur": null,
  "monetary_confidence": null,
  "gkg_themes": null,
  "gkg_persons": null,
  "gkg_organizations": null,
  "gkg_locations": null,
  "gkg_tone": null,
  "gkg_emotions": null,
  "gkg_tone_source": null,
  "text_embedding_model": null,
  "text_embedding": null,
  "cluster_id": null,
  "cross_lingual_dedup_id": null,
  "extraction_timestamp_utc": "2026-06-25T05:17:41Z",
  "extraction_model_digest": "83d74a89b2f24fb44b3dede0983816490339d293cc807e345273f71bc48de66a",
  "confidence_schema_version": "1.0"
}
```

## Assessment

- Ollama stability: PASS for this bounded run. The model stayed loaded, warm-up succeeded, and all 40 articles completed. Six transient HTTP 500 first attempts recovered through client retries.
- Schema conformance: PASS. All 40 outputs persisted as validated `NewsFeature` rows; permanent failure sidecar count is 0.
- Pipeline integration: PASS. The production `run_news(...)` entrypoint wrote the GAP-050 run manifest and failure sidecar, then rows were persisted to canonical Silver Parquet and aggregated into a Gold traceability Parquet.
- LLM quality: MIXED. Clear rail snippets can be useful: the MÁV/Dunakeszi sample was classified as `HU` / `service_change` with a relevant English summary. However, several sparse GDELT snippet/title rows were over-marked as rail-related despite summaries that read like heatwave, sports, or general politics items. The RSS sample was more conservative (`2/15` rail-related), while GDELT was likely too broad (`19/25` rail-related).
- Ready for production: NO for report-quality unattended aggregation. YES for proving that the live qwen3:4b extraction path works, persists, and is observable. Before using this as a final report signal, add a quality gate or evaluator for sparse GDELT snippets and address RSS published-date coverage.

## Observations for Future Work

- Treat GDELT title/snippet-only inputs as lower trust or add a second rail-keyword/deterministic guard before Gold aggregation.
- Improve RSS published-date normalization so valid rail-related RSS rows can reach country/year Gold features.
- Keep the typed failure sidecar and run manifest in every live pass; they captured the important distinction between transient HTTP failures and permanent row failures here.
- Consider adding a small hand-labeled evaluation set for rail relevance before expanding the live sample size.
