# GAP-018 Dependency Bounds And Constraints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound the validated pandas/pyarrow/runtime major windows, commit a reproducible constraints file, and add an offline guard test for environment drift.

**Architecture:** Keep this as an ops-only change: dependency metadata, constraints, one deterministic unit test, and status/docs updates. The guard test imports installed pandas/pyarrow, reads `pyproject.toml` with stdlib `tomllib`, and checks `constraints.txt`; it does not touch Bronze/Silver/Gold data paths.

**Tech Stack:** Python 3.14.0, pytest, stdlib `tomllib`, pandas 3.0.3, pyarrow 24.0.0, pip constraints.

---

## Files

- Modify: `pyproject.toml`
- Create: `constraints.txt`
- Create: `tests/test_env_versions.py`
- Modify: `README.md`
- Modify: `docs/VERIFICATION.md`
- Modify: `docs/GAP_REGISTER.md`
- Modify: `docs/STATE_AND_ROADMAP.md`
- Modify: `docs/TASKS.md`
- Modify: `docs/index.html`
- Modify: `docs/PROGRESS_LOG.md`
- Modify: `.planning/COURSEWORK_PROGRESS.md`
- Create: `.planning/coursework/research/bigdata/gap-018-dependency-bounds-lockfile-2026-06-24.md`

## Task 1: RED Guard Test

- [ ] Add `tests/test_env_versions.py` with `pytestmark = pytest.mark.unit`, `ROOT = Path(__file__).resolve().parents[1]`, helpers for numeric version parsing and bounds checks, and assertions for installed pandas/pyarrow, pyproject dependency bounds, `requires-python`, and constraints pins.
- [ ] Run `python -m pytest -q tests/test_env_versions.py`.
- [ ] Expected result before metadata/constraints edits: failure because `pyproject.toml` lacks `<4` / `<25` and `constraints.txt` does not exist.

## Task 2: Dependency Metadata And Constraints

- [ ] Update only `[project]` dependency lines in `pyproject.toml`: `requires-python >=3.12,<3.15`, `pandas>=2.2,<4`, `pyarrow>=15,<25`, `requests>=2.31,<3`, `schedule>=1.2,<2`; leave S3 pins and `[spark]` unchanged.
- [ ] Add root `constraints.txt` with the Python/version/header and exact `==` pins for the active runtime/test closure captured from `python -m pip freeze`.
- [ ] Re-run `python -m pytest -q tests/test_env_versions.py` and expect it to pass.

## Task 3: Docs And Dashboard Sync

- [ ] Update README Quickstart with `python -m pip install -e ".[test]" -c constraints.txt` and note why `-c` matters.
- [ ] Update `docs/VERIFICATION.md` Safe Checks Now with the constrained install command and dry-run verification line.
- [ ] Update `docs/GAP_REGISTER.md` GAP-018 status/evidence and add a Test Failure Mapping row for `python -m pytest -q tests/test_env_versions.py`.
- [ ] Update `docs/STATE_AND_ROADMAP.md`, `docs/TASKS.md`, and `docs/index.html` to reflect GAP-018 completion without claiming GAP-017/Spark completion.
- [ ] Append handoff entries to `docs/PROGRESS_LOG.md` and `.planning/COURSEWORK_PROGRESS.md`.

## Task 4: Verification, Commit, PR

- [ ] Run `python -m pytest -q tests/test_env_versions.py`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Run `python -m pip install --dry-run -e ".[test]" -c constraints.txt` and confirm it keeps pandas 3.0.3 / pyarrow 24.0.0.
- [ ] Run `git diff --check`.
- [ ] Commit on `impl/gap-018`, push to origin, open a PR against `main`, and verify mergeability plus dashboard reminder/check status.

## Self-Review

- Spec coverage: every GAP-018 DoD item maps to Tasks 1-4. GAP-017 `[spark]` remains out of scope.
- Placeholder scan: no placeholders or broad follow-up work.
- Type/API consistency: guard helpers stay dependency-free; TOML parsing uses stdlib `tomllib.load` with binary mode.
- Approval: plan is self-approved for execution on 2026-06-24.
