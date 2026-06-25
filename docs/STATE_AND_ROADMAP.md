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

Phase: end of the fast-track report kickoff. The pipeline reads
`web sources -> Bronze -> Silver -> Gold -> Spark -> report`. Today the train
has a drafted report/presentation grounded in committed Gold, MinIO, and Spark
evidence.

| Stage | Signal | State |
|---|---|---|
| Bronze (ingest) | operational | Raw landing works. 4 sources scheduled (Eurostat, World Bank, GDELT, RSS); KSH, Statistik Austria, UIC, GDELT-history are live-proven but **not scheduled** (GAP-005). |
| Silver (normalize) | partial | World Bank + Eurostat stats and RSS + GDELT news normalize correctly inside fixture/local pipeline paths. Local Parquet persistence now exists for `StatFact` and successful `NewsFeature` rows; MinIO/s3fs persistence, extraction-failure accounting, and `silver/run.py` remain open. |
| Gold (feature matrix) | partial | The `(geo, year)` feature-matrix builder works and writes Parquet. Fixture evidence exists, and a first real stats-only Gold was produced from bounded local Eurostat + World Bank Bronze landing: `output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet` with 2,139 rows x 3 columns. The current richer real Gold is World Bank-backed at `output/evidence/inventory-live-2026-06-23/railway_ml.parquet` with 2,968 rows x 4 columns. `gold/run.py` now loads persisted local Silver Parquet and records counts (GAP-007 closed); full live MinIO/Ollama E2E remains open. |
| Spark (big-data jobs) | local evidence written | `railway_lakehouse.spark_jobs.coverage` reads the real Gold Parquet and writes `output/evidence/spark/manifest.json` plus a Spark Parquet output directory (GAP-009 closed). |
| Report / presentation | draft evidence-linked | `output/report/REPORT.md` and `output/presentation/PRESENTATION.md` exist and cite committed evidence artifacts; `tests/test_report_evidence_links.py` guards cited paths and headline JSON values (GAP-011 closed). |

### At A Glance

- `python -m pytest -q`: **108 passed**, 1 skipped when run with the
  existing JDK 21 Spark runtime env; the skip is the Windows Spark write-path
  guard because `HADOOP_HOME`/`winutils.exe` is absent in this worktree.
- Bronze sources built: **8**; scheduled: **4**; live-proven (raw bytes): **4**
  (RSS, KSH, UIC, World Bank) + Statistik Austria probed.
- Stats parsers to `StatFact`: **3 / 5**. News parser stages to `NewsFeature`: **3 / 3**.
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

There is no full MinIO/Ollama/news Silver/Gold output. Local Spark evidence now exists under `output/evidence/spark/`.

## Data Inventory

What each source fetches, and whether it reaches structured Silver rows today.

| Source | Format | Geo · Topic | Bronze (collection) | Silver (-> rows) |
|---|---|---|---|---|
| `eurostat` | TSV/.gz (SDMX) | EU incl. HU/AT · rail passengers, freight, network, electrification, safety | scheduled · live-capable | StatFact · tested |
| `worldbank` | JSON | global (HU/AT picked in Silver) · route-km, tonne-km, passenger-km, since 1960 | scheduled · live-proven | StatFact · tested |
| `rss_media` | XML | HU/AT media + MAV/OEBB press · all-topic, rail-filtered in Silver | scheduled · live-proven | ArticleRecord · tested |
| `gdelt` | JSON (DOC 2.0) | HU + AT · rail news | scheduled · **live FAILS (429)** | ArticleRecord · tested (fixture) |
| `ksh` | XLSX | HU only · freight, passengers, rolling stock, network, regional + narrow-gauge lines | live-proven · **not scheduled** | StatFact reader · tested |
| `statistik_austria` | ODS | AT only · freight, rolling-stock fleet (passengers/network are login-only -> use Eurostat) | live-proven · **not scheduled** | **MISSING — no ODS reader** |
| `uic` | PDF | global UIC members · passenger-km, tonne-km, network, rolling stock, employees | live-proven · **not scheduled** | StatFact reader · tested |
| `past_recordings` | JSON · GKG csv.zip | HU + AT · deep news backfill (DOC ~10y; GKG v1 1979-2016) — the real volume play | CLI one-off · not scheduled | DOC pages OK · **GKG csv MISSING** |

