# Verification

## Current Verification State

Deterministic characterization tests now exist under `tests/`.

Fresh results from 2026-06-24 after GAP-009:

```bash
python -m pytest -q
python -m pytest -q -m "unit or integration"
python -m pytest -q -m spark
python -c "import railway_lakehouse.spark_jobs.coverage"
python -m compileall -q src tests
git diff --check
```

Observed results:

- Full suite passed: 105 passed.
- Unit/integration marker suite passed: 103 passed, 2 deselected.
- Spark marker suite passed: 2 passed, 103 deselected.
- Spark coverage import command passed.
- GAP-012 guard tests pass: missing/empty local `--bronze-root` fails before
  Gold writing, and live-check run-id nesting remains pinned.
- GAP-009 guard tests pass: missing Gold input raises `FileNotFoundError` and a
  0-row Gold Parquet raises `ValueError`.
- Compileall passed.
- `git diff --check` passed with line-ending warnings only.

## GAP-011 report and presentation evidence links (2026-06-24)

GAP-011 added the course report and presentation drafts under `output/`, plus a
deterministic evidence-link checker.

Deliverables:

- Report draft: `output/report/REPORT.md`.
- Presentation draft: `output/presentation/PRESENTATION.md`.
- Checker: `tests/test_report_evidence_links.py`.

Commands:

