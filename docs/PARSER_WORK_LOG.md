# Parser Work Log

Last updated: 2026-06-21

Purpose: make the parser state easy to split between classmates before pushing
the project to GitHub. This log records what each parser collects, how it stores
raw data, what bounded live evidence exists, and what each owner should do next.

This is a rolling work log. Update it after every parser test, live probe,
source refresh, or storage contract change.

## Current Truth

The project does not yet have a full Bronze -> Silver -> Gold -> Spark E2E.
For collaboration, the first practical milestone is narrower:

1. Bronze parsers collect real raw data from selected sources.
2. Each raw artifact is stored unchanged with metadata.
3. Docs state how Silver can parse it later and which Gold features it can feed.
4. Failures are documented with owners instead of hidden.

Current bounded live evidence:

- Evidence manifest: `output/evidence/parser-live-check-2026-06-21/manifest.json`
- Scope: bounded live parser check only.
- Not launched: scheduler, long historical backfill, MinIO, Ollama, Spark.
- Raw evidence root: `output/evidence/parser-live-check-2026-06-21/bronze/`
- Public repo policy: commit the manifest and docs; keep raw fetched artifacts
  local unless the course submission explicitly needs them in Git.

## Bounded Live Check Summary

| Parser | Live status | Evidence | Current diagnosis | Next owner task |
|---|---|---|---|---|
| Eurostat | partial | Catalogue landed: `stats/eurostat/_catalogue_toc/.../toc_en.txt`; 1,980,690 bytes. | Discovery found 183 codes, but first dataset fetches failed with quoted codes like `"enpe_rail"` causing 404. | Strip quotes/formatting from TOC codes, add a fixture test, then fetch one real TSV dataset. |
| World Bank | partial | Catalogue landed: `stats/worldbank/_catalogue_indicators/.../indicators.json`; 9,316,675 bytes. | First discovered series `BM.GSR.TRAN.CD` returned a 128-byte API error payload, so discovery is too broad or needs response validation. | Validate indicator responses and prefer confirmed rail indicator allowlist before claiming series collection. |
| GDELT recent | failed live probe | No artifact landed. | DOC API returned HTTP 429 for bounded query. | Add rate-limit handling/backoff and retry; keep bounded `maxrecords` in tests. |
| RSS media | live-ok | Landed `hu_telex.xml` and `hu_index.xml`; 37,219 and 40,157 bytes. | Direct feed fetch works for at least two Hungarian feeds. | Add feed health tests, expand to AT feeds, and document feed drift handling. |
| KSH STADAT | live-ok | Landed `stats/ksh/ksh_rail_freight/.../sza0010.xlsx`; 15,657 bytes. | First configured Hungarian STADAT rail table is reachable. | Add mocked HTTP tests and confirm all seeded KSH table IDs. |
| Statistik Austria | failed live probe | No artifact landed. | Configured OGD JSON URL returned HTTP 200 with 0 bytes. | Refresh OGD IDs/API path and add a test that fails on empty 200 responses. |
| UIC | failed live probe | No artifact landed. | Configured XLS URL returned HTTP 404. | Refresh UIC resource URLs or document access limits/subscription boundaries. |
| GDELT history | failed live probe | No artifact landed. | Bounded DOC history probe also returned HTTP 429. | Keep default backfill disabled; add rate-limit handling and a safe `--max-pages`/`--dry-run` mode. |

Interpretation:

- Currently live-usable raw collection is proven for RSS and one KSH table.
- Eurostat and World Bank can collect catalogues but need parser fixes before
  their dataset/series pulls can be called working.
- GDELT, Statistics Austria, UIC, and historical GDELT need source-specific
  fixes or rate-limit handling before classmates rely on them.

## Parser Inventory

