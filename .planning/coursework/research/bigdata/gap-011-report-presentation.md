# GAP-011 Report And Presentation Research

Date: 2026-06-24

Workflow: `research-orchestrator` was invoked before planning or edits. Local files were researched first with `rg` and direct reads. No external research was needed because GAP-011 drafts must quote committed repo evidence and do not introduce new library/API/domain claims.

## Local Search And Files Reviewed

- `rg --files` confirmed `output/report/` and `output/presentation/` were absent at intake and that the committed evidence roots include `output/evidence/inventory-live-2026-06-23/`, `output/evidence/minio-smoke/`, and `output/evidence/spark/`.
- `rg -n "GAP-011|report/draft|Data Inventory|World Bank|MinIO|Spark|GAP-013|GAP-006|GAP-009" AGENTS.md docs README.md TASK.md pyproject.toml` located the report requirements, source inventory, dashboard status, and current gap rows.
- `AGENTS.md` requires local-first research, the research note, progress-log updates, no fabricated evidence, and dashboard sync when a gap/report state changes.
- `docs/STATE_AND_ROADMAP.md` contains the Data Inventory table and current scope boundary: World Bank/Eurostat/RSS/GDELT are scheduled or tested in fixture/local paths; KSH, Statistik Austria, and UIC have live raw-byte evidence but no Silver parser; GDELT live failed.
- `docs/GAP_REGISTER.md` shows GAP-011 open at intake, GAP-013 open for the live-MinIO World Bank branch, GAP-006 open for remaining parsers/news failure accounting, and GAP-009 closed with Spark evidence.
- `docs/TASKS.md` shows `report/draft` as todo and `spark/evidence-job` as done.
- `docs/VERIFICATION.md` documents the output layout, current full-suite status, MinIO smoke, and Spark evidence command/results.
- `docs/index.html` has a live dashboard row for GAP-011 that still says report started but not done.

## Evidence JSON Read

- `output/evidence/inventory-live-2026-06-23/counts.json`
  - `rows=2968`
  - `columns=4`
  - `column_names=["geo","year","rail_freight_tonne_km","rail_network_length_km"]`
  - `geos_count=151`
  - `year_min=1995`
  - `year_max=2021`
  - `at_rows=27`
  - `hu_rows=27`
- `output/evidence/inventory-live-2026-06-23/manifest.json`
  - World Bank `status=passed`
  - World Bank `artifact_count=3`
  - World Bank `byte_count=17065815`
  - Eurostat `status=failed` with `RemoteDisconnected`
- `output/evidence/inventory-live-2026-06-23/inventory_samples.json`
  - Gold AT 1995: `rail_freight_tonne_km=13715.0`, `rail_network_length_km=5672.0`
  - Gold HU 1995: `rail_freight_tonne_km=8337.0`, `rail_network_length_km=7988.0`
  - Silver stats `reloaded_rows=35112`, both World Bank feature counts `17556`
  - MinIO Silver upload demonstration: `attempted=true`, `ok=true`, `size_bytes=35961`
  - News feature status: `LLM-pending (Ollama not installed); NewsFeature schema frozen, extractor mocked in tests`
- `output/evidence/inventory-live-2026-06-23/crosswalk_cache.json`
  - `Rail lines (total route-km)` maps to `rail_network_length_km`
  - `Railways, goods transported (million ton-km)` maps to `rail_freight_tonne_km`
- `output/evidence/first-real-gold-local-stats-v2/counts.json`
  - Earlier smoke: `rows=2139`, `columns=3`, `geos_count=116`, `year_min=1995`, `year_max=2021`, AT/HU present.
- `output/evidence/minio-smoke/manifest.json`
  - `status=passed`
  - `roundtrip_ok=true`
  - `buckets=["bronze","silver","gold"]`
  - `bytes_written=32`, `bytes_read=32`
- Bronze source manifests:
  - KSH: `output/evidence/ksh-live-check-2026-06-22-current/manifest.json`, `artifact_count=6`, `byte_count=92509`, `status=passed`.
  - UIC: `output/evidence/uic-live-check-2026-06-22/manifest.json`, `artifact_count=2`, `byte_count=2109240`, `status=passed`.
  - World Bank bounded probe: `output/evidence/worldbank-live-check-2026-06-22/manifest.json`, three confirmed indicators and two rejected error envelopes.
  - RSS: `output/evidence/rss-feed-health-2026-06-22/manifest.json`, `artifact_count=9`, `byte_count=496138`, `status=partial`, one 404.
  - Statistik Austria: `output/evidence/statistik-austria-live-check-2026-06-22/manifest.json`, five real rail ODS files; no rail OGD dataset; `rolling_stock_total_2024=20863`.
  - GDELT: `output/evidence/gdelt-live-check-2026-06-22/manifest.json`, `status=failed`, `artifact_count=0`, HU HTTP 429 and AT remote disconnect.
- Spark evidence now exists despite older GAP-011 task text:
  - `output/evidence/spark/manifest.json`
  - `status=passed`
  - `spark_version=4.1.2`
  - `java_version=21.0.11`
  - input `2968` rows x `4` columns
  - output `2968` rows x `5` columns
  - `partitions_written=1`

## Implementation Conclusions

- Treat committed evidence JSON files as the source of truth for all report/presentation numbers.
- Do not cite paths under `output/evidence/**/bronze/`, because those raw Bronze trees are ignored by `.gitignore`.
- The task text says the Spark section should stay pending until GAP-009 lands. Local repository evidence shows GAP-009 has landed and is committed, so the honest report should cite `output/evidence/spark/manifest.json` and should not claim Spark is unbuilt.
- Keep known gaps explicit: GAP-013 live-MinIO stats path, GAP-006 remaining parsers/news extraction failure accounting, GAP-023 Eurostat-to-Gold mapping, and GAP-019 deployable automatic updates.
- Add a deterministic unit test that reads report/presentation text and evidence JSON directly from committed repo deliverables, not from `coursework/` data or services.
