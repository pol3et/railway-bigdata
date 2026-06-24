### GAP-019 — Deployable, restart-safe, fault-tolerant Bronze scheduler

`MID` · level **ops** · effort **M** · depends on: none (pure orchestration/ops; `schedule>=1.2` already a runtime dep; MinIO compose already present). Research: `.planning/coursework/research/bigdata/gap019-deployable-scheduler-spec-2026-06-24.md`.

**Build:** Make the Bronze "automatic updates" scheduler (1) fault-tolerant — a MinIO-unreachable boot or a failing batch degrades (logs + writes a degraded run-evidence manifest) instead of crashing the loop, and (2) deployable + restart-safe — a documented host (docker-compose `scheduler` service AND a systemd-timer/cron alternative) keeps cadence across restarts, with a one-line runbook.

**Context.** `src/railway_lakehouse/bronze/run.py` is the orchestrator (modes `stats|news|all|schedule`). In `schedule` mode (run.py:54-62) it runs both batches once at boot, registers `schedule.every().sunday.at("02:00")` (news) / `schedule.every(365).days` (stats), then loops `run_pending(); sleep(60)`. Two defects:
- **Crashes on MinIO-unreachable boot.** `run_stats()`/`run_news()` (run.py:28-42) each construct `RawLander()` eagerly; `RawLander.__init__` (lander.py:44-54) calls `self.s3.exists(BRONZE_BUCKET)` (lander.py:52) — a network round-trip. MinIO down → botocore connection error raised here, unhandled, killing the whole process at boot. Nothing in run.py catches it; one bad batch also kills the loop.
- **Restart-unsafe with no deployable host.** Cadence lives only in the `schedule` library's in-process job list (confirmed by schedule docs: no persistence, no missed-run recovery across restarts). There is no compose/systemd/cron host keeping cadence; `docker-compose.yml` ships MinIO + `createbuckets` only — no scheduler service.

This is **pure ops/orchestration** — Hard Rules: NO Bronze write-semantics change (the lander stays append/accumulate, bytes-then-meta), NO Silver/Gold/LLM/numbers. Degrade = skip the batch + log + record evidence; never crash the loop; never partially write.

**Reuse, don't invent.** `scripts/minio_smoke.py:61-136` is the existing fail-soft + evidence-manifest idiom (try/except wraps work, writes a `status: failed`/degraded manifest with a hint instead of a traceback). `src/railway_lakehouse/bronze/live_check.py:127-145` is the per-source try/except collector + `write_manifest` JSON writer. Mirror these.

**Steps.**
1. Read `bronze/run.py` (whole), `bronze/lander.py:44-54` (the crash site), `bronze/config.py:11-16` (S3 settings), `scripts/minio_smoke.py` (fail-soft idiom), `bronze/live_check.py` (`write_manifest`), `docker-compose.yml`, and `docs/CODEMAP.md:40` (run.py documented).
2. Add a cheap `_storage_reachable() -> bool` preflight: construct the `s3fs.S3FileSystem` from `bronze.config` and `try: fs.exists(BRONZE_BUCKET); return True except Exception as exc: logger.warning(...); return False`. (Do NOT import-time construct `RawLander`.)
3. Wrap each batch so it degrades, never raises: a helper `_run_batch(name, fn, *, evidence_dir)` that, if storage is unreachable OR `fn()` raises, logs a warning and writes a degraded run-evidence manifest (`status: "degraded"`, `storage_reachable: false`/`error: <repr>`, UTC timestamp, batch name) via a small JSON writer (reuse `write_manifest` style) and returns a status, instead of propagating. On success it writes `status: "ok"`. Default evidence dir under `output/evidence/scheduler/` (configurable).
4. Make `run_stats()`/`run_news()` callable through the wrapper (keep their one-off CLI behavior). Make the `schedule` loop body resilient: wrap `schedule.run_pending()` in try/except so one bad batch never kills cadence; keep `sleep(60)`. Boot batch runs through the same wrapper (no crash on MinIO-down boot).
5. Keep CLI modes working (`stats|news|all|schedule`); preserve the `__doc__`/usage fallback. Optionally add a bounded `--once`-style path only if trivial — do not widen scope.
6. **Deployable host (compose):** add a `scheduler` service to `docker-compose.yml`: builds/runs the project image (add a minimal `Dockerfile` if none exists, installing the package + `[ ]` runtime deps), command `python -m railway_lakehouse.bronze.run schedule`, `depends_on: minio` (note: compose `depends_on` only waits for container start, not readiness — the fail-soft preflight is what actually protects boot), `restart: unless-stopped`, env wired from `.env` (S3_ENDPOINT pointing at the compose `minio` service, e.g. `http://minio:9000`). Keep MinIO creds as the existing local-only defaults.
7. **Native alternative + runbook:** document a systemd-timer (or cron) alternative that runs `python -m railway_lakehouse.bronze.run all` on the stats/news cadence (restart-safe because the host re-fires the timer), and a one-line runbook. Put the runbook in `README.md` and a new `docs/OPERATIONS.md` (scheduler deploy + degrade behavior + how to read the run-evidence manifest). Keep `docs/CODEMAP.md` accurate.
8. **Deterministic test** `tests/test_bronze_scheduler.py`, `pytestmark = pytest.mark.unit`, no Docker/network (monkeypatch + `tmp_path` + fixed clock style of `tests/test_infra_minio.py`/`tests/test_bronze_live_check.py`):
   - monkeypatch `RawLander` (or the batch fn) to raise a connection error; assert the wrapped batch **does not raise**, returns a degraded status, and writes a manifest with `status == "degraded"`/`storage_reachable == false` under `tmp_path`.
   - assert `_storage_reachable()` returns `False` (not raises) when the fs `exists` call raises.
   - assert the schedule loop body swallows a batch exception (e.g. patch `schedule.run_pending` to raise once, run one iteration via a seam, assert no propagation) — refactor the loop body into a testable `_tick()`-style function if needed.
   - a success-path test: batch fn succeeds → manifest `status == "ok"`.
