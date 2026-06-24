# GAP-020 s3 read-back tests plan

Date: 2026-06-24
Scope: GAP-020 only, plus the one-line GAP-014 UTF-8 parity fix required by the requested UTF-8 test.

## Local research

- Target code is `src/railway_lakehouse/pipeline.py`.
- `_list_bronze_files()` chooses the local `bronze_root` branch when present; otherwise it requires `lander.s3` and globs `bronze/<domain>/<source or *>/*/ingest_date=*/*`.
- `_is_data_file()` excludes `.meta.json` sidecars and applies the caller include predicate to the filename.
- `_read_tsv()` already opens non-`Path` paths through `lander.s3.open(path, "rb")` and infers gzip from `.gz`.
- `_read_text()` reads local paths with explicit UTF-8 but reads non-`Path` paths in text mode, which is the GAP-014 parity bug.
- Existing committed fixture bytes under `tests/fixtures/bronze/` provide the local-side parity reference and must remain read-only.
- `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`, `docs/PROGRESS_LOG.md`, and `.planning/COURSEWORK_PROGRESS.md` need updates when GAP-020 is closed.

## External research

- Official fsspec usage docs say `fsspec.filesystem("<protocol>")` returns a filesystem instance and filesystem methods include familiar operations such as `glob`, `cat`, and `open`: https://filesystem-spec.readthedocs.io/en/latest/usage.html
- Official fsspec API docs show `glob(path)` returns matched paths and `open(..., mode, compression, encoding)` supports binary/text modes and compression handling: https://filesystem-spec.readthedocs.io/en/latest/api.html
- Ref documentation search was attempted for fsspec API details, but the Ref provider returned "Not enough credits"; Context7 did not expose a core fsspec library entry. The official Read the Docs pages above are the fallback primary source.

## Approved implementation plan

1. Add `tests/test_pipeline_s3_readback.py` with `pytestmark = pytest.mark.unit`.
2. Build a fresh `fsspec.filesystem("memory")` fixture/helper that clears `fs.store` and `fs.pseudo_dirs` before seeding.
3. Seed `bronze/...` memory objects with:
   - Eurostat plain TSV plus `.meta.json`.
   - Eurostat gzip TSV plus `.meta.json`.
   - News RSS XML plus `.meta.json`.
   - News GDELT JSON plus `.meta.json`.
4. Write RED tests for the requested behaviors:
   - s3 glob/filtering returns `.tsv` and `.tsv.gz`, not sidecars.
   - no-backend object raises `ValueError` matching `bronze_root or s3`.
   - gzip TSV read via s3 branch yields the expected DataFrame.
   - local fixture TSV bytes and memory s3 bytes produce equal DataFrames.
   - local fixture news bytes and memory s3 bytes produce equal article dicts.
   - UTF-8-only text round-trips exactly through the s3 branch.
5. Run the focused new unit test before the production fix and confirm the UTF-8 test fails for the expected reason.
6. Apply the minimal `_read_text()` fix: open non-`Path` objects in binary mode and decode as UTF-8, matching the local branch.
7. Re-run the focused unit test, then `python -m pytest -q -m unit tests/test_pipeline_s3_readback.py`, `python -m pytest -q`, and `python -m compileall -q src tests`.
8. Update the gap register, dashboard/task docs, progress logs, and this research note with exact evidence.
9. Review the diff for scope, stage only intended files, commit, push `impl/gap-020`, and open a PR against `main`.

## Self-review and approval

- Scope is limited to the requested deterministic s3/memory read-back tests, one UTF-8 parity fix, and required documentation/dashboard/progress updates.
- No live MinIO, Docker, Ollama, Spark, network data collection, or Bronze fixture mutation is planned.
- Numeric stats are read back byte/value-identically through pandas; no LLM or numeric rewriting is introduced.
- Plan approved for implementation.

## Implementation evidence

- RED check before the UTF-8 fix: `python -m pytest -q tests/test_pipeline_s3_readback.py` failed with 5 passed, 1 failed; the failing case was the s3 `_read_text` branch attempting locale-sensitive text decode and raising `UnicodeDecodeError` on UTF-8 byte `0x98`.
- Focused post-fix check: `python -m pytest -q -m unit tests/test_pipeline_s3_readback.py` passed: 6 passed.
- Unit marker check: `python -m pytest -q -m unit` passed: 83 passed, 10 deselected.
- Full suite check: `python -m pytest -q` passed: 93 passed.
- Compile check: `python -m compileall -q src tests` passed.
- No Docker, MinIO, Ollama, Spark, live collectors, or network data collection was used.
