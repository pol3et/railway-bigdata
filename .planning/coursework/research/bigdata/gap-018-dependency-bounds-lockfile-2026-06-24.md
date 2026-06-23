# GAP-018 Dependency Bounds And Constraints Research

Date: 2026-06-24

Skill/workflow:
- Used `research-orchestrator`.
- Local files read first: `AGENTS.md`, `pyproject.toml`, `.gitignore`, `tests/test_infra_minio.py`, `README.md`, `docs/VERIFICATION.md`, `docs/GAP_REGISTER.md`, `docs/STATE_AND_ROADMAP.md`, `docs/TASKS.md`, `docs/GAP_TASKS.md`, `docs/index.html`, `docs/PROGRESS_LOG.md`, and `.planning/COURSEWORK_PROGRESS.md`.
- Routed external docs through MCP providers:
  - Ref search for Python `tomllib` was attempted, but Ref returned a credit-limit error.
  - Context7 `/websites/devdocs_io_python_3_14`: `tomllib.load` reads TOML from a readable binary file object, matching the planned `open("pyproject.toml", "rb")` test path. Source: https://devdocs.io/python~3.14/library/tomllib
  - Context7 `/websites/pip_pypa_io_en_stable`: pip supports applying constraints with `-c constraints.txt` / `--constraint constraints.txt`, including transitive dependency constraints. Sources: https://pip.pypa.io/en/stable/reference/requirements-file-format and https://pip.pypa.io/en/stable/topics/dependency-resolution

Ground truth commands:
- `python --version` -> Python 3.14.0.
- `python -m pip --version` -> pip 26.0.1 for Python 3.14.
- `python -m pip freeze` captured the active environment.
- A metadata closure over pyproject runtime roots plus pytest identified the runtime/test constraint set to record.

Validated core versions from the active environment:
- `pandas==3.0.3`
- `pyarrow==24.0.0`
- `requests==2.33.1`
- `s3fs==2024.6.1`
- `fsspec==2024.6.1`
- `aiobotocore==2.13.1`
- `botocore==1.34.131`
- `schedule==1.2.2`
- `pytest==9.0.3`

Runtime/test closure to lock:
- `aiobotocore==2.13.1`, `aiohappyeyeballs==2.6.2`, `aiohttp==3.13.5`, `aioitertools==0.13.0`, `aiosignal==1.4.0`, `attrs==26.1.0`, `botocore==1.34.131`, `certifi==2026.4.22`, `charset-normalizer==3.4.7`, `colorama==0.4.6`, `frozenlist==1.8.0`, `fsspec==2024.6.1`, `idna==3.13`, `iniconfig==2.3.0`, `jmespath==1.1.0`, `multidict==6.7.1`, `numpy==2.4.4`, `packaging==26.1`, `pandas==3.0.3`, `pluggy==1.6.0`, `propcache==0.5.2`, `pyarrow==24.0.0`, `Pygments==2.20.0`, `pytest==9.0.3`, `python-dateutil==2.9.0.post0`, `requests==2.33.1`, `s3fs==2024.6.1`, `schedule==1.2.2`, `six==1.17.0`, `tzdata==2026.2`, `urllib3==2.6.3`, `wrapt==1.17.3`, `yarl==1.24.2`.

Findings:
- `pyproject.toml` currently has `requires-python = ">=3.12"`, `pandas>=2.2`, `pyarrow>=15`, `requests>=2.31`, and `schedule>=1.2`; these need upper major bounds for GAP-018.
- The four S3 pins already use exact `==` versions and should stay unchanged.
- The `[project.optional-dependencies].spark` extra is owned by GAP-017 and must remain untouched.
- No `constraints.txt`, `requirements*.txt`, or `poetry.lock` is present, and `.gitignore` has no rule that hides a root constraints file.
- Existing unit-test style for repo config guards uses `pytestmark = pytest.mark.unit` and `ROOT = Path(__file__).resolve().parents[1]` in `tests/test_infra_minio.py`.
