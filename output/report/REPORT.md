# Railway Lakehouse Evidence Report

Draft date: 2026-06-24

This report is evidence-grounded: each quantitative claim points to a committed artifact under `output/evidence/`, and the Evidence Index maps headline claims to JSON keys.

## Problem And Dataset

The course project builds a railway lakehouse for Hungary and Austria, with international context where the source data is broader. The current reportable dataset combines rail statistics and rail-news inputs, then turns verified statistical series into an analysis-ready Gold table.

| Source | Format | Current project role | Evidence |
|---|---|---|---|
| World Bank | JSON time series | Proven statistics source for the current Gold matrix: `artifact_count=3`, `byte_count=17065815`, `status=passed`. | `output/evidence/inventory-live-2026-06-23/manifest.json` |
| Eurostat | TSV/SDMX | Parser path exists, but the 2026-06-23 live inventory run recorded `status=failed` on catalogue fetch; Eurostat-to-Gold mapping remains a gap. | `output/evidence/inventory-live-2026-06-23/manifest.json` |
| KSH | XLSX | Raw Hungarian rail workbooks live-check passed with `artifact_count=6`, `byte_count=92509`. Silver XLSX parsing is still open. | `output/evidence/ksh-live-check-2026-06-22-current/manifest.json` |
| Statistik Austria | ODS | Live probe found `5` rail ODS files and `rolling_stock_total_2024=20863`; ODS-to-Silver parsing is still open. | `output/evidence/statistik-austria-live-check-2026-06-22/manifest.json` |
| UIC | PDF | Raw public UIC PDF live-check passed with `artifact_count=2`, `byte_count=2109240`. PDF extraction is still open. | `output/evidence/uic-live-check-2026-06-22/manifest.json` |
| RSS media | XML | Raw RSS collection is partially live-proven with `artifact_count=9`, `byte_count=496138`, and `status=partial`. Live LLM extraction is not proven. | `output/evidence/rss-feed-health-2026-06-22/manifest.json` |
| GDELT | JSON DOC API | Recent live probe did not land usable bytes: `status=failed`, `artifact_count=0`. Fixture parsing exists, but live collection needs follow-up. | `output/evidence/gdelt-live-check-2026-06-22/manifest.json` |

## Architecture

The project uses a Bronze -> Silver -> Gold -> Spark -> report data spine. Bronze lands immutable raw web data, Silver normalizes rows and validates schema, Gold builds a deterministic feature matrix, Spark runs the Big Data evidence job, and this report quotes only committed outputs.

Architecture references:

- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
- [docs/DATA_CONTRACTS.md](../../docs/DATA_CONTRACTS.md)

The raw-to-feature boundary is deterministic for numeric stats: the Gold builder does not use an LLM to rewrite numeric values. The current proven Gold output is backed by `output/evidence/inventory-live-2026-06-23/counts.json` and `output/evidence/inventory-live-2026-06-23/inventory_samples.json`.

## Proven End-To-End Result Today

The strongest proven data run is the live World Bank Bronze -> Silver -> Gold path using a local Bronze root. It produced a Gold Parquet at `output/evidence/inventory-live-2026-06-23/railway_ml.parquet`, summarized by `output/evidence/inventory-live-2026-06-23/counts.json`.

Headline Gold result:

- `rows=2968`, shown in prose as 2,968 rows, from `output/evidence/inventory-live-2026-06-23/counts.json`.
- `columns=4`, shown as 4 columns, from `output/evidence/inventory-live-2026-06-23/counts.json`.
- `column_names=["geo","year","rail_freight_tonne_km","rail_network_length_km"]`, from `output/evidence/inventory-live-2026-06-23/counts.json`.
- `geos_count=151`, shown as 151 geos, from `output/evidence/inventory-live-2026-06-23/counts.json`.
- `year_min=1995` and `year_max=2021`, shown as 1995-2021, from `output/evidence/inventory-live-2026-06-23/counts.json`.
- `at_rows=27` and `hu_rows=27`, shown as 27 AT rows and 27 HU rows, from `output/evidence/inventory-live-2026-06-23/counts.json`.

Concrete sample values are copied from `output/evidence/inventory-live-2026-06-23/inventory_samples.json`:

- AT in 1995 has `rail_freight_tonne_km=13715.0` and `rail_network_length_km=5672.0`.
- HU in 1995 has `rail_freight_tonne_km=8337.0` and `rail_network_length_km=7988.0`.

