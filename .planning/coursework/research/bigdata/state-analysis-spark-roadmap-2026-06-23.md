# Research: Current State, Data Inventory, and Spark/Big-Data Roadmap

Date: 2026-06-23
Skill: `research-orchestrator` (mandatory for `bigdata/` tasks).
Task type: read-only state analysis + roadmap (no source code changed).

## Method

Orchestrated via the `Workflow` tool: 4 read-only mapping agents over the repo
(grounded in source files + committed evidence, not doc prose) running in
parallel with 2 external-research agents. Local files were read first; external
claims were routed through `research-orchestrator` MCP providers.

## Routed MCP providers used

- **Context7** — Spark / Delta Lake / Iceberg / PySpark API + config facts.
- **Ref** — exact config keys / API signatures (attempted; some pages credit-limited).
- **Tavily** — setup guides, Windows winutils pitfalls, engine comparisons.
- **Exa** — example Spark+GDELT / Spark+Delta+MinIO course repos.

## Queries (representative)

- "PySpark read parquet from MinIO s3a connector hadoop-aws config path style access"
- "Delta Lake vs Iceberg vs plain Parquet single node lakehouse course project"
- "PySpark Windows winutils.exe hadoop.dll local setup Java 17 pyspark 3.5"
- "Spark vs DuckDB vs Polars vs Dask single node when to use depth volume"
- "GDELT GKG backfill volume masterfilelist 100k rows Spark course project"
- "Spark window functions lag YoY growth missing years pitfall"
- "demonstrate big data depth volume scaled down lab grading criteria"

## Key source URLs

- Hadoop S3A connecting docs — https://hadoop.apache.org/docs/r3.4.1/hadoop-aws/tools/hadoop-aws/connecting.html
- Spark Parquet data source — https://spark.apache.org/docs/latest/sql-data-sources-parquet.html
- Delta release/compatibility matrix — https://docs.delta.io/releases
- Delta 3.2 on Spark 3.5 — https://delta.io/blog/delta-lake-3-2
- hadoop-aws ↔ Hadoop version coupling — https://stackoverflow.com/questions/77327653/hadoop-common-hadoop-aws-aws-java-sdk-bundle-version-compatibility
- Iceberg multi-engine runtime jars — https://iceberg.apache.org/multi-engine-support
- Apache wiki WindowsProblems (winutils/hadoop.dll) — https://cwiki.apache.org/confluence/display/HADOOP2/WindowsProblems
- cdarlint/winutils binaries — https://github.com/cdarlint/winutils
- PySpark install (PyPI) — https://spark.apache.org/docs/latest/api/python/getting_started/install.html
- Spark standalone (local→cluster scaling) — https://spark.apache.org/docs/latest/spark-standalone.html
- Coiled TPC-H engine decision matrix — https://docs.coiled.io/blog/tpch.html
- Spark vs DuckDB/Polars (mix engines) — https://mwc360.github.io/data-engineering/2024/12/12/Should-You-Ditch-Spark-DuckDB-Polars.html
- Polars comparison (single-node vs Spark overhead) — https://docs.pola.rs/user-guide/misc/comparison
- Databricks single-node Spark benchmark — https://www.databricks.com/blog/2018/05/03/benchmarking-apache-spark-on-a-single-node-machine.html
- GDELT scale / datasets — https://www.gdeltproject.org/data.html , https://blog.gdeltproject.org/the-datasets-of-gdelt-as-of-february-2016
- gdelttools backfill loader — https://github.com/jdrumgoole/gdelttools/blob/master/README.md
- Student Spark+GDELT (~55M rows on laptop) — https://github.com/Senyeah/data301-project
- "Teaching Big Data With Limited Resources" (grading criteria) — https://cidl.uitm.edu.my/uploads/CG-BDA/Teaching%20Big%20Data%20With%20Limited%20Resources%20Practical%20Lessons%20from%20a%20Scaled%20Down%20Lab.pdf

## Findings (grounded)

State: end of storage-boundary phase / start of Spark phase. Bronze landing
operational (4 scheduled, 4 more live-proven raw bytes only); Silver normalizes
World Bank + Eurostat stats and RSS + GDELT news **in-memory only** (no persisted
Silver writer); Gold feature-matrix builder works and writes Parquet but only
from a 4-row fixture. The single end-to-end artifact is
`output/evidence/fixture-e2e/railway_ml.parquet` (4 rows × 3 cols, news skipped).

Task list 9–12:
- 9 silver/stats-parsers: **2/5** — Eurostat ✓, World Bank ✓; KSH XLSX / Statistik
  Austria ODS / UIC PDF readers MISSING. (List was stale: StatAustria is ODS not
  JSON/CSV; UIC is PDF not XLS.)
- 10 silver/news-parsers: **3/3** — RSS ✓, GDELT ArtList ✓, ArticleRecord→NewsFeature
  coded + tested with mocked Ollama (live LLM unproven).
- 11 gold/feature-matrix: **done on fixture** — assemble + write Parquet + save
  counts all proven; caveat: fed in-memory, `gold/run.py` storage-load is a stub
  (GAP-007).
- 12 spark/evidence-job: **0/3 — not started** (GAP-009). No `spark_jobs/` package.

Critical path: GAP-006(min Silver persist) → GAP-007(Gold←Silver) → **GAP-009(Spark
evidence)** → GAP-011(report). GAP-010(live) and the GDELT-volume backfill run in
parallel. Engine recommendation: **Apache Spark/PySpark** (rubric-aligned), Delta
Lake on Parquet, pinned stack Spark 3.5.x/Scala 2.12/delta-spark 3.2.x/hadoop-aws
3.3.4/JDK 17 + winutils on Windows; DuckDB/Polars as EDA+benchmark sidecar; raise
real volume via GDELT backfill so Spark is justified, not apologized for.

Deliverable: visual status+roadmap dashboard (Artifact) plus this log.