### Extracted (proven) today

- World Bank rail series -> `StatFact` (verbatim values, ISO3->geo map).
- Eurostat rail series (TSV incl. gzip) -> `StatFact` (flag-stripped, labels mapped).
- RSS XML and GDELT ArtList JSON -> `ArticleRecord` (stable IDs).
- `ArticleRecord` -> validated `NewsFeature` (deterministic Lingua language ID first; Ollama only for semantic fields; tested with mocked LLM output).
- A unified `(geo, year)` Gold matrix from Bronze fixtures (proven on 4 rows).

### Extractable next (bytes already land; only parsers missing)

- Statistik Austria ODS -> `StatFact` (`read_excel engine=odf` -> `read_tabular_long`).
- UIC PDF -> `StatFact` (public Synopsis table via `pdfplumber`; Traffic Trends has no country-level synopsis table).
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
| 9 | silver/stats-parsers | **4 / 5** (GAP-006) | Eurostat ✓, World Bank ✓, KSH XLSX ✓, UIC PDF ✓; Statistik Austria ODS ✗. |
| 10 | silver/news-parsers | **3 / 3** (GAP-006, PR #9) | RSS ✓, GDELT ArtList ✓, ArticleRecord->NewsFeature ✓ (LLM step tested with mocked Ollama; live LLM unproven). |
| 11 | gold/feature-matrix | **done on fixture + persisted Silver CLI** | Assemble `(geo, year)` ✓, write Parquet ✓, save row/col counts ✓ (4x3). `gold/run.py` now loads persisted local Silver Parquet and writes counts (GAP-007 closed). |
| 12 | spark/evidence-job | **3 / 3 — local evidence written** (GAP-009) | `spark_jobs.coverage` reads the real Gold Parquet, writes `output/evidence/spark/coverage_by_geo_year/`, and records Spark version, counts, files, duration, and timestamps in `manifest.json`. |

## Gap Register Summary

| Gap | Status | Topic |
|---|---|---|
| GAP-001..003 | closed | deps/install, single import root, Bronze package |
| GAP-004 | closed | fixture-backed Bronze reads (E2E) |
| GAP-005 | open | scheduler wiring for KSH/StatAustria/UIC/history |
| GAP-006 | open | local Silver persistence done; remaining stats parsers/news failure accounting |
| GAP-007 | closed | Gold loads persisted Silver through `gold.run` |
| GAP-008 | closed | deterministic test suite |
| GAP-009 | closed | Spark/big-data evidence job (the deliverable) |
| GAP-010 | in_progress | live Bronze/Silver/Gold evidence (live MinIO smoke now proven 2026-06-24) |
| GAP-011 | open | report + presentation |
| GAP-012..030 | open | **19 new gaps** found by the 2026-06-24 `undocumented-gap-hunt` (see `GAP_REGISTER.md`). Highest-impact: GAP-012 (the documented Bronze→Gold regen recipe silently builds an empty Gold), GAP-013 (live MinIO stats path drops World Bank), GAP-015 (units never normalized despite the contract), GAP-016 (non-deterministic Gold news schema), GAP-017 (`pyspark>=3.5` resolves to Spark 4.x), GAP-019 (in-memory-only "automatic updates" scheduler). |
| GAP-017 | done | Spark stack decision implemented: `[spark]` now pins PySpark 4.1.x and Delta 4.1.x only; S3A is recorded as Spark Maven packages `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6`, with JDK 17/21 + `JAVA_HOME`; static guard: `pytest -q tests/test_spark_stack_pins.py`. |

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
2. **Wire Gold <- persisted Silver** — GAP-007 is closed. `gold/run.py main()`
   reads the Silver Parquet with `persist.load_stats/load_news`, writes the Gold
   matrix, and records row/column counts. Verification: `python -m pytest -q -m
   integration` -> 14 passed; local CLI smoke wrote a 4x4 persisted-Silver Gold
   matrix with AT/HU and `rail_passenger_km`.
3. **Spark evidence job** — GAP-009 is closed. `src/railway_lakehouse/spark_jobs/coverage.py`
   reads the real Gold Parquet and writes evidence to `output/evidence/spark/`,
   recording Spark version, input/output row counts, files/partitions written,
   and duration. The command is documented in `README.md` and
   `docs/VERIFICATION.md`. **=> Spark evidence exists.**
4. **Live end-to-end evidence** — GAP-010, parallel, 0.5-2d (service-dependent).
   Bounded live Bronze->Silver->Gold (needs MinIO + Ollama) producing
   `output/evidence/live/railway_ml.parquet`; re-run the Spark job against it.
   Not required to first demonstrate Spark.
5. **Report + presentation** — GAP-011 is closed for the fast-track draft.
   `output/report/REPORT.md` and `output/presentation/PRESENTATION.md` ground
   claims in Step 3 Spark evidence + Step 2 Gold counts, with a deterministic
   evidence-link checker.

### Parallel track — volume and coverage (lay anytime after Step 2)

- **Raise real volume (highest grade leverage).** The rail stats are only
  thousands of rows — too small to justify Spark honestly. Use the existing
  `past_recordings` backfiller to land a rail-filtered GDELT slice of 100k+
  articles, and add the missing GKG `.csv.zip` Silver parser. This is what makes
  a "depth and volume" rubric reward Spark.
- **Extra stats coverage (optional, multi-day).** KSH XLSX and UIC PDF now feed
  `StatFact`; Statistik Austria ODS is the remaining extra stats reader.
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

**Updated 2026-06-24 (GAP-017):** use the **Spark 4.1 stack**, not the old Stack-A
Spark line. Stack A is not installable on this repo's **Python 3.14 / pandas 3.0 /
pyarrow 24** runtime without downgrading the already-green pipeline. Spark 4.1 adds Python
3.14 support and a coherent 4.1 stack exists, so the project deliberately adopts this path
under GAP-017's Spark-4 branch:

`Spark 4.1.x` · `Scala 2.13` · `delta-spark 4.1.x` (Python package; Delta 4.1.0+/4.3.0
targets Spark 4.1; Maven `io.delta:delta-spark_4.1_2.13:4.1.0` when a SparkSession needs
Delta JARs) · `JDK 17 or 21`. `pip install -e ".[spark]"` resolves PySpark 4.1.x and
`delta-spark` 4.1.x only. For the `s3a://` MinIO path, set `spark.jars.packages` from
`railway_lakehouse.spark_config.SPARK_S3A_PACKAGES`:
`org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6`. The
`hadoop-aws` Maven version must equal Spark 4.x's bundled Hadoop 3.4.1 generation.
Spark 4 turns ANSI SQL on by default (net positive; use `try_cast`). Reading plain Parquet
needs no extra JARs; the S3A Maven packages are only for the `s3a://` MinIO path.

### Integration pattern

Drop Spark in as a parallel Gold/analytics engine, not a rewrite. Keep pandas
Bronze landing + Silver normalization; let Spark **read** the Parquet those layers
produce (and raw Bronze in MinIO via the `s3a` connector, reusing the
`S3_ENDPOINT`/`S3_KEY`/`S3_SECRET`/`BRONZE_BUCKET` env vars from `bronze/config.py`)
and **write** analysis outputs. For MinIO set
`spark.hadoop.fs.s3a.path.style.access=true` and
`spark.hadoop.fs.s3a.connection.ssl.enabled=false`. Reading plain Parquet needs no
extra JARs; the S3A Maven packages are only for the `s3a://` path. Note PySpark writes
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

## Update 2026-06-24 — GAP-018 reproducibility guard

- Dependency bounds: `requires-python` is now `>=3.12,<3.15`; pandas is `>=2.2,<4`;
  pyarrow is `>=15,<25`; requests and schedule also have next-major caps. The exact S3
  pins stayed unchanged, and the `[spark]` extra remains GAP-017 scope.
- `constraints.txt` at the repo root pins the graded Python 3.14 runtime/test closure,
  including pandas 3.0.3, pyarrow 24.0.0, s3fs/fsspec 2024.6.1, aiobotocore 2.13.1,
  botocore 1.34.131, requests 2.33.1, schedule 1.2.2, and pytest 9.0.3.
- Verification: `python -m pytest -q tests/test_env_versions.py` -> 5 passed;
  `python -m pytest -q` -> 92 passed; `python -m compileall -q src tests` exited 0;
  `python -m pip install --dry-run -e ".[test]" -c constraints.txt` kept pandas 3.0.3
  and pyarrow 24.0.0.

Corrections to earlier wording in this doc:

- The real Gold is now **two** World Bank features (freight tonne-km + network route-km), not one;
  proven on **2,968 real rows**, not just the 4-row fixture.
- **Eurostat reaches Silver but not Gold** for a structural reason, not just "unmapped labels":
  `merge.read_eurostat_tsv` uses the **SDMX dimension-key header** (e.g. `freq,unit,geo\TIME_PERIOD`)
  as `source_column`, which matches no crosswalk rule, so every Eurostat row is dropped before
  Gold. The only Eurostat fixture uses a hand-crafted human-readable header, so the green
  fixture/integration tests **overstate** Eurostat's real reach. (Tracked as a new gap — see
  GAP_REGISTER.)
