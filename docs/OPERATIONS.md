# Operations

## Bronze Scheduler

Purpose: keep the Bronze automatic-update path deployable and fault-tolerant without changing raw landing semantics.

One-line runbook:

```bash
docker compose up -d minio createbuckets scheduler && docker compose logs -f scheduler
```

Run-evidence manifests are written under:

```text
output/evidence/scheduler/
```

Each manifest records:

- `batch`: `stats` or `news`
- `status`: `ok` or `degraded`
- `storage_reachable`: whether the batch reached MinIO or degraded on a storage-like failure
- `timestamp_utc`, `endpoint`, `bucket`, and `evidence_path`
- `error` for degraded runs

`status: "degraded"` means the scheduler skipped or failed a batch, logged the error, wrote local evidence, and kept the process alive. This is expected when MinIO is unavailable during boot or a batch raises a connection error. The manifest is local evidence only; raw Bronze bytes still go through `RawLander` unchanged.

## Docker Compose Host

Start the local lakehouse plus scheduler:

```bash
cp .env.example .env
docker compose up -d minio createbuckets scheduler
docker compose logs -f scheduler
```

The `scheduler` service:

- builds the project image from `Dockerfile`
- runs `python -m railway_lakehouse.bronze.run schedule`
- uses `S3_ENDPOINT=http://minio:9000` inside the Compose network
- mounts `./output:/app/output` so manifests remain on the host
- uses `restart: unless-stopped`

`depends_on: minio` controls service start order, not MinIO readiness. The scheduler's S3 preflight is the readiness guard: if MinIO is still starting, the boot batch writes a degraded manifest and the loop continues.

## Native Timer Alternative

Use a host timer when you want restart-safe cadence without a long-running Python process. The one-shot command is:

```bash
python -m railway_lakehouse.bronze.run all
```

Example systemd service:

```ini
# /etc/systemd/system/railway-bronze-all.service
[Unit]
Description=Railway Bronze one-shot ingest

[Service]
Type=oneshot
WorkingDirectory=/opt/railway-bigdata
EnvironmentFile=/opt/railway-bigdata/.env
ExecStart=/usr/bin/python -m railway_lakehouse.bronze.run all
```

Example systemd timer with weekly news cadence plus yearly stats cadence through the same one-shot command:

```ini
# /etc/systemd/system/railway-bronze-all.timer
[Unit]
Description=Railway Bronze automatic updates

[Timer]
OnCalendar=Sun *-*-* 02:00:00
OnCalendar=*-01-01 03:00:00
Persistent=true
Unit=railway-bronze-all.service

[Install]
WantedBy=timers.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now railway-bronze-all.timer
systemctl list-timers railway-bronze-all.timer
```

Cron alternative:

```cron
# weekly automatic updates
0 2 * * 0 cd /opt/railway-bigdata && /usr/bin/python -m railway_lakehouse.bronze.run all >> output/evidence/scheduler/cron.log 2>&1
# yearly stats cadence
0 3 1 1 * cd /opt/railway-bigdata && /usr/bin/python -m railway_lakehouse.bronze.run all >> output/evidence/scheduler/cron.log 2>&1
```

For an exact split cadence, run `python -m railway_lakehouse.bronze.run news` from the weekly timer and `python -m railway_lakehouse.bronze.run stats` from the yearly timer. Both modes use the same fail-soft wrapper and manifest writer.