The same run persisted and reloaded Silver stats with `reloaded_rows=35112` in `output/evidence/inventory-live-2026-06-23/inventory_samples.json`. The Silver feature counts in that artifact are `rail_freight_tonne_km=17556` and `rail_network_length_km=17556`, both sourced from World Bank.

The earlier first-real Gold smoke remains useful history, but it is not the headline result: `output/evidence/first-real-gold-local-stats-v2/counts.json` recorded `rows=2139`, `columns=3`, and `geos_count=116`. The richer `rows=2968`, `columns=4` inventory run supersedes it for this draft.

## Object Storage

Local MinIO object storage is proven by the bounded smoke manifest at `output/evidence/minio-smoke/manifest.json`.

- `status=passed`
- `roundtrip_ok=true`
- `buckets=["bronze","silver","gold"]`
- `bytes_written=32`
- `bytes_read=32`

This proves local S3-style object storage and bucket setup. It does not prove the full live MinIO Bronze -> Silver -> Gold statistics read path; that limitation is tracked as GAP-013 in [docs/GAP_REGISTER.md](../../docs/GAP_REGISTER.md).

## Bronze Source Coverage

The Bronze coverage below cites committed manifests only. It intentionally does not cite ignored raw Bronze subtrees, because those raw bytes are absent on clean checkouts.

| Source | Live-check status | Quantitative evidence | Evidence artifact |
|---|---|---|---|
| KSH | passed | `artifact_count=6`, `byte_count=92509`, HTTP statuses all 200 | `output/evidence/ksh-live-check-2026-06-22-current/manifest.json` |
| UIC | passed | `artifact_count=2`, `byte_count=2109240`, HTTP statuses all 200 | `output/evidence/uic-live-check-2026-06-22/manifest.json` |
| World Bank inventory run | passed for World Bank; failed for Eurostat | World Bank `artifact_count=3`, `byte_count=17065815`; Eurostat `status=failed` | `output/evidence/inventory-live-2026-06-23/manifest.json` |
| World Bank indicator probe | valid probe | `3` confirmed rail indicators; `2` invalid/error-envelope controls rejected | `output/evidence/worldbank-live-check-2026-06-22/manifest.json` |
| RSS feeds | partial | `artifact_count=9`, `byte_count=496138`, one `404` feed failure | `output/evidence/rss-feed-health-2026-06-22/manifest.json` |
| Statistik Austria | probe result | `5` real rail ODS files; `rolling_stock_total_2024=20863` | `output/evidence/statistik-austria-live-check-2026-06-22/manifest.json` |
| GDELT recent | failed | `artifact_count=0`; HU returned HTTP `429`; AT hit remote disconnect | `output/evidence/gdelt-live-check-2026-06-22/manifest.json` |

## Spark Results

GAP-009 has landed in this checkout, so the Spark section is filled from committed evidence rather than left as a pending placeholder. The evidence manifest is `output/evidence/spark/manifest.json`.

Spark evidence:

- `status=passed`
- `spark_version=4.1.2`
- `java_version=21.0.11`
- input Gold `input_rows=2968`, `input_columns=4`
- output coverage `output_rows=2968`, `output_columns=5`
- `partitions_written=1`

The Spark job reads the real Gold Parquet and writes coverage output under `output/evidence/spark/coverage_by_geo_year`. A future rerun remains pending for a larger dataset after GAP-013, GAP-006, and GAP-023 add the remaining live MinIO, news, and Eurostat coverage.

## Known Gaps And Not-Yet-Proven Scope

- GAP-013: the headline Gold result used the local `--bronze-root` path, not the live MinIO stats read branch. The live MinIO branch still drops World Bank, so a true live MinIO stats matrix is not proven. See [docs/GAP_REGISTER.md](../../docs/GAP_REGISTER.md).
- GAP-023: Eurostat raw/stat paths exist, but Eurostat-to-Gold mapping remains incomplete. The 2026-06-23 inventory run recorded Eurostat `status=failed` in `output/evidence/inventory-live-2026-06-23/manifest.json`.
- GAP-006: KSH XLSX, Statistik Austria ODS, UIC PDF readers, and persisted news failure accounting remain open. The news feature status is `LLM-pending (Ollama not installed); NewsFeature schema frozen, extractor mocked in tests` in `output/evidence/inventory-live-2026-06-23/inventory_samples.json`.
- GAP-019: automatic updates are not yet deployable; the scheduler remains a follow-up in [docs/GAP_REGISTER.md](../../docs/GAP_REGISTER.md).
- Full live MinIO/Ollama/news/Spark end-to-end execution is not claimed by this report. The proven pieces are the committed Gold inventory run, MinIO smoke, and Spark coverage job cited above.

