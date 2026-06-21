# Tests

Run from `bigdata/course_proj`.

```bash
python -m pytest -q
python -m pytest -q -m unit
```

Markers:

- `unit`: deterministic tests with no network or external services.
- `integration`: deterministic cross-layer fixture tests.
- `live`: opt-in real endpoint or service checks.
- `spark`: Spark-dependent checks.
- `slow`: long-running checks.

Expected failures must include a `docs/GAP_REGISTER.md` gap ID in the `xfail` reason.

The current suite uses path shims in `conftest.py` because the project has not yet migrated to one `src/railway_lakehouse` import root. Remove those shims when GAP-002 is closed.