| Parser | Module | Source family | What it collects | Storage shape | Downstream transform | Status |
|---|---|---|---|---|---|---|
| Eurostat | `src/railway_lakehouse/bronze/sources/eurostat.py` | Eurostat catalogue and SDMX TSV API | Rail, regional transport, and transport safety statistical datasets. Lands catalogue plus raw gzipped TSV datasets. | `bronze/stats/eurostat/<dataset_id>/ingest_date=YYYY-MM-DD/<dataset_id>.tsv.gz` plus `.meta.json`. | `silver/stats/merge.py::read_eurostat_tsv`, then crosswalk to canonical features. | Unit-tested discovery; live catalogue partial; dataset URL cleanup needed. |
| World Bank | `src/railway_lakehouse/bronze/sources/worldbank.py` | World Bank Indicators API | Indicator catalogue and all-country time series JSON for rail-related indicators. | `bronze/stats/worldbank/<indicator>/ingest_date=YYYY-MM-DD/<indicator>.json` plus `.meta.json`. | `silver/stats/merge.py::read_worldbank_json`, then crosswalk. | Unit-tested discovery fallback; live catalogue partial; indicator validation needed. |
| GDELT recent | `src/railway_lakehouse/bronze/sources/gdelt.py` | GDELT DOC 2.0 API | Recent rail-related news article lists for HU/AT source countries. | `bronze/news/gdelt/<geo>/ingest_date=YYYY-MM-DD/gdelt_doc_<geo>_<timespan>.json` plus `.meta.json`. | `silver/news/extract.py::gdelt_passthrough` or article extraction, then Gold news aggregation. | Query unit-tested; live probe hit 429. |
| RSS media | `src/railway_lakehouse/bronze/sources/rss_media.py` | HU/AT media and official RSS feeds | Whole RSS feeds, unfiltered, to avoid losing sparse rail items. | `bronze/news/rss/<geo_outlet>/ingest_date=YYYY-MM-DD/<geo_outlet>.xml` plus `.meta.json`. | Future RSS parser should extract article records, then `silver/news/extract.py`. | Live-ok for Telex and Index feeds; direct unit tests still needed. |
| KSH | `src/railway_lakehouse/bronze/sources/ksh.py` | Hungarian Central Statistical Office STADAT files | Seeded Hungarian transport/rail XLSX tables. | `bronze/stats/ksh/<dataset_id>/ingest_date=YYYY-MM-DD/<filename>.xlsx` plus `.meta.json`. | Future KSH parser should read XLSX and emit `StatFact` rows. | Live-ok for `ksh_rail_freight`; not scheduled; tests needed. |
| Statistik Austria | `src/railway_lakehouse/bronze/sources/statistik_austria.py` | Statistics Austria OGD JSON/CSV | Seeded Austrian transport/rail OGD datasets. | `bronze/stats/statistik_austria/<dataset_id>/ingest_date=YYYY-MM-DD/<ogd_id>.json|csv` plus `.meta.json`. | Future Austrian parser should read JSON-stat/CSV and emit `StatFact` rows. | Live seed failed empty; OGD IDs/API path need refresh. |
| UIC | `src/railway_lakehouse/bronze/sources/uic.py` | UIC RAILISA/statistics files | International railway statistics files for infrastructure, traffic, rolling stock. | `bronze/stats/uic/<dataset_id>/ingest_date=YYYY-MM-DD/<filename>.xls` plus `.meta.json`. | Future UIC parser should read XLS and emit `StatFact` rows, then slice HU/AT in Silver. | Live seed 404; resource URLs/access need refresh. |
| GDELT history | `src/railway_lakehouse/bronze/sources/past_recordings.py` | GDELT DOC history and GKG v1 files | Historical rail-related news pages or raw GKG daily zip files. | `bronze/news/gdelt_history/<dataset_id>/ingest_date=YYYY-MM-DD/<file>` plus `.meta.json`. | Future history parser should normalize article records before `NewsFeature` extraction. | Exists but dangerous by default; bounded probe hit 429; add safe limits before use. |

## Feature Coverage Matrix

Legend:

- `P`: primary intended source.
- `C`: candidate source; parser or mapping still needed.
- `N`: news-derived feature.
- `-`: not expected from this source.

| Feature / output | Eurostat | World Bank | KSH | Statistik Austria | UIC | RSS | GDELT |
|---|---|---|---|---|---|---|---|
| `rail_freight_tonnes` | P | C | P | C | C | - | - |
| `rail_freight_tonne_km` | P | P | C | C | P | - | - |
| `rail_passengers` | P | C | P | C | C | - | - |
| `rail_passenger_km` | P | P | C | C | P | - | - |
| `rail_network_length_km` | P | P | C | C | P | - | - |
| `rail_electrified_km` | P | C | - | C | P | - | - |
| `rail_accidents` | P | - | - | C | - | - | - |
| `rail_fatalities` | P | - | - | C | - | - | - |
| `rail_investment` | C | - | C | C | - | N | N |
| `rail_rolling_stock` | P | - | C | C | P | - | - |
| `rail_employees` | C | - | C | C | C | - | - |
| `news_article_count` | - | - | - | - | - | N | N |
| `news_n_<event_type>` | - | - | - | - | - | N | N |
| `news_sentiment_mean` | - | - | - | - | - | N | N |
| `news_share_negative` | - | - | - | - | - | N | N |
| `news_total_investment_eur` | - | - | - | - | - | N | N |
| `news_op_<operator>` | - | - | - | - | - | N | N |

