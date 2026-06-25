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

## Silver UIC Staging Contract

Producer: `src/railway_lakehouse/silver/stats/load.py`.

Consumer: audit/reparse workflows; Gold does not aggregate this table yet.

Purpose: preserve every extracted UIC PDF table row plus text chunks from
text-only UIC publications so parser mappings can expand without fetching or
re-parsing Bronze bytes.

Frozen local path contract:

```text
silver/uic_staging/ingest_date=YYYY-MM-DD/uic_staging.parquet
```

Schema:

| Field | Meaning |
|---|---|
| `table_name` | Constant `uic_staging`. |
| `dataset_id` | Bronze UIC dataset id, such as `uic_synopsis` or `uic_traffic_trends_2024`. |
| `table_id` | Stable grouping key: `dataset_id + "_" + table_idx + "_" + row_type`. |
| `table_idx` | Ordinal position from `pdfplumber` table extraction; `-1` for text chunks. |
| `row_type` | `header`, `data_row`, or `text_chunk`. |
| `row_idx` | Row ordinal inside the table, or text-chunk ordinal for `text_chunk`. |
| `parse_status` | `success`, `geo_unmapped`, `year_missing`, `value_unparseable`, `table_mismatch`, or `text_only`. |
| `geo` | Parsed ISO-like project geo where available; null for headers, text chunks, and unmapped rows. |
| `year` | Parsed observation year where available. |
| `source_dataset` | Same value as `dataset_id`, retained for source lineage parity. |
| `source_system` | Constant `uic`. |
| `raw_geo_cell` | Original unparsed country-code cell. |
| `raw_year_cell` | Original unparsed railway-company/year cell. |
| `raw_value_cells` | Original unparsed cells from mapped value columns, as `list<string>`. |
| `text_chunk` | Extracted text line for `text_chunk` rows; empty for table rows. |
| `created_at` | UTC ISO timestamp when the row was staged. |

Rules:

- Bronze PDF bytes remain immutable; staging is a Silver audit output.
- Numeric values that feed `StatFact` remain deterministic parser output. UIC
  staging rows are not LLM-rewritten and do not feed Gold until a later task
  explicitly wires them.
- The Traffic Trends PDF has extractable text but no country-level synopsis
  table; it is represented as `text_chunk` rows with `parse_status="text_only"`.

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

LLM/generative fields plus legacy compatibility fields:

5. `language`
6. `is_rail_related`
7. `country`
8. `event_type`
9. `operators`
10. `rail_lines`
11. `monetary_amount_eur`
12. `monetary_raw`
13. `summary_en`
14. `sentiment` - GAP-034 deterministic XLM-R label
    (`negative`/`neutral`/`positive`) for `extract_article(...)` rows;
    GDELT passthrough rows may still use their deterministic tone heuristic.
15. `confidence` - GAP-034 XLM-R max softmax probability in `[0, 1]`
    when sentiment is populated by the encoder; null when the encoder is
    unavailable or the row came from a path without classifier confidence.

Reserved / populated model-extracted fields for the GAP-031...038 passes:

16. `language_detected_code`
17. `language_confidence`
18. `sentiment_label` - mirrors the XLM-R sentiment label for GAP-034 rows.
19. `sentiment_score` - signed deterministic sentiment score in `[-1, 1]`;
    Gold prefers this value and falls back to label mapping for legacy rows.
20. `sentiment_confidence` - XLM-R max softmax probability for GAP-034 rows.
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
44. `is_duplicate`

Rules:

- LLM output is untrusted until validated by `validate_news_feature(...)`.
- GAP-035 populates deterministic language fields through the local language-id
  pass.
- GAP-034 populates deterministic XLM-R sentiment fields after LLM validation:
  `sentiment`, `confidence`, `sentiment_label`, `sentiment_score`, and
  `sentiment_confidence`. The LLM prompt/schema does not own sentiment or
  confidence.
- The current GAP-039 implementation reserves the wide model fields. GAP-036 now
  populates `text_embedding`/`text_embedding_model` when the optional
  `sentence-transformers` news extra is installed. The production
  `run_extraction_pipeline(...)` path then invokes deterministic local
  near-duplicate assignment via `cross_lingual_dedup_id` + `is_duplicate` when
  embeddings are present.
- Remaining reserved model fields for later passes are NER, Spark clustering,
  and deterministic monetary parsing; those are owned by GAP-031...038.
- `monetary_raw` is explicitly part of the Silver news contract.
- `sentiment` and `confidence` remain the legacy fields consumed by current
  consumers. New Gold sentiment aggregation prefers `sentiment_score` and only
  uses label mapping when a row lacks the deterministic signed score.

### Embeddings and Dedup

Research record:
`.planning/coursework/research/bigdata/labse-embeddings-dedup.md`.

- `text_embedding_model` records the sentence-transformers model id used for the
  row. GAP-036 defaults to `intfloat/multilingual-e5-base`, with BGE-M3 kept as
  a config-level swap. LaBSE is not the project default.
- `text_embedding` stores a normalized multilingual sentence embedding as
  `list<float32>` in Parquet. The default e5-base vector has 768 dimensions and
  uses the `passage: ` prefix for article/summary text.
- `cross_lingual_dedup_id` is a deterministic group id assigned to rows whose
  embedding cosine similarity is at or above the configured threshold
  (default `0.95`) in the production Silver news extraction pipeline and local
  helper. Group ids are derived from sorted member article ids, so shuffled input
  produces the same id.
- `is_duplicate` is `true` for non-canonical siblings inside a dedup group,
  `false` for canonical grouped rows or singleton embedded rows, and null when
  no embedding-backed grouping pass has run.
- GAP-036 deliberately does not change Gold counts. Spark-scale clustering and
  count enforcement remain GAP-037/GAP-040 work.

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
