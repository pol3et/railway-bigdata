# Data Contracts

## Bronze Raw Artifact

Producer: source fetchers.

Consumer: `RawLander`.

Current schema from `src/railway_lakehouse/bronze/lander.py`:

| Field | Meaning |
|---|---|
| `domain` | Data domain such as `stats` or `news`. |
| `source` | Source system such as `eurostat`, `worldbank`, `gdelt`, `rss`, `ksh`, `statistik_austria`, `uic`. |
| `dataset_id` | Stable dataset or source identifier. |
| `filename` | Original or stable file name. |
| `content` | Raw bytes exactly as fetched. |
| `source_url` | URL used for collection. |
| `content_type` | Source content type. |
| `http_status` | HTTP result. |
| `extra` | Source-specific metadata. |

Bronze path pattern:

```text
bronze/<domain>/<source>/<dataset_id>/ingest_date=YYYY-MM-DD/<file>
bronze/<domain>/<source>/<dataset_id>/ingest_date=YYYY-MM-DD/<file>.meta.json
```

## Silver Stats Contract

Target row: `StatFact` from `src/railway_lakehouse/silver/schema.py`.

| Field | Meaning |
|---|---|
| `geo` | Country or region code. |
| `year` | Observation year. |
| `feature` | Canonical English feature key. |
| `value` | Numeric value. |
| `unit` | Source/native unit. |
| `source_system` | Original system. |
| `source_dataset` | Original dataset id. |
| `source_column` | Original column/label for provenance. |

Rule: numeric values must be parsed and merged deterministically. LLM use is limited to label mapping where needed.

## Silver News Contract

Target row: `NewsFeature` from `src/railway_lakehouse/silver/schema.py`.

Field order is authoritative in `src/railway_lakehouse/silver/schema.py`
(`NewsFeature.__dataclass_fields__`) and is preserved in Parquet by
`src/railway_lakehouse/silver/persist.py`.

Provided by Bronze / article lineage:

1. `article_id`
2. `source`
3. `url`
4. `published_date`

Legacy LLM/generative fields retained for backward compatibility:

5. `language`
6. `is_rail_related`
7. `country`
8. `event_type`
9. `operators`
10. `rail_lines`
11. `monetary_amount_eur`
12. `monetary_raw`
13. `summary_en`
14. `sentiment`
15. `confidence`

Reserved model-extracted fields for the GAP-031...038 passes:

16. `language_detected_code`
17. `language_confidence`
18. `sentiment_label`
19. `sentiment_score`
20. `sentiment_confidence`
21. `is_rail_related_confidence`
22. `event_type_confidence`
23. `summary_en_source`
24. `operators_ner_model`
25. `operators_confidence`
26. `rail_lines_ner_model`
27. `rail_lines_confidence`
28. `monetary_raw_parsed_eur`
29. `monetary_confidence`

GDELT GKG passthrough fields:

30. `gkg_themes`
31. `gkg_persons`
32. `gkg_organizations`
33. `gkg_locations`
34. `gkg_tone`
35. `gkg_emotions`
36. `gkg_tone_source`

Embedding, deduplication, and clustering fields:

37. `text_embedding_model`
38. `text_embedding`
39. `cluster_id`
40. `cross_lingual_dedup_id`

Caching/audit fields:

41. `extraction_timestamp_utc`
42. `extraction_model_digest`
43. `confidence_schema_version`

Rules:

- LLM output is untrusted until validated by `validate_news_feature(...)`.
- The current GAP-039 implementation reserves the wide model fields but does not
  populate language detection, XLM-R sentiment, NER, embeddings, clustering, or
  deterministic monetary parsing; those are owned by GAP-031...038.
- `monetary_raw` is explicitly part of the Silver news contract.
- `sentiment` and `confidence` are the legacy fields consumed by current Gold.
  `sentiment_label`/`sentiment_score` and per-field confidences are the forward
  contract for later deterministic model passes.

### Content-hash cache contract

Silver news extraction has a local idempotency cache implemented by
`src/railway_lakehouse/silver/news/cache.py`.

- `extract_cache_key(article)` is a SHA-256 over `article_id`, `title`, `body`,
  `url`, and `published_date`. A changed URL or changed article text is treated
  as new extraction work.
- `model_digest_key()` is a SHA-256 over the current `OLLAMA_MODEL` value,
  Ollama config values, the JSON schema, prompt system text, few-shot examples,
  temperature, and `NEWS_EXTRACTION_PROMPT_VERSION`.
  It invalidates cached LLM extractions after prompt/model/config changes; it is
  not a hash of model weights.