```powershell
python -m pytest -q tests/test_report_evidence_links.py
python -c 'import re,os; missing=[p for f in ["output/report/REPORT.md","output/presentation/PRESENTATION.md"] for p in re.findall("output/evidence/[^\\s\\)\\]\\\"`]+", open(f,encoding="utf-8").read()) if not os.path.exists(p)]; print("MISSING EVIDENCE PATHS:", missing); assert not missing'
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot'; python -m pytest -q
python -m compileall -q src tests
git diff --check
```

Observed results:

- Evidence-link checker passed: 3 passed.
- Evidence path scan printed `MISSING EVIDENCE PATHS: []`.
- Full suite passed with the existing JDK 21 runtime env: 108 passed, 1 skipped.
- The skipped test was the pre-existing Windows Spark write-path check because
  `HADOOP_HOME`/`winutils.exe` is not present in this worktree; Spark guard
  coverage still ran.
- Compileall passed.
- `git diff --check` passed with CRLF warnings only.

PowerShell note: the Bash-style chained one-liner from the GAP-011 task failed
before running tests in this shell because the regex contains a backtick, which
PowerShell treats as an escape character. The same three checks were run as the
PowerShell-safe commands above.

Additional local stats Bronze -> Gold validation (GAP-012 corrected recipe,
2026-06-24):

Raw Bronze bytes under `output/evidence/**/bronze/` are intentionally ignored by
Git. The committed `output/evidence/local-stats-bronze/manifest.json` is the
audit snapshot, not a complete raw Bronze tree, so raw Bronze must be
regenerated on a clean checkout. Use the fresh regen directory below; reusing
`output/evidence/local-stats-bronze` would collide with the committed
`manifest.json` and make `live_check` write under a run-id subdirectory.
`--max-artifacts 1` means one bounded dataset or series per stats source, plus
the required source catalogue artifact.

```powershell
$env:PYTHONPATH='src'
python -c "import pathlib, railway_lakehouse; print(pathlib.Path(railway_lakehouse.__file__).as_posix())"
python -m pytest -q
python -m railway_lakehouse.bronze.live_check --sources eurostat,worldbank --out output/evidence/local-stats-bronze-regen --max-artifacts 1 --timeout-seconds 60
python -m railway_lakehouse.pipeline --bronze-root output/evidence/local-stats-bronze-regen/bronze --skip-news-extraction --news 0 --out output/evidence/local-stats-bronze-regen/railway_ml.parquet --crosswalk-path output/evidence/local-stats-bronze-regen/crosswalk_cache.json --counts-out output/evidence/local-stats-bronze-regen/counts.json
python -m json.tool output/evidence/local-stats-bronze-regen/counts.json
```
Observed results:

* Local stats Bronze landing passed for Eurostat and World Bank:
  4 artifacts, 14,996,995 bytes.
* Committed Bronze audit snapshot: output/evidence/local-stats-bronze/manifest.json.
* Regenerated raw Bronze tree:
  output/evidence/local-stats-bronze-regen/bronze.
* First real stats-only Gold written by the regen recipe:
  output/evidence/local-stats-bronze-regen/railway_ml.parquet.
* Gold counts recorded by the pipeline:
  output/evidence/local-stats-bronze-regen/counts.json.
* Gold shape: 2,139 rows x 3 columns.
* Gold columns: [geo, year, rail_network_length_km].
* The Gold feature is the World Bank route-km series. Eurostat raw bytes were
  landed in Bronze, but the bounded Eurostat dataset did not contribute a Gold
  feature in this smoke because its label remained unmapped.
* Gold includes both target countries: AT and HU.
* Gold year range: 1995-2021.
* News extraction was intentionally skipped with --skip-news-extraction; this does not prove live LLM/news extraction.
* Negative guard check: `python -m railway_lakehouse.pipeline --bronze-root output/evidence/does-not-exist/bronze --skip-news-extraction --news 0 --out output/runtime/gap-012-negative/empty.parquet` exited non-zero with a `FileNotFoundError` mentioning `--bronze-root` and `live_check`; `output/runtime/gap-012-negative/empty.parquet` was not created.


Additional GAP-004 fixture E2E validation from 2026-06-22:

```bash
python -m pytest -q tests\test_pipeline_gaps.py
python -m pytest -q -m integration
python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction
python -c "import pandas as pd; df=pd.read_parquet(r'output\evidence\fixture-e2e\railway_ml.parquet'); print(df.shape); print(df.to_string(index=False))"
```

Observed results:

- Pipeline GAP test passed: 5 passed.
- Integration marker suite passed: 6 passed, 54 deselected.
- Fixture pipeline command wrote `output/evidence/fixture-e2e/railway_ml.parquet` and `output/evidence/fixture-e2e/crosswalk_cache.json`.
- Parquet readback returned shape `(4, 3)` with `AT/HU` rows for `2020/2021`.
- The fixture CLI run used `--skip-news-extraction`, so it did not prove a live Ollama service.

Additional GDELT validation from 2026-06-22:

```bash
python -m pytest -q tests\test_bronze_characterization.py -k "gdelt or past_recordings"
python -m pytest -q tests\test_bronze_characterization.py
bounded GDELT live retry probe through gdelt.ingest with max_records=25 and max_retries=1
```

Observed results:

- GDELT/past-recordings targeted tests passed: 6 passed, 17 deselected.
- Bronze characterization passed: 23 passed.
- Bounded GDELT live retry probe wrote `output/evidence/gdelt-live-check-2026-06-22/manifest.json`: failed, 0 artifacts, 0 bytes; HU returned HTTP 429 after retry handling and AT failed with a remote disconnect.
- No long historical backfill was run.

Additional KSH validation from 2026-06-22:

```bash
python -m pytest -q tests\test_bronze_characterization.py
python -m pytest -q tests\test_bronze_live_check.py
python -m pytest -q tests\test_bronze_live_check_integration.py
python -m pytest -q -m integration
python -m railway_lakehouse.bronze.live_check --sources ksh --out output/evidence/ksh-live-check-2026-06-22-current --max-artifacts 6 --timeout-seconds 30
python -m json.tool output\evidence\ksh-live-check-2026-06-22-current\manifest.json
```

Observed results:

- Bronze characterization passed: 15 passed.
- Bronze live-check unit tests passed: 8 passed.
- Bronze KSH live-check integration test passed: 1 passed.
- Integration marker suite passed its implemented fixture path: 1 passed, 1 xfailed for documented GAP-004.
- Bounded KSH live check passed with 6 artifacts, 92,509 bytes, and 0 failures.
- Current KSH live-check manifest JSON validated successfully.

Additional UIC validation from 2026-06-22:

```bash
python -m pytest -q tests\test_bronze_live_check.py
python -m pytest -q tests\test_bronze_characterization.py::test_uic_public_resources_use_current_free_pdf_endpoints tests\test_bronze_characterization.py::test_uic_pdf_validation_rejects_html_empty_and_non_200 tests\test_bronze_characterization.py::test_uic_ingest_lands_valid_public_pdfs_and_skips_html_or_404 tests\test_bronze_live_check.py::test_collect_uic_lands_successes_and_records_failures
python -m railway_lakehouse.bronze.live_check --sources uic --out output/evidence/uic-live-check-2026-06-22 --max-artifacts 2 --timeout-seconds 30
python -m compileall .
python -m pytest -q
```

Observed results:

- Bronze live-check unit tests passed: 9 passed.
- UIC-specific source/live-check tests passed: 4 passed.
- Bounded UIC live check passed with 2 artifacts, 2,109,240 bytes, and 0 failures.
- Compileall passed.
- Full suite passed: 43 passed, 1 xfailed for documented GAP-004.

## Safe Checks Now

Run from `bigdata/course_proj`:

```bash
python -m pip install -e ".[test]" -c constraints.txt
python -m pip install --dry-run -e ".[test]" -c constraints.txt
python -m pytest -q tests/test_env_versions.py
python -m pytest -q -m unit
python -m pytest -q
```

Use `-c constraints.txt` to reproduce the graded pandas/pyarrow/S3 runtime stack. Omitting `-c` allows resolver drift; the environment guard fails if pandas or pyarrow moves outside the validated major window.

Do not run `live`, `spark`, or `slow` tests unless the command is explicit and the services are available.

## Current Tests

```text
tests/
  test_bronze_characterization.py
  test_bronze_live_check.py
  test_bronze_live_check_integration.py
  test_env_versions.py
  test_silver_characterization.py
  test_silver_persist.py
  test_silver_persist_integration.py
  test_gold_characterization.py
  test_infra_minio.py
  test_pipeline_gaps.py
  fixtures/bronze/
