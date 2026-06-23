# Verification

## Current Verification State

Deterministic characterization tests now exist under `tests/`.

Fresh results from 2026-06-23 after syncing PR #9 and PR #10 into `main`:

```bash
python -m pytest -q
python -m compileall -q src tests
git diff --check
```

Observed results:

- Full suite passed: 74 passed.
- GAP-004 fixture pipeline tests passed; there is no current expected xfail.
- GAP-006 merged slice tests now cover World Bank/Eurostat Silver stats
  fixtures and RSS/GDELT Silver news parser fixtures.
- Compileall passed.
- `git diff --check` passed.

Additional local stats Bronze -> Gold validation from 2026-06-23:

Raw Bronze bytes under `output/evidence/**/bronze/` are intentionally ignored by
Git. Re-run the live-check command first on a clean checkout; the committed
manifest is the audit snapshot. `--max-artifacts 1` means one bounded dataset or
series per stats source, plus the required source catalogue artifact.

```powershell
$env:PYTHONPATH='src'
python -c "import pathlib, railway_lakehouse; print(pathlib.Path(railway_lakehouse.__file__).as_posix())"
python -m pytest -q
python -m railway_lakehouse.bronze.live_check --sources eurostat,worldbank --out output/evidence/local-stats-bronze --max-artifacts 1 --timeout-seconds 60
python -m railway_lakehouse.pipeline --bronze-root output/evidence/local-stats-bronze/bronze --skip-news-extraction --news 0 --out output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet --crosswalk-path output/evidence/first-real-gold-local-stats-v2/crosswalk_cache.json --counts-out output/evidence/first-real-gold-local-stats-v2/counts.json
python -m json.tool output/evidence/first-real-gold-local-stats-v2/counts.json
```
Observed results:

* Full suite passed: 83 passed after rebasing on the merged Silver persistence branch.
* Local stats Bronze landing passed for Eurostat and World Bank.
* Bronze evidence snapshot: output/evidence/local-stats-bronze/manifest.json.
* Live bounded Bronze artifacts: 4 artifacts, 14,996,995 bytes.
* First real stats-only Gold written to output/evidence/first-real-gold-local-stats-v2/railway_ml.parquet.
* Gold counts recorded by the pipeline in output/evidence/first-real-gold-local-stats-v2/counts.json.
* Gold shape: 2,139 rows x 3 columns.
* Gold columns: geo, year, rail_network_length_km.
* The Gold feature is the World Bank route-km series. Eurostat raw bytes were
  landed in Bronze, but the bounded Eurostat dataset did not contribute a Gold
  feature in this smoke because its label remained unmapped.
* Gold includes both target countries: AT and HU.
* Gold year range: 1995-2021.
* News extraction was intentionally skipped with --skip-news-extraction; this does not prove live LLM/news extraction.


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