- `FileSystemCache` stores one JSON file per article under
  `silver/.news_extraction_cache/<model_digest>/<cache_key>.json`, plus
  `_manifest.json` with cached count, hits, misses, last update, and the last
  100 hit/miss events.
- The cache is a local optimization and is git-ignored. It is not committed and
  is not the MinIO/S3 Silver table.
- Extraction failures are collected as `ExtractionFailure` objects and can be
  written to a JSON sidecar under
  `silver/news/news_extraction_failures/ingest_date=YYYY-MM-DD/failures.json`.
  A Parquet failure table remains a follow-up persistence decision.
- GAP-050 production run manifests are written by `pipeline.run_pipeline()` and
  `silver.run.run_news()` under the configured artifact root (default
  `output/silver`):
  `silver/news/news_extraction_runs/ingest_date=YYYY-MM-DD/manifest.json` and
  record processed/cached/failed counts, failure rate, latency, model digest,
  and prompt version.

## Silver Persisted Outputs (Parquet)

Producer: `src/railway_lakehouse/silver/persist.py`.

Consumer: Gold (`build_from_silver`) and Spark evidence jobs.

Frozen local path contract (partitioned by `ingest_date`):

```text
silver/stats/stat_fact/ingest_date=YYYY-MM-DD/stat_fact.parquet
silver/news/news_feature/ingest_date=YYYY-MM-DD/news_feature.parquet
```

- Root is a local filesystem Silver tree for fixtures and local evidence.
- Each `ingest_date` partition is one replaceable snapshot. Re-running the same
  date overwrites that date's Parquet file; use a new date or future run-id
  partitioning if multiple same-day snapshots must be retained.
- MinIO/s3fs Silver persistence is not wired here; keep that in GAP-010 storage
  work.
- Stats columns = `StatFact` field order; news columns = `NewsFeature` field
  order (derived from `schema.py` and written with explicit Arrow types, so
  empty files keep the same physical schema as non-empty files).
- `load_stats(root)` / `load_news(root)` read the latest `ingest_date=`
  partition unless an explicit date is passed.
- An empty news run still writes a valid 0-row, schema-shaped Parquet so Gold
  always has a deterministic input.
- `news_feature` stores validated successful `NewsFeature` rows. Extraction
  failures are not mixed into the success table; GAP-039 defines the JSON
  sidecar above while leaving a Parquet failure table to a later storage task.

## Gold Contract

Default grain: one row per `(geo, year)`.

Sub-annual option: `aggregate_news(..., granularity="year-month")` and
`build_gold(..., granularity="year-month")` emit news features at
`(geo, year, month)`. When yearly stats are merged with year-month news,
stats join on `(geo, year)` and repeat across months that have news.

Inputs:

- Silver stats long table.
- Silver news feature rows.

Outputs:

- Wide statistical feature columns.
- News aggregate columns:
  - Existing deterministic features: `news_article_count`,
    `news_sentiment_mean`, `news_share_negative`,
    `news_total_investment_eur`, canonical `news_n_<event_type>` counts, and
    canonical `news_op_<operator>` counts.
  - Language features: canonical ISO 639-1 count columns
    `news_language_hu`, `news_language_de`, `news_language_en`,
    `news_language_fr`, `news_language_es`, `news_language_it`,
    `news_language_pl`, `news_language_ro`, `news_language_sk`,
    `news_language_cs`, plus `news_language_primary` and
    `news_language_entropy`. Czech is `cs`; `cz` is not an ISO 639-1
    language code.
  - Confidence features: `news_confidence_mean`, `news_confidence_std`,
    `news_confidence_min`, `news_confidence_max`, and
    `news_confidence_bin_low`, `news_confidence_bin_medium`,
    `news_confidence_bin_high` for `[0,0.33]`, `(0.33,0.67]`,
    `(0.67,1.0]`.
  - Rail-line features: `news_n_rail_lines_unique` and
    `news_rail_lines_list`. Gold intentionally does not pivot arbitrary
    free-text rail-line names until a canonical rail-line gazetteer exists.
  - GKG-ready features from already-persisted Silver `gkg_*` fields:
    `news_gkg_tone_mean/std/min/max`, `news_n_gkg_<field>_unique`, and
    `news_gkg_<field>_list` for themes, persons, organizations, locations,
    and emotions. Raw GKG csv.zip parsing and canonical theme/CAMEO pivots
    remain deferred to the GKG parser task.
- Parquet output written through `src/railway_lakehouse/gold/build.py`.

Rule: absence of news can be zero for count-like news columns and empty for
deterministic list columns. Missing statistical observations and statistical
news summaries such as sentiment/confidence/tone means remain null/NaN.
