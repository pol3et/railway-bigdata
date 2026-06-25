# PR 27 Spark analysis review fixes - 2026-06-25

## Local research

- Reviewed PR #27 with `ship-it:ship-pr` and retained the isolated worktree at
  `../Halo-Skills-pr-27`.
- Inspected local contracts first: `AGENTS.md`, `docs/DATA_CONTRACTS.md`,
  `docs/VERIFICATION.md`, `docs/TASKS.md`, and `docs/index.html`.
- Confirmed Gold contract does not define `terrain_complexity`; hardcoding it in
  `src/railway_lakehouse/gold/build.py` would create a fabricated feature.
- Confirmed committed Spark evidence input exists at
  `output/evidence/inventory-live-2026-06-23/railway_ml.parquet`; the PR's new
  Spark jobs instead defaulted to a non-committed
  `output/evidence/bigdata/railway_ml.parquet`.
- Confirmed PR analysis CSV/JSON artifacts were committed at repository root
  under `analysis_artifacts/`, while the project rule requires runtime outputs
  under `output/` or a documented lakehouse path.

## External docs

- Context7 PySpark docs were checked for Spark API claims:
  - `DataFrameStatFunctions.corr` supports Pearson and Spearman correlation:
    https://spark.apache.org/docs/latest/api/python/_sources/reference/pyspark.sql/api/pyspark.sql.DataFrameStatFunctions.rst.txt
  - `DataFrameWriter.parquet` writes Parquet output directories:
    https://spark.apache.org/docs/latest/api/python/_sources/reference/pyspark.sql/api/pyspark.sql.DataFrameWriter.parquet.rst.txt
  - `percent_rank` is a Spark SQL window ranking function, so by-country
    Spearman ranking must partition by country as well as the variable label:
    https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.functions.percent_rank.html

## Fix plan

- Remove the fabricated `terrain_complexity` Gold feature and its test/doc
  claims.
- Point new Spark job defaults at an existing committed Gold Parquet, then fail
  loudly if the selected input lacks the investment/regional columns needed by
  that analysis.
- Make correlation output directories mode-specific so panel and level runs do
  not overwrite each other.
- Rank per-country Spearman values within each country.
- Add guards so the Spark analysis jobs cannot publish `status: passed` with no
  analytical rows or no investment/regional signal.
- Move committed analysis artifacts to `output/evidence/analysis-artifacts/` and
  update their copied output paths honestly; preserve that the source Gold used
  for the snapshot is not committed in this PR.
- Add deterministic tests for import/default behavior and pure logic helpers,
  plus Spark-marked integration coverage for the jobs when local Hadoop native
  helpers are available.
- Update dashboard/task/verification/progress docs before stopping.
