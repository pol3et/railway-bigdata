# State And Roadmap

Snapshot: 2026-06-23. Authoritative status + completion roadmap for
`bigdata/course_proj`.

Grounded in `docs/GAP_REGISTER.md`, the Bronze source adapters + Silver parsers,
`pipeline.py` / `gold/build.py`, and committed evidence manifests under
`output/evidence/`. Research routed via `research-orchestrator` (Context7,
Tavily, Exa, Ref); full query/citation log in
`.planning/coursework/research/bigdata/state-analysis-spark-roadmap-2026-06-23.md`.

Nothing here is claimed as run that lacks a committed evidence artifact.

## Current State

Phase: end of the storage-boundary phase / start of the Spark phase. The
pipeline reads `web sources -> Bronze -> Silver -> Gold -> (Spark) -> report`.
Today the train is at **Gold**; the next stop is **Spark**.

| Stage | Signal | State |
|---|---|---|
| Bronze (ingest) | operational | Raw landing works. 4 sources scheduled (Eurostat, World Bank, GDELT, RSS); KSH, Statistik Austria, UIC, GDELT-history are live-proven but **not scheduled** (GAP-005). |
| Silver (normalize) | partial | World Bank + Eurostat stats and RSS + GDELT news normalize correctly inside fixture/local pipeline paths. Local Parquet persistence now exists for `StatFact` and successful `NewsFeature` rows; MinIO/s3fs persistence, extraction-failure accounting, and `silver/run.py` remain open. |
| Gold (feature matrix) | partial | The `(geo, year)` feature-matrix builder works and writes Parquet. Fixture evidence exists, and a first real stats-only Gold was produced from bounded local Eurostat + World Bank Bronze landing: `output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet` with 2,139 rows x 3 columns. The current real Gold feature is World Bank `rail_network_length_km`; Eurostat raw bytes landed but remained unmapped in this smoke. `gold/run.py` still cannot load persisted Silver from storage yet (GAP-007). |
| Spark (big-data jobs) | not built | No `spark_jobs/` package exists. The registered command `python -m railway_lakehouse.spark_jobs.coverage` cannot import (GAP-009). This is the graded deliverable. |
| Report / presentation | not started | Blocked: every claim must cite generated evidence that does not exist yet (GAP-011). |

### At A Glance

- `python -m pytest -q`: **87 passed**, 0 xfail.
- Bronze sources built: **8**; scheduled: **4**; live-proven (raw bytes): **4**
  (RSS, KSH, UIC, World Bank) + Statistik Austria probed.
- Stats parsers to `StatFact`: **2 / 5**. News parser stages to `NewsFeature`: **3 / 3**.
- Gaps closed: **5 / 11** (GAP-001..004, 008).
- End-to-end Bronze->Silver->Gold artifacts:
  - fixture: `output/evidence/fixture-e2e/railway_ml.parquet` = **4 rows x 3 cols**, news skipped.
  - first real stats-only run: `output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet` = **2,139 rows x 3 cols**, World Bank `rail_network_length_km`, includes `AT` and `HU`, news skipped.

### Evidence Reality Check

Earlier source-specific live runs proved **raw Bronze landing only**, not Silver/Gold.
The local stats evidence additionally proves a bounded raw-Bronze-to-Gold
reproduction for World Bank route-km; the MinIO smoke proves local object
storage reachability only, not a full MinIO/Ollama/news/Spark run.

- KSH: 6 STADAT XLSX, HTTP 200, 92,509 B
  (`output/evidence/ksh-live-check-2026-06-22-current/manifest.json`).
- RSS: 9 feeds, ~496 KB, one 404 (partial)
  (`output/evidence/rss-feed-health-2026-06-22/`).
- UIC: 2 public PDFs, HTTP 200, 2,109,240 B
  (`output/evidence/uic-live-check-2026-06-22/manifest.json`).
- Statistik Austria: 5 rail ODS, HTTP 200
  (`output/evidence/statistik-austria-live-check-2026-06-22/manifest.json`).
- World Bank: 3 confirmed indicators with valid time series; 2 error envelopes
  correctly rejected (`output/evidence/worldbank-live-check-2026-06-22/manifest.json`).
- GDELT live: **failed** (HU HTTP 429, AT RemoteDisconnected) -> fixture-only.

There is no full MinIO/Ollama/news Silver/Gold output and no Spark output.

## Data Inventory

What each source fetches, and whether it reaches structured Silver rows today.

