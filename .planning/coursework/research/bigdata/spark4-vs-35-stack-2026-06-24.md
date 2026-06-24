# Spark 4 vs 3.5 stack decision (GAP-017) — 2026-06-24

Skill: `research-orchestrator`. Routed MCP providers: **Context7** (Apache Spark / PySpark / Delta
docs), **Tavily** (release status, Delta↔Spark compat, recency), **Ref** (exact version requirements).
Run as the Research phase of the `gap-task-specs` workflow plus a confirming Tavily search on
Delta↔Spark-4.1.

Question (from the user): "I think Spark 4 is fine unless it clashes with other stack or we have a
particular reason for pin — research the compat and best stack." Decide the coherent stack for this
repo (MinIO via s3a, Delta Lake, Windows + JDK, Gold Parquet now, volume later) given it runs on
**Python 3.14 / pandas 3.0.3 / pyarrow 24.0.0**.

## Decision

**Adopt the Spark 4.1 stack — Spark 4 does not clash.** The deciding constraint is Python:
the repo is on **Python 3.14**, and **Spark 4.1 is the first PySpark release to support Python 3.14**,
so Spark 3.5 and even 4.0 cannot run in the current interpreter without a second Python. Spark 4.0/4.1
are GA/production-ready and a fully coherent 4.1 stack exists.

Pin this coherent set:

- `pyspark==4.1.*` (resolves 4.1.2) — Java 17/21, Scala 2.13, Python 3.10+ (incl. 3.14).
- `delta-spark==4.1.*` — Delta 4.1.0+ (latest 4.3.0) is built on Spark 4.1.0; Maven `io.delta:delta-spark_4.1_2.13`.
- S3A Maven packages for `spark.jars.packages`: `org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6`.
  The Hadoop connector must equal Spark 4.x's bundled hadoop-client generation; s3a uses **AWS SDK v2** now.
- **JDK 17 or 21** (the box currently has Java 8 → required install). `winutils`/`hadoop.dll` must match Hadoop **3.4.x** on Windows, or use WSL2 / Dockerized Spark.

Caveat: Spark 4 turns **ANSI SQL on by default** — invalid casts/overflows raise instead of
returning NULL (a net data-integrity win; use `try_cast()`, or `spark.sql.ansi.enabled=false` as a
last resort). Window-function + Parquet DataFrame APIs are unchanged 3.5→4.x, so migration risk is ~0.
Reading plain Parquet needs no extra JARs; the S3A packages are only for the `s3a://` MinIO path — so the
first Spark job (read Gold Parquet → coverage evidence) needs neither Delta nor s3a.

## Findings (with sources)

- **Spark 4.1 is the first release to support Python 3.14** — the load-bearing fact for this repo.
  https://spark.apache.org/releases/spark-release-4.1.0.html
- Spark 4.0.0 GA 2025-05-23 (managed on EMR/Databricks/Synapse); 4.1.0 GA 2025-12-11; 4.1.2 current
  (mid-2026); Spark 4.0 community EOS ~2026-11-23, so a new build should target 4.1.x.
  https://spark.apache.org/releases/spark-release-4-0-0.html · https://eosl.date/eol/product/apache-spark
- Spark 4.x requires Java 17/21, Scala 2.13, Python 3.10+. https://spark.apache.org/docs/4.1.1/index.html
- Spark 3.5.x supports Java 8/11/17, Scala 2.12/2.13, Python 3.8+ (the only line still on Java 8/11) —
  but does not support Python 3.14. https://spark.apache.org/docs/3.5.6
- Spark 4 turns ANSI SQL on by default. https://www.decube.io/post/apache-spark-4-release
- PySpark 4.0 dependency floors: pandas>=2.0, numpy>=1.21, pyarrow>=11 (our pandas 3.0 / pyarrow 24 satisfy).
  https://spark.apache.org/docs/4.1.1/api/python/_sources/migration_guide/pyspark_upgrade.rst.txt
- Delta↔Spark compatibility table: Delta 4.0.x↔Spark 4.0.x; Delta 3.0-3.3↔Spark 3.5.x; Delta 2.4↔3.4.
  https://docs.delta.io/releases
