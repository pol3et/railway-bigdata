# GAP-009 Spark Evidence Job Research

Date: 2026-06-24

Workflow: `research-orchestrator` was invoked before planning or edits. Local files were researched first, then Spark API details were routed through Context7. Ref was attempted for exact API references but returned a quota error, so Context7's Spark 4.1.1 documentation was used as the routed provider.

## Local Research

- `pyproject.toml` already contains the GAP-017 Spark extra pins:
  - `pyspark==4.1.*`
  - `delta-spark==4.1.*`
- `src/railway_lakehouse/spark_config.py` records the S3A Maven packages for later `spark.jars.packages` use:
  - `org.apache.hadoop:hadoop-aws:3.4.1`
  - `software.amazon.awssdk:bundle:2.24.6`
- `docs/STATE_AND_ROADMAP.md:191-205` confirms the Spark 4.1 / Delta 4.1 / JDK 17-or-21 stack and states that reading plain local Parquet needs no extra JARs.
- `docs/STATE_AND_ROADMAP.md:216-225` confirms PySpark writes a directory of part-files plus `_SUCCESS` and records native Windows `winutils.exe` / `hadoop.dll` requirements.
- `docs/TASKS.md:138-145` marks GAP-009 as Wave 2 / Contract B: Spark reads real Gold and writes evidence with Spark version, counts, and files written.
- At intake, `docs/GAP_REGISTER.md:25` pointed at `output/evidence/live/railway_ml.parquet`, which does not exist in this checkout.
- The real richest Gold input exists at `output/evidence/inventory-live-2026-06-23/railway_ml.parquet`; existing docs record it as 2,968 rows x 4 columns.

## External / Routed Research

Provider: Context7

Queries:

1. `Apache Spark` library resolution for PySpark SparkSession, Parquet read/write, counts, groupBy, and `spark.version`.
2. `/websites/spark_apache_4_1_1`: "PySpark SparkSession.builder.appName master getOrCreate, SparkSession.version, DataFrameReader.parquet, DataFrame.count columns, groupBy count agg, DataFrameWriter.mode overwrite parquet directory semantics"
3. `/websites/spark_apache_4_1_1`: "PySpark SparkSession.version property DataFrame columns count groupBy count aggregate examples"

Relevant source URLs surfaced by Context7:

- https://spark.apache.org/docs/4.1.1/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrameReader.parquet.html
- https://spark.apache.org/docs/4.1.1/api/python/reference/pyspark.sql/api/pyspark.sql.functions.count.html
- https://spark.apache.org/docs/4.1.1/sql-getting-started.html
- https://spark.apache.org/docs/4.1.1/api/java/org/apache/spark/sql/SparkSession.html
- https://spark.apache.org/docs/latest/sql-data-sources-parquet.html

Provider: Ref

- Query: `PySpark 4.1 SparkSession.builder appName master getOrCreate SparkSession.version DataFrameReader.parquet DataFrameWriter.parquet`
- Result: Ref returned "Not enough credits"; no Ref source content was available.

Provider: Firecrawl

- Query: `kontext-tech winutils hadoop-3.4.0-win10-x64 bin winutils.exe hadoop.dll GitHub`
- Result: found the Windows Hadoop helper source used for native local writes:
  - https://github.com/cdarlint/winutils
  - https://kontext.tech/project/tools/article/hadoop-3-4-0-winutils-for-windows-10-x64
  - https://github.com/kontext-tech/winutils/tree/master/hadoop-3.4.0-win10-x64/bin

## Implementation Conclusions

- Use `SparkSession.builder.appName("railway-coverage").master(master).getOrCreate()` for the local evidence job.
- Read the Gold Parquet via `spark.read.parquet(...)`.
- Capture input rows with `df.count()` and columns with `df.columns`.
- Perform deterministic Spark work with `groupBy("geo", "year").agg(...)`, using `pyspark.sql.functions.count` to record per-feature non-null coverage.
- Write the coverage DataFrame with `out_df.write.mode("overwrite").parquet(...)`; treat the destination as a directory and scan it for part-files plus `_SUCCESS`.
- Do not configure S3A or Hadoop AWS packages in this job; the local Parquet path needs no extra JARs and MinIO/S3A belongs to a later gap.
- On native Windows, Spark local writes need `HADOOP_HOME/bin` to provide `winutils.exe` and `hadoop.dll`; this is an execution environment prerequisite, not project code.
