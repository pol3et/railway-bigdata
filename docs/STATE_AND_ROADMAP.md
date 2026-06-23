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
| Silver (normalize) | partial | World Bank + Eurostat stats and RSS + GDELT news normalize correctly, but **in-memory only** inside `pipeline.py`. No persisted Silver writer; `silver/run.py` is a stub (GAP-006). |
| Gold (feature matrix) | partial | The `(geo, year)` feature-matrix builder works and writes Parquet. Fixture evidence exists, and a first real stats-only Gold was produced from local Eurostat + World Bank Bronze evidence: `output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet` with 2,139 rows x 3 columns. `gold/run.py` still cannot load persisted Silver from storage yet (GAP-007). |
| Spark (big-data jobs) | not built | No `spark_jobs/` package exists. The registered command `python -m railway_lakehouse.spark_jobs.coverage` cannot import (GAP-009). This is the graded deliverable. |
| Report / presentation | not started | Blocked: every claim must cite generated evidence that does not exist yet (GAP-011). |

### At A Glance

- `python -m pytest -q`: **77 passed**, 0 xfail.
- Bronze sources built: **8**; scheduled: **4**; live-proven (raw bytes): **4**
  (RSS, KSH, UIC, World Bank) + Statistik Austria probed.
- Stats parsers to `StatFact`: **2 / 5**. News parser stages to `NewsFeature`: **3 / 3**.
- Gaps closed: **5 / 11** (GAP-001..004, 008).
- End-to-end Bronze->Silver->Gold artifacts:
  - fixture: `output/evidence/fixture-e2e/railway_ml.parquet` = **4 rows x 3 cols**, news skipped.
  - first real stats-only run: `output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet` = **2,139 rows x 3 cols**, includes `AT` and `HU`, news skipped.

### Evidence Reality Check

Live runs proved **raw Bronze landing only**, not Silver/Gold:

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

There is no live Silver/Gold output and no Spark output.

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
| GAP-006 | open | Silver persistence + remaining stats parsers |
| GAP-007 | open | Gold loads persisted Silver |
| GAP-008 | closed | deterministic test suite |
| GAP-009 | open | Spark/big-data job (the deliverable) |
| GAP-010 | in_progress | live Bronze/Silver/Gold evidence |
| GAP-011 | open | report + presentation |

## Roadmap To Completion

Named, trackable version of this roadmap (stable slugs, also used in the team
chat): `TASKS.md`.

Shortest line from here (Gold proven on a fixture) to Spark evidence and a
defensible report. Hard blockers sit on the main line; volume and coverage run
on a parallel track.

### Main line (critical path, ~2.5-4 days)

1. **Persist Silver outputs** — GAP-006 (min), ~0.5-1d. Decide the canonical
   persisted Silver stats and news Parquet paths and write them. Gold needs a
   documented input to load from.
2. **Wire Gold <- persisted Silver** — GAP-007, ~1d (HARD). Wire
   `build_from_silver()` into `gold/run.py main()` to read the Silver Parquet,
   write the Gold matrix, and record row/column counts. Close with
   `python -m pytest -q -m integration`. Produces the first real (non-fixture)
   Gold dataset.
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

`Spark 3.5.x` · `Scala 2.12` · `delta-spark 3.2.x` · `hadoop-aws 3.3.4` (must equal
Spark's bundled Hadoop) · `JDK 17`. `pip install pyspark==3.5.* delta-spark==3.2.1`.

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

- Install JDK 17, set `JAVA_HOME` (Spark 3.5 is validated on Java 8/11/17, not 21+).
- `winutils.exe` + `hadoop.dll` (matching Hadoop 3.3.x, e.g. from cdarlint/winutils)
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