9. Run `python -m pytest -q -m unit tests/test_bronze_scheduler.py` then full `python -m pytest -q`; both green. `python -m compileall -q src tests` clean. `git diff --check` clean.
10. Append a `docs/GAP_REGISTER.md` Test Failure Mapping row (exact command + result + `GAP-019`) and flip GAP-019 toward `closed` with evidence + the runbook line. Sync `docs/TASKS.md` + `docs/index.html` (Wave 4 "deployable automatic updates" / Contract C) if state advances.

**Files to touch:** `src/railway_lakehouse/bronze/run.py` (preflight + degrade wrapper + resilient loop + testable seam) · `docker-compose.yml` (add `scheduler` service) · `Dockerfile` (new, minimal, only if none exists) · `docs/OPERATIONS.md` (new — deploy + degrade runbook) · `README.md` (one-line runbook) · `docs/CODEMAP.md` (keep run.py description accurate) · `tests/test_bronze_scheduler.py` (new) · `docs/GAP_REGISTER.md` (mapping row + GAP-019 status). Do NOT change `bronze/lander.py` write semantics.

**Definition of Done (contract).**
- [ ] A MinIO-unreachable boot **degrades** (warns + writes a `status: "degraded"` run-evidence manifest) instead of raising; `_storage_reachable()` returns `False` rather than crashing.
- [ ] The `schedule` loop body is wrapped so one failing batch never kills cadence.
- [ ] A deployable host exists: a `scheduler` service in `docker-compose.yml` (`depends_on: minio`, `restart: unless-stopped`, runs `bronze.run schedule`) AND a documented systemd-timer/cron alternative; a one-line runbook is recorded in `README.md` + `docs/OPERATIONS.md`.
- [ ] Bronze write semantics are unchanged (lander still append/accumulate, bytes-then-meta); no Silver/Gold/LLM/numeric changes.
- [ ] New `tests/test_bronze_scheduler.py` (`pytest.mark.unit`, no Docker/network) covers: degraded batch on connection error (no raise + degraded manifest), `_storage_reachable()` false-on-error, loop body swallows a batch exception, success path manifest `ok`.
- [ ] `python -m pytest -q -m unit tests/test_bronze_scheduler.py` green; full `python -m pytest -q` green; `python -m compileall -q src tests` clean; `git diff --check` clean.
- [ ] `docs/GAP_REGISTER.md` mapping row + GAP-019 status/evidence updated; dashboard synced if state changed.

**Verify:** `python -m pytest -q -m unit tests/test_bronze_scheduler.py  (then full gate: python -m pytest -q)`

**Pitfalls.**
- Do NOT touch `RawLander.land()` / write semantics — only the scheduler's construction/error-handling and a preflight change. Raw Bronze stays append/accumulate.
- `depends_on` does NOT wait for MinIO readiness (only container start) — the fail-soft preflight is the real protection; do not rely on `depends_on` to prevent the connection error.
- `schedule` has no cross-restart persistence (by design) — restart-safety must come from the host (`restart: unless-stopped` / systemd timer re-firing), not from in-process state. Don't try to persist `schedule` state.
- Keep the degrade path from partially writing: skip the batch entirely on unreachable storage; the lander already writes bytes-then-meta within a batch.
- Tests must be deterministic: monkeypatch the fs/lander and the clock; never hit the network or Docker; write only under `tmp_path`. No live MinIO required for the unit suite.
- Evidence/output discipline: scheduler run-evidence manifests go under `output/evidence/scheduler/` (or tmp in tests) — never the repo root.
- Don't break the existing one-off CLI modes or the `__doc__` usage fallback.
