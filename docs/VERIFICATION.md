# Verification

## Current Verification State

Deterministic characterization tests now exist under `tests/`.

Fresh results from 2026-06-21:

```bash
python -m pip install --no-cache-dir -e ".[test]"
python -m pytest -q -m unit
python -m pytest -q
python -m pip check
python -m compileall .
```

Observed results:

- Editable install passed.
- Unit suite passed: 15 passed, 1 deselected.
- Full suite passed: 15 passed, 1 xfailed.
- Expected failure: `tests/test_pipeline_gaps.py::test_pipeline_storage_read_stubs_are_not_wired`, mapped to GAP-004.
- `python -m pip check` reported no broken requirements.
- Compileall passed.

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