| Source | Format | Geo · Topic | Bronze (collection) | Silver (-> rows) |
|---|---|---|---|---|
| `eurostat` | TSV/.gz (SDMX) | EU incl. HU/AT · rail passengers, freight, network, electrification, safety | scheduled · live-capable | StatFact · tested |
| `worldbank` | JSON | global (HU/AT picked in Silver) · route-km, tonne-km, passenger-km, since 1960 | scheduled · live-proven | StatFact · tested |
| `rss_media` | XML | HU/AT media + MAV/OEBB press · all-topic, rail-filtered in Silver | scheduled · live-proven | ArticleRecord · tested |
| `gdelt` | JSON (DOC 2.0) | HU + AT · rail news | scheduled · **live FAILS (429)** | ArticleRecord · tested (fixture) |
| `ksh` | XLSX | HU only · freight, passengers, rolling stock, network, regional + narrow-gauge lines | live-proven · **not scheduled** | **MISSING — no XLSX reader** |
| `statistik_austria` | ODS | AT only · freight, rolling-stock fleet (passengers/network are login-only -> use Eurostat) | live-proven · **not scheduled** | **MISSING — no ODS reader** |
| `uic` | PDF | global UIC members · passenger-km, tonne-km, network, rolling stock, employees | live-proven · **not scheduled** | **MISSING — no PDF extractor** |
| `past_recordings` | JSON · GKG csv.zip | HU + AT · deep news backfill (DOC ~10y; GKG v1 1979-2016) — the real volume play | CLI one-off · not scheduled | DOC pages OK · **GKG csv MISSING** |

### Extracted (proven) today

- World Bank rail series -> `StatFact` (verbatim values, ISO3->geo map).
- Eurostat rail series (TSV incl. gzip) -> `StatFact` (flag-stripped, labels mapped).
- RSS XML and GDELT ArtList JSON -> `ArticleRecord` (stable IDs).
- `ArticleRecord` -> validated `NewsFeature` (Ollama; tested with mocked LLM output).
- A unified `(geo, year)` Gold matrix from Bronze fixtures (proven on 4 rows).

### Extractable next (bytes already land; only parsers missing)

- KSH XLSX -> `StatFact` (openpyxl/`read_excel` -> the dormant
  `merge.read_tabular_long` helper + HU crosswalk).
- Statistik Austria ODS -> `StatFact` (`read_excel engine=odf` -> `read_tabular_long`).
- UIC PDF -> `StatFact` (pdfplumber/camelot table extraction; larger effort).
- GDELT history backfill via `past_recordings` to 100k+ articles, plus a GKG
  `.csv.zip` parser wiring the dormant `extract.gdelt_passthrough` stub — the
  highest-leverage move for real volume.

### Stale assumptions corrected

- UIC now lands **PDF**, not XLS (RAILISA bulk CSV/Excel/REST need a subscription).
- Statistik Austria lands **ODS**; its OGD JSON/CSV has no rail dataset.
- `merge.read_tabular_long` and `extract.gdelt_passthrough` are written-but-uncalled
  stubs, ready to wire. `StatFact.source_system` already enumerates ksh/uic/
  statistik_austria even though no parser feeds them yet.

## Original Task List 9-12 Status

