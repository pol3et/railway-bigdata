# Parser Field Coverage

This matrix records the deterministic parser contract for GAP-044. It is a
companion to `docs/DATA_CONTRACTS.md`: Bronze remains immutable, Silver captures
the stable parser fields, and later Silver/Gold/Spark tasks decide how to widen,
filter, or aggregate.

| Source | Available Fields | Extracted Fields | Dropped / Future | Notes |
|---|---|---|---|---|
| RSS | `title`, `link`, `pubDate`, `description`, `content:encoded`, `author`, `category`, `comments`, `guid`, `enclosure` | `article_id`, `source`, `title`, `url`, `published_date`, `body` | `author`, `category`, `comments`, `guid`, `enclosure` | `content:encoded` is preferred over `description`; extra RSS fields are GAP-032 future widening. |
| GDELT DOC | `url`, `url_mobile`, `title`, `seendate`, `publishedDate`, `datetime`, `snippet`, `summary`, `description`, `domain`, `language`, `sourcecountry`, `socialimage` | `article_id`, `source`, `title`, `url`, `published_date`, `body` | `domain`, `language`, `sourcecountry`, `socialimage`; GKG `themes`, `persons`, `organizations`, `locations`, `tone` | DOC ArtList does not return full GKG rows. GKG passthrough needs a separate GKG source/parser (GAP-031). |
| World Bank | API metadata, `indicator`, `country`, `countryiso3code`, `date`, `value`, `unit`, `obs_status`, `decimal` | `geo`, `year`, `value`, `unit`, `source_dataset`, `source_column`, `source_system` | API metadata, observation status, decimal precision | Numeric rows are parsed deterministically; metadata is future provenance enrichment. |
| Eurostat | series dimensions such as `freq`, `unit`, `geo`, breakdown dimensions, `TIME_PERIOD` columns, values with flags | `geo`, `year`, `value`, `unit`, `source_dataset`, `source_column`, `source_system` | observation flags as separate fields, unit multiplier metadata | Current parser strips flags from numeric cells and keeps aggregate geos visible. GAP-023 policy is separate from this audit. |
| KSH | workbook title/unit hints, label columns, year headers, period-year layouts, regional total rows, numeric cells | `geo`, `year`, `value`, `unit`, `source_dataset`, `source_column`, `source_system` | non-country regional rows, unsupported workbook layouts | Current parser keeps Hungary country totals and logs empty output for unexpected layouts. |
| UIC | PDF text, extracted tables, country code, railway company/year, network, staff, rolling stock, passenger/freight measures | `geo`, `year`, `value`, `unit`, `source_dataset`, `source_column`, `source_system` | non-AT/HU countries, non-matching tables, Traffic Trends text | GAP-041 owns widening to all countries and staging unmapped/Traffic Trends rows. |
| Statistik Austria | raw ODS workbook bytes, table labels, units, years, numeric values | none yet | all ODS fields | GAP-042 owns the Statistik Austria ODS Silver parser. |

## Rationale

- RSS and GDELT DOC intentionally emit the 6-field `ArticleRecord` contract.
  Wider article metadata is reserved by the 44-field `NewsFeature` contract but
  not all source metadata is materialized yet.
- World Bank, Eurostat, KSH, and UIC all emit the long stats contract:
  `geo`, `year`, `value`, `unit`, `source_dataset`, `source_column`,
  `source_system`.
- Numeric stats parsing stays deterministic. LLMs may classify or extract
  article facts elsewhere, but they do not rewrite numeric rows.
- A JSON mirror for tests and dashboard checks lives at
  `docs/PARSER_FIELD_COVERAGE.json`.
