# Verification

## Current Verification State

Deterministic characterization tests now exist under `tests/`.

Fresh results from 2026-06-22:

```bash
python -m pytest -q
python -m compileall src tests
```

Observed results:

- Full suite passed: 43 passed, 1 xfailed.
- Expected failure: `tests/test_pipeline_gaps.py::test_pipeline_storage_read_stubs_are_not_wired`, mapped to GAP-004.
- Compileall passed.
- `git diff --check` passed.

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
python -m pip install -e ".[test]"
python -m pytest -q -m unit
python -m pytest -q
```

Do not run `live`, `spark`, or `slow` tests unless the command is explicit and the services are available.

## Current Tests

```text
tests/
  test_bronze_characterization.py
  test_bronze_live_check.py
  test_bronze_live_check_integration.py
  test_silver_characterization.py
  test_gold_characterization.py
  test_pipeline_gaps.py
```

The pipeline gap test is a strict `xfail`; if it starts passing, GAP-004 should be reviewed and closed only after fixture evidence is recorded.

## Future Checks

### Integration Fixture E2E

1. Land or load a tiny local fixture into a test Bronze area.
2. Read it into Silver.
3. Build Gold.
4. Write a Parquet artifact under `output/evidence/fixture-e2e/`.

Command target:

```bash
python -m pytest -q -m integration
```

### Spark Evidence

Future Spark evidence should capture:

- command used,
- Spark version,
- input rows,
- output rows,
- partitions/files written,
- job duration if available,
- output path.

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