```

The pipeline gap test now closes GAP-004 with fixture-backed Bronze readers and a no-network Bronze -> Silver -> Gold integration path.

## Future Checks

### Integration Fixture E2E

Implemented for GAP-004 with repo-local input fixtures under `tests/fixtures/bronze/`.

The evidence command is:

```bash
python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction
```

Command target:

```bash
python -m pytest -q -m integration
```

### Spark Evidence

GAP-009 now has a local Spark evidence command over the richest real Gold
Parquet. Install the pinned optional stack first (`pyspark==4.1.*` and
`delta-spark==4.1.*` only). Runtime execution requires JDK 17 or 21 with
`JAVA_HOME`; native Windows also needs `HADOOP_HOME` pointing at a Hadoop 3.4.x
helper directory containing `bin/winutils.exe` and `bin/hadoop.dll`.

```bash
python -m pip install -e ".[spark]"
python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/inventory-live-2026-06-23/railway_ml.parquet --out output/evidence/spark/
python -m json.tool output/evidence/spark/manifest.json
```

Observed 2026-06-24:

- Evidence command exited 0.
- Evidence manifest: `output/evidence/spark/manifest.json`.
- Spark output directory: `output/evidence/spark/coverage_by_geo_year/`.
- Spark version: 4.1.2.
- Java version: 21.0.11.
- Input Gold: 2,968 rows x 4 columns
  `[geo, year, rail_freight_tonne_km, rail_network_length_km]`.
- Output coverage: 2,968 rows x 5 columns
  `[geo, year, row_count, rail_freight_tonne_km_non_null, rail_network_length_km_non_null]`.
- Files written include `_SUCCESS` and one
  `part-*.snappy.parquet` data file; Windows local mode also writes Hadoop CRC
  sidecars.
- `partitions_written`: 1.
- `status`: `passed`.

Guard behavior:

- Missing input raises `FileNotFoundError` with a hint to run the Gold pipeline
  or pass an existing Gold Parquet.
- A 0-row input raises `ValueError`; the job does not silently write empty Spark
  evidence.

## Evidence Directory

Use:

```text
output/
  evidence/
  runtime/
  report/
  presentation/
```

Keep public deliverables outside `output/runtime/`.


## MinIO lakehouse storage smoke (GAP-010)

Local MinIO storage was verified by a bounded smoke check.

Commands used:

- cp .env.example .env
- docker compose up -d
- docker compose ps
- python scripts/minio_smoke.py
- python -m pytest -q tests/test_infra_minio.py
- python -m pytest -q

Observed results:

- Docker MinIO container is running as railway-minio.
- MinIO API is exposed at http://localhost:9000.
- MinIO console is exposed at http://localhost:9001.
- Buckets verified by smoke: bronze, silver, gold.
- s3fs write/read/delete round-trip succeeded.
- Smoke evidence: output/evidence/minio-smoke/manifest.json.
- Smoke status: passed.
- roundtrip_ok: true.
- bytes_written: 32.
- bytes_read: 32.
- Unit guard tests passed: tests/test_infra_minio.py (4 passed).
- Full test suite passed: 87 passed.

Scope note: this verifies the local object-storage path for infra/minio-storage.
It does not claim full persisted Bronze->Silver->Gold through MinIO; that remains
tied to silver/persist-outputs and gold/load-from-silver.