- **Delta 4.1.0 (2026-03-01) adds full support for Spark 4.1.0** with the suffixed artifact
  `delta-spark_4.1_2.13`; Delta 4.3.0 is built on Spark 4.1.0 and 4.0.1. So Spark 4.1 + Delta is real today.
  https://delta.io/blog/2026-03-01-delta-lake-4-1-0-released · https://github.com/delta-io/delta/releases
- hadoop-aws must equal Spark's bundled hadoop-client or s3a throws NoSuchMethodError; Spark 3.5 bundles
  Hadoop 3.3.4, Spark 4.x bundles 3.4.1 (AWS SDK v2). https://central.sonatype.com/artifact/org.apache.spark/spark-hadoop-cloud_2.13/3.5.0
- Patch nuance (only relevant if you ever go 3.5): delta-spark 3.2.0 is last for pyspark 3.5.2;
  3.3.x needs pyspark>=3.5.3. https://community.databricks.com/t5/data-engineering/dbr-16-4-lts-spark-3-5-2-is-not-compatible-with-delta-lake-3-3-1/td-p/121221

## Applied

- `docs/GAP_REGISTER.md` GAP-017 row rewritten to "Resolved: adopt the Spark 4.1 stack (Python 3.14)".
- `docs/STATE_AND_ROADMAP.md` Pinned-stack + Windows-setup rewritten to Spark 4.1 / delta 4.1.x /
  hadoop-aws 3.4.1 / JDK 17–21.
- `docs/index.html` Engine pills + GAP-017 chip + Wave-1 chip + Contract A updated to the 4.1 stack.
- `docs/GAP_TASKS.md` GAP-017 task carries the full implementation spec (pin pyproject, guard test,
  README section). Implementation of the pins themselves is the GAP-017 task, not this doc pass.

## GAP-017 implementation confirmation — 2026-06-24

Local files re-read first: `AGENTS.md`, `pyproject.toml`, `README.md`, `.env.example`,
`tests/test_infra_minio.py`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`,
`docs/index.html`, `docs/PROGRESS_LOG.md`, and `.planning/COURSEWORK_PROGRESS.md`.

Live environment commands:

- `python --version` -> `Python 3.14.0`.
- `python -c "import pandas,pyarrow,numpy;print(pandas.__version__,pyarrow.__version__,numpy.__version__)"`
  -> `3.0.3 24.0.0 2.4.4`.
- `java -version` -> `1.8.0_491`.
- `JAVA_HOME` is unset.

External docs checked during implementation:

- Apache Spark 4.1.2 overview: Spark docs identify this as Spark 4.1.2 documentation and state
  Spark runs on Java 17/21, Scala 2.13, and Python 3.10+:
  https://spark.apache.org/docs/latest/
- Apache Spark 4.1.1 docs via Context7 confirmed the same Java 17/21, Scala 2.13, Python 3.10+
  requirement and the PySpark 4.1 pandas/pyarrow minimums:
  https://spark.apache.org/docs/4.1.1/index.html and
  https://spark.apache.org/docs/4.1.1/api/python/migration_guide/pyspark_upgrade.html
- Apache Spark downloads page confirms Spark 4.1.2 is a current stable release and Spark 3.5.8 is a
  separate older line: https://spark.apache.org/downloads.html
- Delta Lake 4.1.0 release notes state full Apache Spark 4.1.0 support, the
  `delta-spark_4.1_2.13` Maven artifact naming, Java 17+, and dropped Spark 3.5 support:
  https://delta.io/blog/2026-03-01-delta-lake-4-1-0-released/
- Delta Lake GitHub releases show later Delta Spark 4.x releases publishing Spark 4.1 / Scala 2.13
  artifacts and the Python `delta-spark` artifact: https://github.com/delta-io/delta/releases
- Hadoop 3.4.1 `hadoop-aws` docs state the page version is 3.4.1, S3A uses the AWS Java V2 SDK,
  `hadoop-aws` and `hadoop-common` versions must be identical, and the AWS V2 shaded `bundle`
  JAR is required with S3A:
  https://hadoop.apache.org/docs/r3.4.1/hadoop-aws/tools/hadoop-aws/index.html and
  https://hadoop.apache.org/docs/r3.4.1/hadoop-aws/tools/hadoop-aws/aws_sdk_upgrade.html

Package-index checks:

- `python -m pip index versions pyspark` -> latest/resolved `4.1.2`; available line includes
  `4.1.2, 4.1.1, 4.1.0` and older `3.5.x`.
- `python -m pip index versions delta-spark` -> latest `4.3.0`; available line includes
  `4.1.0`.
- `python -m pip index versions hadoop-aws` -> no matching PyPI distribution. The `hadoop-aws`
  pin therefore records the required JVM/Maven coordinate for Spark's `s3a://` path; pip cannot
  install that artifact as a Python wheel.

