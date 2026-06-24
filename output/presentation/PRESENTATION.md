# Railway Lakehouse Presentation Draft

## Slide 1 - Title

Railway Lakehouse: Evidence-Grounded Hungary and Austria Rail Data Pipeline

> Speaker notes: The draft is grounded in committed evidence under `output/evidence/`. The strongest current result is the World Bank Gold matrix recorded in `output/evidence/inventory-live-2026-06-23/counts.json`.

## Slide 2 - Problem

Build a railway data collection and analysis path that can support automatic updates, Big Data processing, and an auditable course report.

> Speaker notes: The report scope is honest: the current proven statistics output is World Bank-backed; source expansion and live MinIO end-to-end wiring remain tracked gaps.

## Slide 3 - Architecture

Bronze raw landing -> Silver normalized rows -> Gold feature matrix -> Spark coverage job -> report and presentation.

> Speaker notes: The numeric evidence now spans Gold counts in `output/evidence/inventory-live-2026-06-23/counts.json`, MinIO smoke in `output/evidence/minio-smoke/manifest.json`, and Spark coverage in `output/evidence/spark/manifest.json`.

## Slide 4 - Data Sources

Current source evidence:

- World Bank inventory run: `artifact_count=3`, `byte_count=17065815`, `status=passed` from `output/evidence/inventory-live-2026-06-23/manifest.json`.
- KSH: `artifact_count=6`, `byte_count=92509` from `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`.
- UIC: `artifact_count=2`, `byte_count=2109240` from `output/evidence/uic-live-check-2026-06-22/manifest.json`.
- RSS: `artifact_count=9`, `byte_count=496138`, `status=partial` from `output/evidence/rss-feed-health-2026-06-22/manifest.json`.

> Speaker notes: The sources table in the report adds Statistik Austria and GDELT. The key point is that raw-source evidence is distinct from Silver/Gold contribution.

## Slide 5 - Proven Gold Result

The current proven Gold output is `rows=2968`, `columns=4`, `geos_count=151`, `year_min=1995`, `year_max=2021`, with `at_rows=27` and `hu_rows=27`, all from `output/evidence/inventory-live-2026-06-23/counts.json`.

Columns: `geo`, `year`, `rail_freight_tonne_km`, `rail_network_length_km`, from `output/evidence/inventory-live-2026-06-23/counts.json`.

Samples from `output/evidence/inventory-live-2026-06-23/inventory_samples.json`:

- AT `year=1995`, `rail_freight_tonne_km=13715.0`, `rail_network_length_km=5672.0`.
- HU `year=1995`, `rail_freight_tonne_km=8337.0`, `rail_network_length_km=7988.0`.

> Speaker notes: The earlier smoke was `rows=2139`, `columns=3`, `geos_count=116` in `output/evidence/first-real-gold-local-stats-v2/counts.json`; it is useful history but not the headline result.

## Slide 6 - MinIO Storage

Local object storage smoke passed with `status=passed`, `roundtrip_ok=true`, `bytes_written=32`, `bytes_read=32`, and buckets `bronze`, `silver`, `gold` in `output/evidence/minio-smoke/manifest.json`.

> Speaker notes: This proves the local S3-style storage surface, not the complete live MinIO stats path. GAP-013 still tracks the missing live-MinIO World Bank read path.

## Slide 7 - Spark Result

GAP-009 is landed in this checkout. Spark evidence in `output/evidence/spark/manifest.json` records `status=passed`, `spark_version=4.1.2`, `java_version=21.0.11`, input `2968` rows x `4` columns, output `2968` rows x `5` columns, and `partitions_written=1`.

> Speaker notes: The future placeholder is the larger rerun after more sources and live MinIO/news are proven. This draft does not invent those future numbers.

## Slide 8 - Honest Gaps

- GAP-013: the headline Gold used local `--bronze-root`, not the live MinIO stats branch.
- GAP-023: Eurostat-to-Gold mapping is not complete; the inventory manifest records Eurostat `status=failed` in `output/evidence/inventory-live-2026-06-23/manifest.json`.
- GAP-006: live Ollama/news extraction is not proven; `output/evidence/inventory-live-2026-06-23/inventory_samples.json` states `LLM-pending (Ollama not installed); NewsFeature schema frozen, extractor mocked in tests`.
- GAP-019: deployable automatic updates are still future work.

> Speaker notes: These gaps are part of the value of the report: it separates proven work from the next work needed for a fuller course submission.

## Slide 9 - Conclusion And Next Steps

The project now has a defensible evidence chain: committed Gold counts, committed MinIO smoke, committed Spark coverage, and this report/presentation draft guarded by a deterministic evidence-link test.

> Speaker notes: Next steps are to close the live-MinIO World Bank path, add Eurostat-to-Gold mapping, run live news extraction, and rerun Spark on the larger dataset. No future row counts are claimed here.
