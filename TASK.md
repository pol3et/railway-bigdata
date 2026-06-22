# Course Project Task

Source prompt: `task.png`

## Extracted Requirements

1. Data gathering:
   - Implement a data collection system from selected sources.
   - Use web technologies.
   - Provide the possibility of automatic updates.

2. Big Data technology:
   - Select and implement a Big Data technology such as MapReduce, Spark, or Storm.

3. Processing and analysis:
   - Process and analyze collected and stored data.
   - Show practical value in a short report and presentation.

4. Depth and volume:
   - Final points depend on the depth and volume of processing jobs.

## Local Project Topic

Railway data and news analysis for Hungary and Austria, with possible international context from Eurostat, World Bank, UIC, GDELT, RSS feeds, and national statistics sources.

## Target Deliverables

- Raw data collection with update cadence.
- Bronze/Silver/Gold lakehouse data contracts.
- Reproducible feature matrix in Parquet.
- Spark-backed or otherwise Big-Data-backed analysis jobs.
- Evidence: commands, logs, row counts, source counts, feature coverage, and generated files.
- Short report.
- Presentation.

## Current Gaps

- Deterministic fixture Bronze reads are wired in `src/railway_lakehouse/pipeline.py`; live MinIO end-to-end evidence is still not recorded.
- New national/historical fetchers are present but not imported by the Bronze scheduler.
- No Spark job exists yet under `src/railway_lakehouse/spark_jobs/`.
- Fixture Gold Parquet evidence exists under `output/evidence/fixture-e2e/`; live/Spark/report evidence is still missing.

## Acceptance Bar For Future Agents

A future agent can mark the project implementation ready only when it can point to:

- a documented install command,
- a deterministic smoke test,
- at least one generated output dataset,
- evidence that the Big Data technology path ran,
- report/presentation drafts grounded in generated outputs.
