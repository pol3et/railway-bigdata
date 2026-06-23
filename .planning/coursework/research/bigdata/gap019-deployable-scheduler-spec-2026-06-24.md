# GAP-019 — Deployable, restart-safe, fault-tolerant Bronze scheduler (spec research)

Date: 2026-06-24
Skill: research-orchestrator (local-materials-first lens; no external MCP fetch
needed — the gap is fully grounded in repo files).
MCP providers routed: none required this pass (all evidence is in-repo source +
docs). External scheduling docs (systemd timer / docker compose restart) are
standard and already reflected in `docs/STATE_AND_ROADMAP.md` conventions.

## Task
Write an implementation-ready spec for GAP-019: the Bronze "automatic updates"
scheduler keeps cadence only in-memory, has no deployable host, and crashes on a
MinIO-unreachable startup with no error handling.

## Local files read (with the load-bearing lines)
- `docs/GAP_REGISTER.md` — GAP-019 row (line 47); closure criterion: documented
  restart-safe cadence (cron/systemd timer or compose scheduler) + startup ingest
  wrapped so a MinIO-unreachable boot degrades instead of crashing + runbook line.
- `docs/TASKS.md` — GAP-019 sits in Wave 4 ("deployable automatic updates");
  Contract C wants "a scheduled run lands fresh Bronze (automatic-updates demo)".
  Slug `bronze/scheduler-wiring` (GAP-005) is the sibling orchestration task.
- `docs/STATE_AND_ROADMAP.md` — "automatic updates" is a graded course
  requirement; scheduler wiring is "pure orchestration".
- `src/railway_lakehouse/bronze/run.py:28-65` — the scheduler. `run_stats()`
  (l.28-34) and `run_news()` (l.37-42) each construct `RawLander()` eagerly;
  `main()` `schedule` mode (l.54-62) runs both once at boot, then registers
  `schedule.every().sunday.at("02:00")` / `schedule.every(365).days` and loops
  `schedule.run_pending(); time.sleep(60)`. All cadence state is in-memory.
- `src/railway_lakehouse/bronze/lander.py:44-54` — `RawLander.__init__` builds
  `s3fs.S3FileSystem(...)` then calls `self.s3.exists(BRONZE_BUCKET)` (l.52) — a
  network round-trip to MinIO. MinIO down => botocore connection error raised
  here, unhandled, crashing the whole `schedule` process at boot.
- `src/railway_lakehouse/bronze/config.py:11-16` — S3 settings from env
  (`S3_ENDPOINT` default `http://localhost:9000`, key/secret/bucket).
- `docker-compose.yml` — MinIO + `createbuckets` only; no scheduler service.
  `restart: unless-stopped` already used for `minio`.
- `scripts/minio_smoke.py:61-136` — the existing pattern for a bounded,
  evidence-writing, fail-soft S3 round-trip (try/except wraps `main`, writes a
  `status: failed` manifest with a hint instead of an unhandled traceback). This
  is the degradation model to mirror.
- `src/railway_lakehouse/bronze/live_check.py:45-182` — `LocalBronzeLander` +
  `run_live_check` + `write_manifest`: the per-source try/except collector
  pattern (l.127-145) and JSON manifest writer to reuse for run evidence.
- `tests/test_infra_minio.py` + `tests/test_bronze_live_check.py` — the
  deterministic, no-Docker/no-network test style (monkeypatch, tmp_path, fixed
  clock, `pytestmark = pytest.mark.unit`) the new test must follow.
- `pyproject.toml:11-20` — `schedule>=1.2` is a real runtime dep; markers
  unit/integration/live registered (l.41-47).
- `WIRING.md` (repo root) — GAP-005 scheduler note.
- `docs/CODEMAP.md:40` — `run.py` documented as the orchestrator with
  stats/news/all/schedule modes (keep this accurate after the change).

## Key findings
1. Crash path is exact: boot of `schedule` mode -> `run_stats()` ->
   `RawLander()` -> `self.s3.exists(BRONZE_BUCKET)` (lander.py:52) raises when
   MinIO is unreachable; nothing in run.py catches it.
2. Restart-unsafe: the only cadence record is the `schedule` library's in-process
   job list; a container/host restart re-runs the boot batch and otherwise loses
   timing. There is no host (systemd/cron/compose) keeping cadence across
   restarts.
3. Hard-rule safe fix surface: this is pure ops/orchestration — no Bronze write
   semantics change (lander stays append/accumulate), no Silver/Gold, no LLM,
   no numbers. Degrade = skip the batch + log + record evidence, never crash the
   loop; never partially write (the lander already writes bytes-then-meta).
4. The repo already has the exact fail-soft + evidence-manifest idiom in
   `scripts/minio_smoke.py` and `live_check.write_manifest` — reuse, don't invent.

## Recommended shape
- Add a `_storage_reachable()` preflight (cheap `s3fs.exists(bucket)` in a
  try/except) and wrap each batch so an unreachable MinIO logs a warning, writes
  a degraded run-evidence manifest, and returns instead of raising.
- Add `--once` semantics already present; make `schedule` mode resilient (loop
  body try/except, so one bad batch never kills cadence).
- Add a deployable host: a `scheduler` service in docker-compose (depends_on
  minio, `restart: unless-stopped`) running `python -m railway_lakehouse.bronze.run schedule`,
  AND a documented systemd-timer / cron alternative for native hosts. Document a
  one-line runbook in README + a new `docs/OPERATIONS.md` (or VERIFICATION runbook).
- Deterministic test: monkeypatch `RawLander` to raise a connection error, assert
  `run_stats()`/`run_news()` (or the wrapped batch) degrade (no raise) and a
  manifest with `status: "degraded"`/`storage_reachable: false` is written under
  a tmp_path; a second test asserts the schedule loop body swallows a batch
  exception.

## Evidence
Planning/spec pass only; no code, scheduler, MinIO, Spark, or live collectors run.
