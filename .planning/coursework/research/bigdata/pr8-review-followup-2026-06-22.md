# PR #8 Review Follow-Up - 2026-06-22

## Scope

Review the automated PR #8 findings from the other agent, apply actionable
minor fixes, and merge the PR if verification remains clean.

## Local Research

Files and context reviewed:

- PR #8 top-level review comment fetched through the GitHub review-comment
  workflow.
- `src/railway_lakehouse/pipeline.py`
- `tests/test_pipeline_gaps.py`
- `docs/VERIFICATION.md`
- `docs/PIPELINE.md`
- `docs/GAP_REGISTER.md`
- Existing GAP-004 research/progress notes.

No external docs were needed. This was repo-local review follow-up.

## Applied Findings

- Added contextual errors for malformed Bronze path parsing.
- Simplified the news limit check after the existing `limit <= 0` guard.
- Added `--crosswalk-path` so the committed fixture crosswalk evidence is
  reproducible from the documented command.
- Stopped falling back from missing article body to title text.
- Normalized fallback article IDs with forward slashes.
- Switched article date normalization to `pandas.to_datetime` with explicit
  compact timestamp handling.
- Reworded the pipeline docstring so live MinIO read-back is not implied as
  proven.
- Left the local/S3 helper duplication as acceptable for the current two
  backends; no broader abstraction was needed.

## Evidence

- `python -m pytest -q tests\test_pipeline_gaps.py` passed: 5 passed.
- `python -m railway_lakehouse.pipeline --bronze-root tests\fixtures\bronze --news 1 --out output\evidence\fixture-e2e\railway_ml.parquet --crosswalk-path output\evidence\fixture-e2e\crosswalk_cache.json --skip-news-extraction` passed.
- Parquet readback returned `(4, 3)` with `AT/HU` rows for `2020/2021`.
- `output/evidence/fixture-e2e/crosswalk_cache.json` contains
  `Rail passengers total -> rail_passengers`.
- `python -m pytest -q` passed: 60 passed.
- `python -m pytest -q -m integration` passed: 6 passed, 54 deselected.
- `python -m compileall src tests` passed.

## Boundary

No live collectors, MinIO service, live Ollama model, Spark job, report, or
presentation output was executed for this review follow-up.