Decision held: Stack A remains non-viable for this repo's Python 3.14 runtime, so GAP-017 pins the
Spark 4.1 line and records the JDK/JVM connector requirements without claiming any live Spark run.

## PR review fix: S3A is Maven, not pip — 2026-06-24

Review finding P1 was correct: `hadoop-aws` is a JVM/Maven artifact, not a PyPI package. The
`[spark]` extra must contain only Python packages (`pyspark==4.1.*`, `delta-spark==4.1.*`).
The S3A connector belongs in the future SparkSession's `spark.jars.packages` value.

MCP/provider evidence:

- Context7 `/apache/hadoop` returned the Hadoop `hadoop-aws` docs and stated S3A needs the
  `hadoop-aws` JAR plus the shaded AWS SDK V2 `bundle` JAR, with `hadoop-common` and
  `hadoop-aws` versions identical:
  https://github.com/apache/hadoop/blob/trunk/hadoop-tools/hadoop-aws/src/site/markdown/tools/hadoop-aws/index.md
- Context7 `/websites/hadoop_apache_stable` returned the stable Hadoop S3A docs with the same
  guidance and Spark classloader caveat:
  https://hadoop.apache.org/docs/stable/hadoop-aws/tools/hadoop-aws/index.html
- Ref search for "Apache Hadoop 3.4.1 hadoop-aws S3A AWS SDK v2 bundle Maven coordinate
  software.amazon.awssdk bundle" failed with: "Not enough credits. Visit https://ref.tools/account
  to upgrade." I therefore used Context7 plus official Apache/Maven URLs for the exact coordinate.

Exact coordinate evidence:

- Hadoop 3.4.1 S3A docs: S3A uses the AWS Java V2 SDK and requires the `hadoop-aws` JAR with the
  AWS V2 shaded `bundle` JAR; `hadoop-aws` and `hadoop-common` versions must be identical:
  https://hadoop.apache.org/docs/r3.4.1/hadoop-aws/tools/hadoop-aws/index.html
- Hadoop 3.4.1 `hadoop-aws` POM depends on `software.amazon.awssdk:bundle`:
  https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.4.1/hadoop-aws-3.4.1.pom
- Hadoop 3.4.1 project POM sets `<aws-java-sdk-v2.version>2.24.6</aws-java-sdk-v2.version>`:
  https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-project/3.4.1/hadoop-project-3.4.1.pom
- Delta 4.1.0 release notes document full Spark 4.1.0 support and the Spark-version-suffixed
  Maven coordinate form `io.delta:delta-spark_4.1_2.13:{DELTA_VERSION}`:
  https://delta.io/blog/2026-03-01-delta-lake-4-1-0-released/

Applied review decision:

- Remove `hadoop-aws` from `[project.optional-dependencies].spark` entirely.
- Add `src/railway_lakehouse/spark_config.py` with
  `SPARK_S3A_PACKAGES="org.apache.hadoop:hadoop-aws:3.4.1,software.amazon.awssdk:bundle:2.24.6"`
  and `DELTA_SPARK_MAVEN_PACKAGE="io.delta:delta-spark_4.1_2.13:4.1.0"`.
- Update README, `.env.example`, `docs/STATE_AND_ROADMAP.md`, `docs/index.html`, `docs/TASKS.md`,
  `docs/GAP_REGISTER.md`, and `docs/GAP_TASKS.md` so pip and Maven responsibilities are separated.
