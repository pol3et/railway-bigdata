# GDELT Rate-Limit Handling

Date: 2026-06-22

Task: `parser/gdelt-rate-limit`

## Local Research First

Files reviewed:

- `AGENTS.md`
- `README.md`
- `TASK.md`
- `docs/PROGRESS_LOG.md`
- `docs/GAP_REGISTER.md`
- `docs/PARSER_WORK_LOG.md`
- `docs/CODEMAP.md`
- `docs/DATA_CONTRACTS.md`
- `docs/WORKSTREAMS.md`
- `docs/VERIFICATION.md`
- `WIRING.md`
- `src/railway_lakehouse/bronze/sources/gdelt.py`
- `src/railway_lakehouse/bronze/sources/past_recordings.py`
- `tests/test_bronze_characterization.py`

Relevant local findings:

- `docs/PARSER_WORK_LOG.md` recorded HTTP 429 failures for both recent GDELT and historical DOC probes.
- `src/railway_lakehouse/bronze/sources/gdelt.py` skipped every non-200 response and requested `maxrecords=250`.
- `src/railway_lakehouse/bronze/sources/past_recordings.py` skipped non-200 responses, used `PAGE_SIZE=250`, and had no CLI dry-run or max-page guard.
- Bronze must keep raw fetched bytes immutable; retry and request bounding belong in fetch control flow, not parsing.

## External Source Checks

Ref search was attempted first but returned an account-credit error, so the external check used web search against official GDELT pages.

Official GDELT sources:

- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- https://blog.gdeltproject.org/announcing-the-gdelt-context-2-0-api/
- https://www.gdeltproject.org/data.html

External findings:

- GDELT describes DOC 2.0 as its full-text search API with JSON/JSONP output.
- The documented DOC API parameters include `TIMESPAN`, `STARTDATETIME`, `ENDDATETIME`, and `MAXRECORDS`.
- The documented `MAXRECORDS` upper bound is 200, so this task should not keep requesting 250 records per DOC call.

## Implementation Notes

- Added shared GDELT request helpers in `src/railway_lakehouse/bronze/sources/gdelt_common.py`.
- Recent GDELT ingestion now retries HTTP 429, respects `Retry-After` when present, and caps `maxrecords` at 200.
- Historical DOC and GKG backfill now use the same retry helper.
- Historical CLI now exposes `--dry-run` and `--max-pages`; default CLI max pages is 1, and `--max-pages 0` explicitly opts into an unbounded scan.

## Evidence So Far

- `python -m pytest -q tests\test_bronze_characterization.py -k "gdelt or past_recordings"` initially failed for the new RED tests.
- After implementation, `python -m pytest -q tests\test_bronze_characterization.py -k "gdelt or past_recordings"` passed: 6 passed, 17 deselected.
- `python -m pytest -q tests\test_bronze_characterization.py` passed: 23 passed.

No live GDELT collector, scheduler, MinIO, Spark job, or long historical backfill was run.
