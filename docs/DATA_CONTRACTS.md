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

Important fields:

- `article_id`
- `source`
- `url`
- `published_date`
- `language`
- `is_rail_related`
- `country`
- `event_type`
- `operators`
- `rail_lines`
- `monetary_amount_eur`
- `summary_en`
- `sentiment`
- `confidence`

Rule: LLM output is untrusted until validated by `validate_news_feature(...)`.

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
