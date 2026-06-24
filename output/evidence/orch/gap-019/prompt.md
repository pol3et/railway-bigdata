You are implementing one task in the railway-lakehouse big-data course project.
The repo's `AGENTS.md` is authoritative and auto-loaded — follow its Hard Rules
(raw Bronze immutable; numeric stat merges deterministic, never LLM-rewritten;
outputs under `output/`; no fabricated data; tests must not depend on `coursework/`
data — use `tmp_path`/fixtures; keep the live dashboard in sync).

## Your task: GAP-019

Implement it EXACTLY as written below. Do not widen scope.

### GAP-019 — Deployable, restart-safe, fault-tolerant Bronze scheduler

`MID` · level **ops** · effort **M** · depends on: none (pure orchestration/ops; `schedule>=1.2` already a runtime dep; MinIO compose already present). Research: `.planning/coursework/research/bigdata/gap019-deployable-scheduler-spec-2026-06-24.md`.

**Build:** Make the Bronze "automatic updates" scheduler (1) fault-tolerant — a MinIO-unreachable boot or a failing batch degrades (logs + writes a degraded run-evidence manifest) instead of crashing the loop, and (2) deployable + restart-safe — a documented host (docker-compose `scheduler` service AND a systemd-timer/cron alternative) keeps cadence across restarts, with a one-line runbook.

**Context.** `src/railway_lakehouse/bronze/run.py` is the orchestrator (modes `stats|news|all|schedule`). In `schedule` mode (run.py:54-62) it runs both batches once at boot, registers `schedule.every().sunday.at("02:00")` (news) / `schedule.every(365).days` (stats), then loops `run_pending(); sleep(60)`. Two defects:
- **Crashes on MinIO-unreachable boot.** `run_stats()`/`run_news()` (run.py:28-42) each construct `RawLander()` eagerly; `RawLander.__init__` (lander.py:44-54) calls `self.s3.exists(BRONZE_BUCKET)` (lander.py:52) — a network round-trip. MinIO down → botocore connection error raised here, unhandled, killing the whole process at boot. One bad batch also kills the loop.
- **Restart-unsafe with no deployable host.** Cadence lives only in the `schedule` library's in-process job list (schedule docs confirm: no persistence, no missed-run recovery across restarts — https://schedule.readthedocs.io/en/stable/faq.html). No compose/systemd/cron host keeps cadence; `docker-compose.yml` ships MinIO + `createbuckets` only.

This is **pure ops/orchestration** — Hard Rules: NO Bronze write-semantics change (the lander stays append/accumulate, bytes-then-meta), NO Silver/Gold/LLM/numbers. Degrade = skip the batch + log + record evidence; never crash the loop; never partially write.

**Reuse, don't invent.** `scripts/minio_smoke.py:61-136` is the existing fail-soft + evidence-manifest idiom. `src/railway_lakehouse/bronze/live_check.py:127-145` is the per-source try/except collector + `write_manifest` JSON writer. Mirror these. For docker-compose restart policy: `restart: unless-stopped` is the correct long-running-service policy and `depends_on` only waits for container start, not readiness (https://docs.docker.com/compose/ — confirmed via research record).

**Steps.**
1. Read `bronze/run.py` (whole), `bronze/lander.py:44-54` (crash site), `bronze/config.py:11-16` (S3 settings), `scripts/minio_smoke.py` (fail-soft idiom), `bronze/live_check.py` (`write_manifest`), `docker-compose.yml`, `docs/CODEMAP.md:40`.
2. Add a cheap `_storage_reachable() -> bool` preflight: construct the `s3fs.S3FileSystem` from `bronze.config` and `try: fs.exists(BRONZE_BUCKET); return True except Exception as exc: logger.warning(...); return False`. Do NOT import-time construct `RawLander`.
3. Wrap each batch so it degrades, never raises: a helper `_run_batch(name, fn, *, evidence_dir)` that, if storage is unreachable OR `fn()` raises, logs a warning and writes a degraded run-evidence manifest (`status: "degraded"`, `storage_reachable: false`/`error: <repr>`, UTC timestamp, batch name) via a small JSON writer (reuse `write_manifest` style) and returns a status; on success writes `status: "ok"`. Default evidence dir under `output/evidence/scheduler/` (configurable).
4. Make `run_stats()`/`run_news()` callable through the wrapper (keep their one-off CLI behavior). Make the `schedule` loop body resilient: wrap `schedule.run_pending()` in try/except so one bad batch never kills cadence; keep `sleep(60)`. Boot batch runs through the same wrapper (no crash on MinIO-down boot).
5. Keep CLI modes working (`stats|news|all|schedule`); preserve the `__doc__`/usage fallback. Refactor the loop body into a testable `_tick()`-style seam.
6. **Deployable host (compose):** add a `scheduler` service to `docker-compose.yml`: builds/runs the project image (add a minimal `Dockerfile` if none exists, installing the package + runtime deps), command `python -m railway_lakehouse.bronze.run schedule`, `depends_on: minio`, `restart: unless-stopped`, env wired from `.env` with `S3_ENDPOINT=http://minio:9000`. Keep MinIO creds as the existing local-only defaults.
7. **Native alternative + runbook:** document a systemd-timer (or cron) alternative running `python -m railway_lakehouse.bronze.run all` on the stats/news cadence (restart-safe because the host re-fires the timer), plus a one-line runbook. Put it in `README.md` and a new `docs/OPERATIONS.md` (scheduler deploy + degrade behavior + how to read the run-evidence manifest). Keep `docs/CODEMAP.md` accurate.
8. **Deterministic test** `tests/test_bronze_scheduler.py`, `pytestmark = pytest.mark.unit`, no Docker/network (monkeypatch + `tmp_path` + fixed clock style of `tests/test_infra_minio.py`/`tests/test_bronze_live_check.py`):
   - monkeypatch the batch fn (or `RawLander`) to raise a connection error; assert the wrapped batch **does not raise**, returns a degraded status, and writes a manifest with `status == "degraded"`/`storage_reachable == false` under `tmp_path`.
   - assert `_storage_reachable()` returns `False` (not raises) when the fs `exists` call raises.
   - assert the loop body (`_tick()`) swallows a batch exception (patch it to raise once; assert no propagation).
   - success path: batch fn succeeds → manifest `status == "ok"`.