## Evidence Index

| Headline claim | Evidence path | JSON key/value |
|---|---|---|
| Current Gold rows | `output/evidence/inventory-live-2026-06-23/counts.json` | `rows=2968` |
| Current Gold columns | `output/evidence/inventory-live-2026-06-23/counts.json` | `columns=4` |
| Current Gold column names | `output/evidence/inventory-live-2026-06-23/counts.json` | `column_names=["geo","year","rail_freight_tonne_km","rail_network_length_km"]` |
| Current Gold geos | `output/evidence/inventory-live-2026-06-23/counts.json` | `geos_count=151` |
| Current Gold year range | `output/evidence/inventory-live-2026-06-23/counts.json` | `year_min=1995`; `year_max=2021` |
| AT/HU row counts | `output/evidence/inventory-live-2026-06-23/counts.json` | `at_rows=27`; `hu_rows=27` |
| Gold sample AT 1995 | `output/evidence/inventory-live-2026-06-23/inventory_samples.json` | `geo=AT`; `year=1995`; `rail_freight_tonne_km=13715.0`; `rail_network_length_km=5672.0` |
| Gold sample HU 1995 | `output/evidence/inventory-live-2026-06-23/inventory_samples.json` | `geo=HU`; `year=1995`; `rail_freight_tonne_km=8337.0`; `rail_network_length_km=7988.0` |
| Silver stats reloaded rows | `output/evidence/inventory-live-2026-06-23/inventory_samples.json` | `silver_stats.reloaded_rows=35112` |
| Silver stats feature counts | `output/evidence/inventory-live-2026-06-23/inventory_samples.json` | `rail_freight_tonne_km=17556`; `rail_network_length_km=17556` |
| Gold sample metadata | `output/evidence/inventory-live-2026-06-23/inventory_samples.json` | `gold.rows=2968`; `gold.geos=151` |
| World Bank live inventory status | `output/evidence/inventory-live-2026-06-23/manifest.json` | `source=worldbank`; `status=passed`; `artifact_count=3`; `byte_count=17065815` |
| Eurostat live inventory status | `output/evidence/inventory-live-2026-06-23/manifest.json` | `source=eurostat`; `status=failed` |
| Crosswalk mappings | `output/evidence/inventory-live-2026-06-23/crosswalk_cache.json` | `Rail lines (total route-km)=rail_network_length_km`; `Railways, goods transported (million ton-km)=rail_freight_tonne_km` |
| Earlier Gold smoke | `output/evidence/first-real-gold-local-stats-v2/counts.json` | `rows=2139`; `columns=3`; `geos_count=116` |
| MinIO smoke status | `output/evidence/minio-smoke/manifest.json` | `status=passed`; `roundtrip_ok=true`; `bytes_written=32`; `bytes_read=32` |
| MinIO buckets | `output/evidence/minio-smoke/manifest.json` | `buckets=["bronze","silver","gold"]` |
| KSH Bronze coverage | `output/evidence/ksh-live-check-2026-06-22-current/manifest.json` | `artifact_count=6`; `byte_count=92509` |
| UIC Bronze coverage | `output/evidence/uic-live-check-2026-06-22/manifest.json` | `artifact_count=2`; `byte_count=2109240` |
| World Bank indicator probe | `output/evidence/worldbank-live-check-2026-06-22/manifest.json` | `confirmed_rail_indicators=3`; rejected controls `2` |
| RSS Bronze coverage | `output/evidence/rss-feed-health-2026-06-22/manifest.json` | `artifact_count=9`; `byte_count=496138`; `status=partial` |
| Statistik Austria probe | `output/evidence/statistik-austria-live-check-2026-06-22/manifest.json` | `landed_artifacts=5`; `rolling_stock_total_2024=20863` |
| GDELT live probe | `output/evidence/gdelt-live-check-2026-06-22/manifest.json` | `status=failed`; `artifact_count=0`; `http_status=429` |
| Spark job status | `output/evidence/spark/manifest.json` | `status=passed`; `spark_version=4.1.2`; `java_version=21.0.11` |
| Spark input shape | `output/evidence/spark/manifest.json` | `input_rows=2968`; `input_columns=4` |
| Spark output shape | `output/evidence/spark/manifest.json` | `output_rows=2968`; `output_columns=5`; `partitions_written=1` |