- GAP-007 now closes the local persisted-Silver -> Gold CLI boundary: `gold.run`
  reads `persist.py` outputs directly and writes counts. The older pipeline entrypoint still builds
  Gold from in-memory Silver; full MinIO/Ollama/news E2E remains GAP-010/GAP-013 follow-up.
- `infra/ollama-model` is unstarted: Ollama is not installed, so the (fully coded) `NewsFeature`
  LLM extractor has never executed against a live model — it is exercised only via mocked
  `generate_json` in tests.
- `[spark]` is pinned to the Spark 4.1 stack. GAP-009 provisioned JDK 21 for the
  local Spark evidence run; native Windows local writes also needed
  `HADOOP_HOME` with Hadoop 3.4.x `winutils.exe` and `hadoop.dll`.


## Update 2026-06-24 — KSH XLSX stats reader

`silver/stats-ksh-xlsx-reader` adds deterministic parsing for Hungarian KSH XLSX files, including the live STADAT year-first, regional-total, and sectioned single-year workbook shapes.

Implemented:
- `openpyxl` dependency for XLSX support.
- KSH XLSX reader in `silver/stats/load.py`.
- `ksh` source registration for Bronze `stats/ksh/.../*.xlsx` partitions.
- Unit coverage in `tests/test_silver_stats_ksh.py`.
- Live KSH Bronze parsing evidence from six current XLSX artifacts in `output/evidence/pr24-ksh-live-check-after-fix/manifest.json`.