| # | Task | Status | Notes |
|---|---|---|---|
| 9 | silver/stats-parsers | **2 / 5** (GAP-006) | Eurostat ✓, World Bank ✓; KSH XLSX ✗, Statistik Austria ODS ✗, UIC PDF ✗. |
| 10 | silver/news-parsers | **3 / 3** (GAP-006, PR #9) | RSS ✓, GDELT ArtList ✓, ArticleRecord->NewsFeature ✓ (LLM step tested with mocked Ollama; live LLM unproven). |
| 11 | gold/feature-matrix | **done on fixture** | Assemble `(geo, year)` ✓, write Parquet ✓, save row/col counts ✓ (4x3). Caveat: fed in-memory; `gold/run.py` storage-load is a stub (GAP-007). |
| 12 | spark/evidence-job | **0 / 3 — not started** (GAP-009) | No `spark_jobs/` package; reads Gold Parquet ✗, writes evidence ✗, records counts ✗. |

## Gap Register Summary

| Gap | Status | Topic |
|---|---|---|
| GAP-001..003 | closed | deps/install, single import root, Bronze package |
| GAP-004 | closed | fixture-backed Bronze reads (E2E) |
| GAP-005 | open | scheduler wiring for KSH/StatAustria/UIC/history |
| GAP-006 | open | local Silver persistence done; remaining stats parsers/news failure accounting |
| GAP-007 | open | Gold loads persisted Silver |
| GAP-008 | closed | deterministic test suite |
| GAP-009 | open | Spark/big-data job (the deliverable) |
| GAP-010 | in_progress | live Bronze/Silver/Gold evidence (live MinIO smoke now proven 2026-06-24) |
| GAP-011 | open | report + presentation |
| GAP-012..030 | open | **19 new gaps** found by the 2026-06-24 `undocumented-gap-hunt` (see `GAP_REGISTER.md`). Highest-impact: GAP-012 (the documented Bronze→Gold regen recipe silently builds an empty Gold), GAP-013 (live MinIO stats path drops World Bank), GAP-015 (units never normalized despite the contract), GAP-016 (non-deterministic Gold news schema), GAP-017 (`pyspark>=3.5` resolves to Spark 4.x), GAP-019 (in-memory-only "automatic updates" scheduler). |

## Roadmap To Completion

Named, trackable version of this roadmap (stable slugs, also used in the team
chat): `TASKS.md`.

Shortest line from here (Gold proven on a fixture) to Spark evidence and a
defensible report. Hard blockers sit on the main line; volume and coverage run
on a parallel track.

### Main line (critical path, ~2.5-4 days)

1. **Persist Silver outputs** — GAP-006 (min) is done for local Parquet
   snapshots. MinIO/s3fs persistence and news extraction-failure accounting
   remain follow-up work.
2. **Wire Gold <- persisted Silver** — GAP-007, ~1d (HARD). Wire
   `build_from_silver()` into `gold/run.py main()` to read the Silver Parquet,
   write the Gold matrix, and record row/column counts. Close with
   `python -m pytest -q -m integration`. Produces the first persisted-Silver
   Gold dataset; the bounded local stats-only non-fixture Gold smoke already
   exists from the pipeline path.
3. **Spark evidence job** — GAP-009, ~1-2d (THE TARGET). Create
   `src/railway_lakehouse/spark_jobs/coverage.py` + a SparkSession that reads the
   Gold Parquet and writes evidence to `output/evidence/spark/`, recording Spark
   version, input/output row counts, files/partitions written, and duration. Add
   an opt-in `spark` pytest marker + import/config test; document the command in
   `README.md` and `docs/VERIFICATION.md`. **=> Spark evidence exists.**
4. **Live end-to-end evidence** — GAP-010, parallel, 0.5-2d (service-dependent).
   Bounded live Bronze->Silver->Gold (needs MinIO + Ollama) producing
   `output/evidence/live/railway_ml.parquet`; re-run the Spark job against it.
   Not required to first demonstrate Spark.
5. **Report + presentation** — GAP-011. Create `output/report/` and
   `output/presentation/`; ground every claim in Step 3 Spark evidence + Step 2
   Gold counts (+ Step 4 live counts). Report-start unblocks once Step 3 + Step 2
   land.

### Parallel track — volume and coverage (lay anytime after Step 2)

- **Raise real volume (highest grade leverage).** The rail stats are only
  thousands of rows — too small to justify Spark honestly. Use the existing
  `past_recordings` backfiller to land a rail-filtered GDELT slice of 100k+
  articles, and add the missing GKG `.csv.zip` Silver parser. This is what makes
  a "depth and volume" rubric reward Spark.
- **Extra stats coverage (optional, multi-day).** KSH XLSX, Statistik Austria
  ODS, UIC PDF -> `StatFact`. Bytes already land live; only readers are missing.
- **Scheduler wiring (GAP-005).** Add ksh/statistik_austria/uic to
  `bronze/run.py` for the "automatic updates" requirement — pure orchestration.

## Big-Data Engine Decision

**Use Apache Spark (PySpark).** It is the rubric-aligned choice: the course names
MapReduce/Spark/Storm and grades on depth and volume of processing jobs. Spark is
the only named option that scales the same code from a laptop to a cluster. Run it
in **local mode now**, then start a standalone master + workers to **prove
horizontal scaling** (the differentiator vs single-node engines).

Write Gold/analysis tables as **Delta Lake** (Parquet + a `_delta_log/` — gives
ACID, time travel, schema evolution: real "lakehouse" talking points) while
keeping raw Bronze as plain Parquet.

Keep **DuckDB / Polars** as a fast EDA + benchmark sidecar (a "Spark vs DuckDB"
comparison is itself rubric points), never as the headline engine. Dask is off the
named-technologies list — use only as a comparison point.

### Pinned stack (avoid JAR/version hell)

**Updated 2026-06-24 (GAP-017 research):** use the **Spark 4.1 stack**, not 3.5 — the repo
runs on **Python 3.14**, and Spark 4.1 is the first release to support Python 3.14 (3.5/4.0
cannot run in this interpreter). Spark 4 is GA and a coherent 4.1 stack exists, so it does
not clash:

`Spark 4.1.x` · `Scala 2.13` · `delta-spark 4.1.x` (Delta 4.1.0+/4.3.0, built on Spark 4.1.0;
Maven `io.delta:delta-spark_4.1_2.13`) · `hadoop-aws 3.4.1` (must equal Spark 4.x's bundled
Hadoop; AWS SDK **v2** for s3a) · `JDK 17 or 21`. `pip install "pyspark==4.1.*" "delta-spark==4.1.*"`.
Spark 4 turns ANSI SQL on by default (net positive; use `try_cast`). Reading plain Parquet
needs no extra JARs; `hadoop-aws` is only for the `s3a://` MinIO path.

### Integration pattern

Drop Spark in as a parallel Gold/analytics engine, not a rewrite. Keep pandas
Bronze landing + Silver normalization; let Spark **read** the Parquet those layers
produce (and raw Bronze in MinIO via the `s3a` connector, reusing the
`S3_ENDPOINT`/`S3_KEY`/`S3_SECRET`/`BRONZE_BUCKET` env vars from `bronze/config.py`)
and **write** analysis outputs. For MinIO set
`spark.hadoop.fs.s3a.path.style.access=true` and
`spark.hadoop.fs.s3a.connection.ssl.enabled=false`. Reading plain Parquet needs no
extra JARs; the `hadoop-aws` JAR is only for the `s3a://` path. Note PySpark writes
a **directory** of part-files + `_SUCCESS`, not a single `.parquet` file.

### Windows setup notes

- Install **JDK 17 or 21**, set `JAVA_HOME` (Spark 4.x requires Java 17/21; Java 8/11 are
  dropped — the box currently has Java 8, so this is a required install).
- `winutils.exe` + `hadoop.dll` (matching Hadoop **3.4.x** for Spark 4.1, e.g. from cdarlint/winutils)
  are **required to write** to local `file://`; set `HADOOP_HOME` and add `bin` to
  PATH; copy `hadoop.dll` to `System32`.
- Set `PYSPARK_PYTHON`/`PYSPARK_DRIVER_PYTHON` to the same venv interpreter.
- First `SparkSession` build downloads JARs via Ivy from Maven Central (needs
  network; corporate proxies can block it).
- Alternative: run MinIO (and optionally Spark) via Docker, or develop under WSL2
  to sidestep winutils entirely. A clean defensible setup for the report: "native
  Windows + winutils for compute, Dockerized MinIO for object storage".

### Spark processing-job ideas (depth)

- Multi-source `(geo, year)` joins: rail stats (dimensions) x GDELT corpus (facts).
- YoY growth + 3-year moving averages via window functions (mind the lag-with-gaps
  pitfall: build the full geo x year grid before windowing).
- COVID shock/recovery detection (2020 ridership collapse vs 2023 recovery).
- Partitioned news aggregation at scale (read raw RSS/GDELT from MinIO via s3a).
- Explode + pivot operator/line mentions per country-year.
- News-volume x incident/investment correlation (`F.corr`).
- Port `gold/build.py` (resolve-conflicts -> pivot -> join) into Spark as a Delta
  table with time travel.
- Delta time-travel / schema-evolution demo + distributed data-quality checks.
- Then benchmark local-vs-cluster and plot the scaling curve; add a Spark vs
  DuckDB/Polars comparison.

## Research Sources

Full query log: `.planning/coursework/research/bigdata/state-analysis-spark-roadmap-2026-06-23.md`.
Key references:

- Hadoop S3A connector — https://hadoop.apache.org/docs/r3.4.1/hadoop-aws/tools/hadoop-aws/connecting.html
- Spark Parquet data source — https://spark.apache.org/docs/latest/sql-data-sources-parquet.html
- Delta releases/compatibility — https://docs.delta.io/releases
- hadoop-aws version coupling — https://stackoverflow.com/questions/77327653/hadoop-common-hadoop-aws-aws-java-sdk-bundle-version-compatibility
- Apache wiki WindowsProblems — https://cwiki.apache.org/confluence/display/HADOOP2/WindowsProblems
- cdarlint/winutils — https://github.com/cdarlint/winutils
- Spark standalone (scaling) — https://spark.apache.org/docs/latest/spark-standalone.html
- Coiled engine decision matrix — https://docs.coiled.io/blog/tpch.html
- Spark vs DuckDB/Polars (mix engines) — https://mwc360.github.io/data-engineering/2024/12/12/Should-You-Ditch-Spark-DuckDB-Polars.html
- GDELT scale — https://www.gdeltproject.org/data.html
- Teaching Big Data with limited resources (grading) — https://cidl.uitm.edu.my/uploads/CG-BDA/Teaching%20Big%20Data%20With%20Limited%20Resources%20Practical%20Lessons%20from%20a%20Scaled%20Down%20Lab.pdf


## Update 2026-06-23 — MinIO storage path

infra/minio-storage adds a local S3-compatible lakehouse store for the project.

Implemented:

- docker-compose.yml starts MinIO.
- .env.example documents S3/MinIO defaults.
- docker compose bootstraps bronze, silver, and gold buckets.
- scripts/minio_smoke.py verifies a bounded write/read/delete round-trip through s3fs.
- tests/test_infra_minio.py guards the committed infra without requiring Docker.
- smoke evidence is written to output/evidence/minio-smoke/manifest.json.

Verified result:

- status: passed
- endpoint: http://localhost:9000
- buckets: bronze, silver, gold
- roundtrip_ok: true
- bytes_written: 32
- bytes_read: 32

This proves the local object-storage path needed for GAP-010. Full persisted
Bronze->Silver->Gold through MinIO still depends on silver/persist-outputs and
gold/load-from-silver.

## Update 2026-06-23 — live re-audit (tests + inventory)

Re-verified after the `silver/persist-outputs`, `bronze/local-stats-landing`/`gold/first-real-result`,
and `infra/minio-storage` merges. Two background research/audit workflows
(`railway-state-audit`, 21 agents; `undocumented-gap-hunt`) plus direct runs; all 8
load-bearing claims independently confirmed. Full log:
`.planning/coursework/research/bigdata/state-reaudit-tests-inventory-2026-06-23.md`.

Verified this session (real, on disk):

- Tests: `python -m pytest -q` → **87 passed** (77 unit + 10 integration); `-m live`/`-m spark`
  select 0; `compileall` clean. Env: Python 3.14.0 / pandas 3.0.3 / pyarrow 24.0.0.
- **Live MinIO proven** (not just reachable): `docker compose up -d` → `railway-minio` up;
  compose `createbuckets` created `bronze`/`silver`/`gold`; `scripts/minio_smoke.py` passed a
  32 B s3fs round-trip on the **bronze** bucket (`roundtrip_ok=true`).
- **Live World Bank Bronze→Silver→Gold**: `inventory-live-2026-06-23/railway_ml.parquet` =
  **2,968 rows × 4 cols** `[geo, year, rail_freight_tonne_km, rail_network_length_km]`, 151 geos,
  1995–2021, AT/HU 27 rows each (AT 1995 freight=13715, network=5672). Crosswalk 2/2 mapped;
  merge kept 35112/35112. Supersedes the prior 2,139×3 single-feature smoke.
- Silver `StatFact` (35,112 rows) persisted via `silver/persist.py` and reloaded identically;
  the parquet was also uploaded to the MinIO `silver` bucket as a manual demonstration.

Corrections to earlier wording in this doc:

- The real Gold is now **two** World Bank features (freight tonne-km + network route-km), not one;
  proven on **2,968 real rows**, not just the 4-row fixture.
- **Eurostat reaches Silver but not Gold** for a structural reason, not just "unmapped labels":
  `merge.read_eurostat_tsv` uses the **SDMX dimension-key header** (e.g. `freq,unit,geo\TIME_PERIOD`)
  as `source_column`, which matches no crosswalk rule, so every Eurostat row is dropped before
  Gold. The only Eurostat fixture uses a hand-crafted human-readable header, so the green
  fixture/integration tests **overstate** Eurostat's real reach. (Tracked as a new gap — see
  GAP_REGISTER.)
- World Bank reaches Gold via the **in-memory** Silver path; the pipeline still never calls
  `persist.py` before Gold (GAP-007). The persist→reload→Gold contract is green only in an
  isolated test, not in the production pipeline.
- `infra/ollama-model` is unstarted: Ollama is not installed, so the (fully coded) `NewsFeature`
  LLM extractor has never executed against a live model — it is exercised only via mocked
  `generate_json` in tests.
- pyspark is a declared-but-uninstalled extra; only Java 8 is present (Spark 3.5 supports 8/11/17,
  17 recommended) — GAP-009 entirely unstarted.
