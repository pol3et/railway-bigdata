# Merge Strategy And Gap Register

Date: 2026-06-21

Purpose: define the cleanest path to merge the current dump into one GitHub-ready project and record whether the code currently works end to end.

## Short Answer

The code is mostly aimed at the same course-project goal: a railway data lakehouse with Bronze collection, Silver preprocessing/extraction, and Gold analysis features.

It is not working end to end yet.

Evidence:

- `python -m compileall bigdata\course_proj` passed, so files are syntactically valid.
- Import check for `railway_lakehouse.pipeline` failed because local Python has no `pandas`.
- Import check for `bronze.run` failed because local Python has no `s3fs`.
- `railway_lakehouse/pipeline.py` still contains explicit `NotImplementedError` stubs for Bronze reads.
- New source adapters under `railway_lakehouse/bronze/sources/` are not wired into the existing `bronze/bronze/run.py`.

## External Guidance Used

Research was routed through `research-orchestrator`.

- Python Packaging User Guide via Context7:
  - https://packaging.python.org/en/latest/guides/writing-pyproject-toml
  - https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout
  - Finding: `pyproject.toml` is the standard project configuration file, and `src/` layout helps prevent accidental imports from the working tree.
- GitHub Docs via Context7:
  - https://docs.github.com/en/get-started/git-basics/ignoring-files
  - https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors
  - Finding: commit repo-local `.gitignore` rules and contribution docs so collaborators get the same repository behavior.
- Spark docs via Context7 in the earlier intake:
  - https://spark.apache.org/docs/3.5.6/api/python/getting_started/testing_pyspark.html
  - https://spark.apache.org/docs/3.5.6/structured-streaming-kafka-integration.html
  - Finding: Spark work should have explicit `SparkSession` entrypoints and documented batch/streaming reads/writes.

## Recommended Merge Strategy

Use one GitHub repository rooted at `bigdata/course_proj`, not the full coursework tree.

Target shape:

```text
bigdata/course_proj/
  README.md
  AGENTS.md
  TASK.md
  pyproject.toml
  .gitignore
  CONTRIBUTING.md
  docs/
  src/
    railway_lakehouse/
      bronze/
        config.py
        lander.py
        run.py
        sources/
      silver/
      gold/
      spark_jobs/
      pipeline.py
  tests/
  output/
    evidence/
    report/
    presentation/
    runtime/       # ignored
```

Why this is cleanest:

- One import root: `railway_lakehouse`.
- One package manager config: `pyproject.toml`.
- One test root: `tests/`.
- One docs root: `docs/`.
- One output policy: public evidence in `output/evidence`, scratch in `output/runtime`.
- No competing `bronze/bronze` vs `railway_lakehouse/bronze` package paths.

## Merge Order

### 1. Freeze First

Before moving code, add:

- `pyproject.toml` with current dependencies.
- `.gitignore` for bytecode, env files, local outputs, and runtime scratch.
- tiny unit tests for pure Silver/Gold functions.
- one synthetic Bronze/Silver/Gold smoke fixture.

Goal: know what breaks because of the move, not because it was already broken.

### 2. Consolidate Bronze

Move existing operational Bronze code:

- from `bronze/bronze/config.py`
- from `bronze/bronze/lander.py`
- from `bronze/bronze/run.py`
- from `bronze/bronze/sources/{eurostat,worldbank,gdelt,rss_media}.py`

into:

- `src/railway_lakehouse/bronze/`

Then add current new adapters:

- `ksh.py`
- `statistik_austria.py`
- `uic.py`
- `past_recordings.py`

Wire them in one scheduler/orchestrator.

### 3. Normalize Imports

Use package-qualified imports:

```python
from railway_lakehouse.bronze.lander import RawLander
from railway_lakehouse.silver.stats import merge as stats_merge
from railway_lakehouse.gold.run import build_from_silver
```

Avoid depending on the current working directory.

### 4. Wire Storage Boundaries

Implement the two current stubs in `pipeline.py`:

- `_read_bronze_eurostat(...)`
- `_read_bronze_news(...)`

Also decide where Silver writes its outputs so Gold can load them without in-memory handoff only.

### 5. Add Spark Jobs

Add `src/railway_lakehouse/spark_jobs/`.

Minimum useful jobs:

- read Gold Parquet,
- compute row/source/feature coverage,
- produce country-year trend tables,
- write analysis outputs under `output/evidence/` or a documented Gold path.

### 6. Publish Work Split

Create GitHub issues or a simple `docs/WORK_SPLIT.md` from the gap register below.

## Gap Register

| Gap | Evidence | Owner |
|---|---|---|
| Missing project dependency manifest | No `pyproject.toml` or `requirements.txt` under `bigdata/course_proj`; import checks miss `pandas` and `s3fs`. | DevEx / packaging |
| Import ambiguity | Bronze imports work only if `bigdata/course_proj/bronze` is on `PYTHONPATH`; Silver/Gold imports assume `railway_lakehouse` is on `PYTHONPATH`. | DevEx / packaging |
| Duplicate Bronze locations | Existing core is under `bronze/bronze`; intended add-ons are under `railway_lakehouse/bronze/sources`. | Bronze owner |
| End-to-end pipeline not wired | `pipeline.py` raises `NotImplementedError` for Bronze reads. | Integration owner |
| New source adapters not scheduled | `bronze/bronze/run.py` imports only Eurostat, World Bank, GDELT, and RSS. | Bronze/source owner |
| Silver storage boundary missing | `silver/run.py` expects supplied frames/articles and logs that MinIO reads must be wired. | Silver owner |
| Gold storage boundary missing | `gold/run.py` says Silver loads must be wired. | Gold owner |
| No tests | No `tests/` directory under project. | QA owner |
| No Spark job in current tree | Current project has pandas/lakehouse logic but no current Spark entrypoint under `bigdata/course_proj`. | Spark owner |
| No generated dataset evidence | No pre-existing output evidence found before documentation scaffold. | Data/output owner |
| Report/presentation not started | Only organization notes exist under `output/project-organization`. | Report owner |

## Work Split For Classmates

1. Packaging/Repo Owner:
   - create `pyproject.toml`, `.gitignore`, `CONTRIBUTING.md`;
   - make imports installable;
   - add base test command.

2. Bronze Owner:
   - consolidate Bronze code;
   - wire all source adapters;
   - keep raw landing contract unchanged.

3. Silver Owner:
   - implement readers from Bronze storage;
   - add crosswalk cache review artifact;
   - test stats/news validators.

4. Gold Owner:
   - load Silver outputs;
   - produce Gold Parquet from fixture and real data.

5. Spark Owner:
   - add Spark jobs and evidence output.

6. Report Owner:
   - turn generated outputs into report and presentation.

## Decision

Do not merge by copying files into each other ad hoc.

Merge by first making the project installable and testable, then moving Bronze into the single `railway_lakehouse` package, then wiring storage and Spark evidence.
