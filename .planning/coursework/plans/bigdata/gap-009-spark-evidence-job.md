# GAP-009 Spark Evidence Job Implementation Plan

> Approved by this agent on 2026-06-24 after self-review. Scope is limited to GAP-009 plus the already-required GAP-017 guard check.

**Goal:** Add an importable PySpark coverage job that reads the real Gold Parquet and writes committed Spark evidence under `output/evidence/spark/`.

**Architecture:** Keep the Spark job isolated in `railway_lakehouse.spark_jobs.coverage`. The module imports without PySpark by deferring Spark imports into Spark-only helpers; `main()` owns SparkSession lifecycle and failed-manifest handling, while `run_coverage()` validates input, performs deterministic aggregation, writes the output Parquet directory, and returns the manifest payload.

**Tech Stack:** Python 3.12-3.14, PySpark 4.1.x optional extra, pandas/pyarrow for test fixture Parquet, pytest markers `unit` and `spark`.

---

## File Responsibilities

- `src/railway_lakehouse/spark_jobs/__init__.py`: package marker with docstring only.
- `src/railway_lakehouse/spark_jobs/coverage.py`: CLI, SparkSession builder, input validation, deterministic aggregation, manifest writing, failure manifest handling.
- `tests/test_spark_coverage.py`: Spark-marked tests that build their own Gold input under `tmp_path` and skip when PySpark is absent.
- `tests/test_spark_stack_pins.py`: CI-safe unit guard that imports the coverage module without PySpark and verifies callables/defaults alongside existing GAP-017 pin checks.
- Docs/dashboard/evidence files: sync GAP-009 status, verification commands, progress logs, and committed Spark output evidence.

## Tasks

### Task 1: Tests First

- [ ] Add `tests/test_spark_coverage.py` with module-level `pytest.importorskip("pyspark")`, a `spark` marker, a success test using `coverage.main([... "--master", "local[1]"])`, and guard tests for missing and empty inputs through `run_coverage()`.
- [ ] Extend `tests/test_spark_stack_pins.py` with a `unit` import contract for `railway_lakehouse.spark_jobs.coverage`, `main`, `run_coverage`, `build_session`, and the default real Gold path.
- [ ] Run the import/pin guard and confirm it fails because `railway_lakehouse.spark_jobs.coverage` does not exist yet.

### Task 2: Spark Job Implementation

- [ ] Create `src/railway_lakehouse/spark_jobs/__init__.py`.
- [ ] Create `src/railway_lakehouse/spark_jobs/coverage.py` with:
  - `DEFAULT_INPUT = "output/evidence/inventory-live-2026-06-23/railway_ml.parquet"`
  - `DEFAULT_OUT = "output/evidence/spark/"`
  - `build_session(master)`
  - `run_coverage(spark, input_path, out_dir) -> dict`
  - `_write_json(path, payload)`
  - `main(argv=None)`
- [ ] Keep PySpark imports inside Spark-executing functions so plain imports pass without the optional extra.
- [ ] Validate missing input with `FileNotFoundError` including the path and remediation hint.
- [ ] Validate empty input with `ValueError` before writing output.
- [ ] Aggregate by `geo` and `year` with deterministic non-null feature counts and `row_count`.
- [ ] Write `coverage_by_geo_year` as a Spark Parquet directory and scan it for files plus part-file count.
- [ ] Write `manifest.json` with timestamps, command, Spark version, input/output counts, file list, partition count, duration, status, Java version, `JAVA_HOME`, and evidence path.
- [ ] Ensure `main()` writes a failed manifest on exceptions, prints the evidence path, returns nonzero, and always stops Spark when a session was built.

### Task 3: Documentation And Dashboard

- [ ] Update `README.md` with the Spark evidence command, JDK 17/21 note, and evidence path.
- [ ] Replace `docs/VERIFICATION.md` Spark placeholder with the real command, manifest fields, and observed output after running.
- [ ] Update `docs/TASKS.md` to mark `spark/evidence-job` done and Contract B Spark evidence checks complete.
- [ ] Update `docs/GAP_REGISTER.md` GAP-009 status and add Test Failure Mapping rows for unit/import, Spark evidence, compileall/full suite, and any skipped Spark marker result.
- [ ] Update `docs/index.html` Spark chip/metric and Wave 2/Contract B display.
- [ ] Append the handoff entry to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

### Task 4: Verification And PR

- [ ] Run `python -m pytest -q -m "unit or integration"`.
- [ ] Run `python -c "import railway_lakehouse.spark_jobs.coverage"`.
- [ ] Install/confirm the pinned `[spark]` extra and JDK 17 or 21 before live Spark execution.
- [ ] Run `python -m pytest -q -m spark`.
- [ ] Run `python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/inventory-live-2026-06-23/railway_ml.parquet --out output/evidence/spark/`.
- [ ] Run `python -m json.tool output/evidence/spark/manifest.json`.
- [ ] Run `python -m pytest -q`, `python -m compileall -q src tests`, and `git diff --check`.
- [ ] Commit, push `impl/gap-009`, open a PR against `main`, and verify mergeability.

## Self-Review

- Spec coverage: every GAP-009 step maps to the tasks above; GAP-017 is confirmed through existing pins and the unit guard; S3A config remains out of the local job.
- Placeholder scan: no task defers an unspecified implementation detail; every output path and command is concrete.
- Type consistency: public names are stable across tests, implementation, docs, and CLI (`build_session`, `run_coverage`, `main`, `coverage_by_geo_year`, `manifest.json`).