9. Run `python -m pytest -q -m unit tests/test_bronze_scheduler.py` then full `python -m pytest -q`; both green. `python -m compileall -q src tests` clean. `git diff --check` clean.
10. Append a `docs/GAP_REGISTER.md` Test Failure Mapping row (exact command + result + `GAP-019`) and flip GAP-019 toward `closed` with evidence + the runbook line. Sync `docs/TASKS.md` + `docs/index.html` (Wave 4 "deployable automatic updates" / Contract C) if state advances.

**Files to touch:** `src/railway_lakehouse/bronze/run.py` · `docker-compose.yml` · `Dockerfile` (new, only if none exists) · `docs/OPERATIONS.md` (new) · `README.md` · `docs/CODEMAP.md` · `tests/test_bronze_scheduler.py` (new) · `docs/GAP_REGISTER.md`. Do NOT change `bronze/lander.py` write semantics.

**Definition of Done (contract).**
- [ ] A MinIO-unreachable boot **degrades** (warns + writes a `status: "degraded"` manifest) instead of raising; `_storage_reachable()` returns `False` rather than crashing.
- [ ] The `schedule` loop body is wrapped so one failing batch never kills cadence.
- [ ] A deployable host exists: a `scheduler` service in `docker-compose.yml` (`depends_on: minio`, `restart: unless-stopped`, runs `bronze.run schedule`) AND a documented systemd-timer/cron alternative; a one-line runbook in `README.md` + `docs/OPERATIONS.md`.
- [ ] Bronze write semantics unchanged (lander still append/accumulate, bytes-then-meta); no Silver/Gold/LLM/numeric changes.
- [ ] New `tests/test_bronze_scheduler.py` (`pytest.mark.unit`, no Docker/network) covers: degraded batch on connection error (no raise + degraded manifest), `_storage_reachable()` false-on-error, loop body swallows a batch exception, success path manifest `ok`.
- [ ] `python -m pytest -q -m unit tests/test_bronze_scheduler.py` green; full `python -m pytest -q` green; `python -m compileall -q src tests` clean; `git diff --check` clean.
- [ ] `docs/GAP_REGISTER.md` mapping row + GAP-019 status/evidence; dashboard synced if state changed.

**Verify:** `python -m pytest -q -m unit tests/test_bronze_scheduler.py  (then full gate: python -m pytest -q)`

**Pitfalls.** Do NOT touch `RawLander.land()` / write semantics — only the scheduler's construction/error-handling + preflight. `depends_on` does NOT wait for MinIO readiness — the fail-soft preflight is the real protection. `schedule` has no cross-restart persistence (by design) — restart-safety comes from the host (`restart: unless-stopped` / systemd timer), not in-process state; don't try to persist `schedule` state. Degrade path must not partially write — skip the batch entirely on unreachable storage. Tests deterministic: monkeypatch fs/lander + clock; no network/Docker; write only under `tmp_path`. Scheduler run-evidence manifests under `output/evidence/scheduler/` (or tmp in tests) — never repo root. Don't break the one-off CLI modes or `__doc__` fallback.

## How to work
- Drive this with your **`$ship-it`** workflow, with **NO Linear** — all context lives in
  this repo's code and docs (`AGENTS.md`, `docs/GAP_TASKS.md`, `docs/GAP_REGISTER.md`,
  `docs/DATA_CONTRACTS.md`, `docs/TASKS.md`, `docs/STATE_AND_ROADMAP.md`). Do not look for or
  expect a ticket.
- First write **one** implementation plan, **review and approve it yourself**, then implement
  strictly against that approved plan. Keep the plan scoped to this gap only.
- If you need ANY external research (docker-compose service syntax, systemd timer unit syntax,
  s3fs/botocore exception types), use the **`/research-orchestrator`** skill and route through its
  MCP providers. Cite source URLs; record/extend research in
  `.planning/coursework/research/bigdata/gap019-deployable-scheduler-spec-2026-06-24.md`.
- Write the **unit tests** above (deterministic, no Docker/network). A bounded live cross-check
  against the running MinIO (localhost:9000) is OPTIONAL evidence, not the closure test.
- Run the task's **Verify** command and the full suite (`python -m pytest -q`) and make them
  green before you open the PR.
- This advances/closes a gap → update `docs/GAP_REGISTER.md`, and `docs/TASKS.md` + `docs/index.html`
  in the SAME change if state changes (AGENTS dashboard-sync Hard Rule) or CI will flag it.
- Branch `impl/gap-019` is already checked out in this worktree. Commit, push to origin, and
  open a PR against `main` with `gh` (you have write access).

## Definition of done (do not stop until ALL are true)
- The task's Definition-of-Done checklist items are met.
- `python -m pytest -q` is green; `python -m compileall -q src tests` clean.
- A PR against `main` exists and is **mergeable** (no conflicts, CI reminder satisfied).

## Final output
When done, your final message MUST be a single JSON object: the branch, PR url+number,
which test tiers you ran and their result, whether it is mergeable, which Definition-of-Done
items are met, and (if you had to stop early) blocked=true with the blocker. No prose outside the JSON.
