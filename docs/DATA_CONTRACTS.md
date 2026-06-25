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

### GDELT GKG Bronze Raw Contract

Producer: `src/railway_lakehouse/bronze/sources/past_recordings.py`
when run with the historical GKG engine.

Path:

```text
bronze/news/gdelt_history/gkg_v1_daily/ingest_date=YYYY-MM-DD/YYYYMMDD.gkg.csv.zip
bronze/news/gdelt_history/gkg_v1_daily/ingest_date=YYYY-MM-DD/YYYYMMDD.gkg.csv.zip.meta.json
```

Content:

- Raw GDELT GKG daily ZIP bytes, landed unchanged.
- The ZIP member is a tab-delimited `.csv` file despite the CSV suffix.
- Bronze does not unzip, filter, normalize, deduplicate, or re-land parsed rows.
- GKG 1.0 rows group articles into namesets; GKG 2.x rows are document-grain.

Silver parsing is transient: `silver/news/gkg_parser.py` unzips and parses
records only to feed deterministic `NewsFeature` passthrough fields. The
production pipeline reader parses these ZIPs from Bronze, forwards the resulting
`GKGRecord` objects into the news extraction runner, and emits bounded
GKG-sourced `NewsFeature` rows through passthrough when no matching article row
already exists. The project does not persist a separate `GKGRecord` Silver table
in GAP-031.

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

### Transient GKGRecord Contract

`GKGRecord` in `src/railway_lakehouse/silver/schema.py` is an in-memory domain
object for GDELT GKG parser output. It is not a persisted table.

| Field | Meaning |
|---|---|
| `gkg_id` | GKG record id, or deterministic hash fallback when a source id is absent. |
| `gkg_date` | GKG date string (`YYYYMMDD` for 1.0, often `YYYYMMDDHHMMSS` for 2.x). |
| `document_identifier` | Source document identifier / URL field, used only for explicit best-effort matching. |
| `source_common_name` | Source host/name when provided by GKG. |
| `gkg_themes` | Semicolon-delimited GKG theme tokens. |
| `gkg_tone` | First numeric tone value from the comma-delimited tone field. |
| `gkg_persons` | Semicolon-delimited persons. |
| `gkg_organizations` | Semicolon-delimited organizations. |
| `gkg_locations` | Semicolon-delimited GKG location blocks or names. |
| `gkg_emotions` | Remaining comma-delimited tone/emotion values when available. |

GKG-derived `NewsFeature` rows populate `sentiment` from tone,
`country` from source/location fields, `event_type` from explicit GKG theme
tokens, and `operators` from deterministic known-operator matching. Unknown or
missing GKG fields remain `None`/`other`; no LLM inference fills them.

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

Grain: one row per `(geo, year)`.

Inputs:

- Silver stats long table.
- Silver news feature rows.

Outputs:

- Wide statistical feature columns.
- News aggregate columns such as article counts, event counts, sentiment, investment totals, and operator mentions.
- Parquet output written through `src/railway_lakehouse/gold/build.py`.

Rule: absence of news can be zero for count-like news columns. Missing statistical observations remain null/NaN.