## Work Waves

### Wave 0 - Evidence And Split Points

Owner: QA / docs owner.

Status: done for this pass.

Deliverables:

- Bounded live evidence manifest under `output/evidence/parser-live-check-2026-06-21/`.
- This parser work log.
- Progress log entries that state which sources are live-ok, partial, or failed.

### Wave 1 - Make Bronze Parsers Reliably Collect Real Data

Parallel owner tasks:

| Owner track | Files | Expected behavior | Verification |
|---|---|---|---|
| Eurostat owner | `bronze/sources/eurostat.py`, `tests/test_bronze_characterization.py` | Strip quoted TOC codes and land at least one real TSV dataset in a bounded run. | Unit fixture for quoted codes, then bounded live evidence artifact. |
| World Bank owner | `bronze/sources/worldbank.py`, Silver stats tests | Discovery keeps confirmed rail indicators and rejects API error payloads. | Unit test with API error JSON; bounded live evidence for one known rail indicator. |
| RSS owner | `bronze/sources/rss_media.py` | Feed registry health is checked; at least HU and AT feeds land when reachable. | Mocked HTTP tests plus bounded live feed manifest. |
| GDELT owner | `bronze/sources/gdelt.py`, `bronze/sources/past_recordings.py` | Bounded live query handles 429 with retry/backoff and never starts long backfill accidentally. | Mocked 429 test, safe CLI flags, bounded live success or documented rate-limit failure. |
| KSH owner | `bronze/sources/ksh.py` | All seeded STADAT tables are verified or marked stale. | Mocked table fetch tests plus bounded live manifest. |
| Statistik Austria owner | `bronze/sources/statistik_austria.py` | Refresh OGD IDs/API path and reject empty 200 responses. | Mocked empty-response test plus bounded live JSON/CSV artifact. |
| UIC owner | `bronze/sources/uic.py` | Refresh reachable resources or document access/subscription limits. | Mocked 404 test plus bounded live artifact or explicit access note. |

### Wave 2 - Turn Live Probe Into A Repo Command

Owner: DevEx / Bronze owner.

Goal: replace ad hoc live probing with a documented command.

Expected command shape:

```powershell
python -m railway_lakehouse.bronze.live_check --sources eurostat,rss,ksh --out output/evidence/live-bronze --max-artifacts 10
```

Requirements:

- Local output mode must not require MinIO.
- It must write raw files and `.meta.json` sidecars using the same Bronze layout.
- It must write a manifest with source status, artifact counts, byte counts, and failures.
- It must default to bounded behavior and require explicit flags for long backfills.

### Wave 3 - Silver Parsers For Proven Bronze Artifacts

Owner: Silver stats and Silver news owners.

Start only after the related Bronze parser has a real artifact.

Tasks:

- KSH XLSX -> `StatFact`
- Statistics Austria JSON-stat/CSV -> `StatFact`
- UIC XLS -> `StatFact`
- RSS XML -> article records -> `NewsFeature`
- GDELT ArtList JSON -> article records or passthrough -> `NewsFeature`

### Wave 4 - Gold, Spark, And Report Evidence

Owner: Gold / Spark / report owners.

Start only after fixture Silver rows exist.

Tasks:

- Build Gold `(geo, year)` feature matrix from verified Silver rows.
- Add Spark job that reads Gold Parquet and writes row-count/aggregate evidence.
- Draft report and presentation using only files in `output/evidence/`.

## GitHub Collaboration Checklist

Before pushing public:

- Keep `.env` and credentials out of the repo.
- Keep live evidence artifacts only if file size and licensing are acceptable for coursework sharing.
- Include this file, `docs/GAP_REGISTER.md`, `docs/WORK_SPLIT.md`, and `docs/VERIFICATION.md`.
- Make the first GitHub issue batch from the Wave 1 owner tasks above.
- Do not advertise MinIO, Ollama, Spark, or full E2E as working until their evidence exists.

Suggested repo name: `pol3et/railway-lakehouse`.
