# Test-First Integration Plan

Date: 2026-06-21

Goal: turn `bigdata/course_proj` into a GitHub-ready railway lakehouse repo with documentation, tests, usage instructions, real launch evidence, and a gap register that classmates can split by ownership.

## Guiding Rule

Write tests before large integration moves.

Some tests may fail at first. That is acceptable if each failure becomes a documented gap with:

- gap ID,
- owner workstream,
- failing command/test,
- expected behavior,
- closure criteria,
- verification command.

## Phase 1 - Repo Hygiene And Test Harness

Objective: make the project installable and testable before moving files.

Tasks:

1. Add `pyproject.toml`.
   - Package name: `railway-lakehouse` or similar.
   - Python version: choose one supported version and document it.
   - Dependencies from imports: `pandas`, `pyarrow`, `requests`, `s3fs`, `schedule`.
   - Optional groups: `test`, `spark`, `ollama`, `dev`.
2. Add `.gitignore`.
   - Ignore `__pycache__/`, `.pytest_cache/`, `.venv/`, `.env`, local bucket data, `output/runtime/`, large raw dumps.
3. Add `CONTRIBUTING.md`.
   - Explain branches, tests, gap IDs, and evidence requirements.
4. Add pytest config.
   - Use conventional `tests/test_*.py`.
   - Add markers: `unit`, `integration`, `live`, `spark`, `slow`.
5. Add a first `tests/README.md`.
   - Explain how to run deterministic tests versus live checks.

Verification:

```bash
python -m pip install -e ".[test]"
python -m pytest -q
```

Expected first outcome:

- Some imports may fail until dependencies and package paths are fixed.
- Record failures in `docs/GAP_REGISTER.md`.

## Phase 2 - Characterization Tests Before Moving Code

Objective: capture what currently works.

Add tests around current code without reorganizing it yet:

- Bronze:
  - `build_meta_dict` computes byte size, checksum, and run id.
  - Eurostat `discover_rail_datasets` selects rail datasets and excludes false positives.
  - World Bank `discover_rail_indicators` keeps known rail fallbacks.
  - GDELT query builder includes rail terms and country restriction.
- Silver stats:
  - `read_eurostat_tsv` melts years and extracts numeric values.
  - `build_crosswalk` maps English labels by rule with LLM disabled.
  - `merge_sources` drops unmapped rows and keeps provenance.
- Silver news:
  - `validate_news_feature` coerces invalid model output safely.
  - `extract_article` uses mocked Ollama output.
- Gold:
  - conflict resolution honors source priority.
  - stats pivot produces `(geo, year)` rows.
  - news aggregation fills count-like columns with zero.
  - Gold writer writes Parquet to `tmp_path`.

Verification:

```bash
python -m pytest -q -m unit
```

Gap rule:

- A failing characterization test is a valid finding.
- Do not delete it just to get green tests.
- If the current intended behavior is unclear, move it to a named gap and ask for owner decision.

## Phase 3 - Create One Package Layout

Objective: remove competing import roots.

Target:

```text
src/railway_lakehouse/
  bronze/
  silver/
  gold/
  spark_jobs/
  pipeline.py
```

Move order:

1. Create `src/railway_lakehouse/`.
2. Move existing `railway_lakehouse/silver` and `railway_lakehouse/gold`.
3. Move `railway_lakehouse/pipeline.py`.
4. Move `bronze/bronze/{config.py,lander.py,run.py,sources/}` into `src/railway_lakehouse/bronze/`.
5. Merge source adapters from `railway_lakehouse/bronze/sources/` into the same source package.
6. Normalize imports to `railway_lakehouse.*`.
7. Leave temporary compatibility notes only if needed, not duplicate executable packages.

Verification:

```bash
python -m pytest -q -m unit
python -c "import railway_lakehouse; import railway_lakehouse.pipeline"
```

## Phase 4 - Local Fixture E2E

Objective: prove Bronze -> Silver -> Gold without network.

Build tiny fixtures:

- one Eurostat-like TSV fixture,
- one GDELT/RSS-like news fixture,
- one mocked Ollama extraction result,
- local filesystem or fake S3 storage adapter.

Test:

```bash
python -m pytest -q -m integration
```

Expected output:

- Gold Parquet under `tmp_path` in tests.
- Optional copied evidence under `output/evidence/fixture-e2e/` if the test is promoted to a documented smoke command.

## Phase 5 - Storage And Services E2E

Objective: prove the real storage path.

Tasks:

1. Add or restore Docker Compose for MinIO and optional Ollama/Spark services.
2. Configure local `.env.example` without secrets.
3. Implement Bronze reads in `pipeline.py`.
4. Implement Silver persistence and Gold load path.
5. Run a bounded E2E:
   - small Eurostat pull or fixture upload,
   - small news pull or fixture upload,
   - Silver transform,
   - Gold output.

Verification:

```bash
python -m railway_lakehouse.pipeline --news 10 --out output/evidence/live/railway_ml.parquet
```

If live APIs or services fail, record the exact error in `docs/GAP_REGISTER.md`.

## Phase 6 - Spark / Big Data Evidence

Objective: satisfy the Big Data requirement with real job evidence.

Minimum Spark job:

- read Gold Parquet,
- compute coverage metrics,
- compute country-year trend tables,
- write outputs to `output/evidence/spark/`.

Verification:

```bash
python -m railway_lakehouse.spark_jobs.coverage --input output/evidence/live/railway_ml.parquet --out output/evidence/spark/
```

Evidence to capture:

- Spark version,
- command,
- input row count,
- output row count,
- output files,
- warnings/failures.

## Phase 7 - GitHub-Ready Project

Objective: make classmates productive immediately after clone.

Required docs:

- `README.md` with quickstart.
- `AGENTS.md` with agent routing.
- `TASK.md` with course criteria.
- `CONTRIBUTING.md` with gap workflow.
- `docs/GAP_REGISTER.md`.
- `docs/WORK_SPLIT.md`.
- `docs/VERIFICATION.md`.
- `.env.example`.

Optional GitHub files:

- `.github/workflows/tests.yml`
- `.github/ISSUE_TEMPLATE/gap.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `CODEOWNERS`

## Gap Closure Contract

A gap is closed only when:

1. the code or docs changed,
2. a unit/integration/live/Spark test verifies it,
3. the verification command and output are recorded,
4. `docs/GAP_REGISTER.md` marks the gap closed,
5. report/presentation claims are updated if affected.

## First Five Tasks For The Next Agent

1. Create `docs/GAP_REGISTER.md` from `docs/MERGE_STRATEGY.md`.
2. Add `pyproject.toml`, `.gitignore`, and `CONTRIBUTING.md`.
3. Add pytest config and initial unit tests for pure functions.
4. Run tests; keep failures visible and convert them into gap IDs.
5. Only then start the `src/railway_lakehouse` package merge.
