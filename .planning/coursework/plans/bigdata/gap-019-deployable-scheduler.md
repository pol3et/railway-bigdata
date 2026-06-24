# GAP-019 Deployable Scheduler Implementation Plan

Goal: make the Bronze automatic-update scheduler fault-tolerant, deployable, and restart-safe without changing Bronze landing semantics.

Architecture: keep `RawLander` writes unchanged and add orchestration-only guards in `src/railway_lakehouse/bronze/run.py`. The scheduler preflights S3 before each batch, writes local run-evidence manifests under `output/evidence/scheduler/`, and lets Docker Compose or a host timer provide restart-safe cadence.

Tech stack: Python 3.12-3.14, `schedule>=1.2,<2`, `s3fs==2024.6.1`, Docker Compose, optional systemd timers or cron.

Global constraints:
- Do not edit `RawLander.land()` or Bronze write semantics.
- No Silver, Gold, LLM, Spark, or numeric-stat changes.
- Unit tests must use monkeypatch and `tmp_path`, with no Docker or network.
- Do not run `pip install` or `pip install -e`.

## Files
- Modify: `src/railway_lakehouse/bronze/run.py` for preflight, wrapper, manifests, and `_tick()`.
- Create: `tests/test_bronze_scheduler.py` for deterministic unit coverage.
- Modify: `docker-compose.yml` and create `Dockerfile` for a restartable scheduler service.
- Create: `docs/OPERATIONS.md`; modify `README.md`, `docs/CODEMAP.md`, `docs/GAP_REGISTER.md`, `docs/TASKS.md`, `docs/index.html`.
- Update: `.planning/coursework/research/bigdata/gap019-deployable-scheduler-spec-2026-06-24.md`, `docs/PROGRESS_LOG.md`, `.planning/COURSEWORK_PROGRESS.md`.

## Tasks
- [x] Write failing scheduler unit tests for degraded connection errors, `_storage_reachable()` false-on-error, `_tick()` swallowing exceptions, and success manifest `ok`.
- [x] Implement minimal scheduler wrapper code: `_storage_reachable()`, `_run_batch()`, JSON manifest writer, `_tick()`, and resilient `schedule` mode.
- [x] Add deployable Compose scheduler service and minimal Docker image.
- [x] Document Compose and native systemd/cron operation plus the one-line runbook.
- [x] Update GAP/dashboard/status docs for GAP-019 closure.
- [ ] Run `python -m pytest -q -m unit tests/test_bronze_scheduler.py`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Run `git diff --check`.
- [ ] Commit, push `impl/gap-019`, and open a PR against `main`.

## Self Review
- Spec coverage: every GAP-019 Definition-of-Done item maps to a task above; GAP-005 source scheduling remains out of scope.
- Placeholder scan: no TODO/TBD/placeholders remain in this plan.
- Type consistency: tests and implementation use the same local interfaces: `_storage_reachable() -> bool`, `_run_batch(...) -> dict`, `_tick(...) -> bool`.

Approved: self-reviewed and approved for inline execution on 2026-06-24.