Verified:
- KSH reader tests: 9 passed.
- KSH plus dependency guard tests: 14 passed.
- Integration marker suite: 16 passed.
- Full test suite: 136 passed, 1 skipped.

Boundary:
- KSH XLSX can now flow from Bronze raw files into the Silver StatFact contract.
- Statistik Austria ODS remains pending; UIC PDF is covered by the follow-up update below.

## Update 2026-06-24 — UIC PDF stats reader

`silver/stats-uic-pdf-reader` adds deterministic parsing for UIC public PDF tables.

Implemented:
- `pdfplumber` dependency for PDF table extraction.
- UIC PDF table reader in `silver/stats/load.py`.
- `uic` source registration for Bronze `stats/uic/.../*.pdf` partitions.
- Rule-based crosswalk coverage for UIC original English column labels.
- Unit coverage in `tests/test_silver_stats_uic_pdf.py`.
- Real UIC PDF parse evidence in `output/evidence/pr26-uic-pdf-silver-probe/manifest.json`.

Verified:
- UIC reader tests: 6 passed.
- Current UIC Synopsis PDF parsed to 39 unified Silver rows across AT/HU and 9 mapped features.
- Current UIC Traffic Trends PDF produced 0 rows because it has no country-level synopsis table.

Boundary:
- UIC public Synopsis PDF can now flow from Bronze raw files into the Silver StatFact contract.
- This does not claim OCR, subscribed RAILISA CSV/Excel/API access, or a Gold rerun including UIC.
- Statistik Austria ODS remains the pending extra stats parser.
