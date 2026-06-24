"""
Bronze orchestrator.

Two cadences, matching the requirements:
  * stats  -> yearly  (Eurostat + World Bank; national agencies plug in here)
  * news   -> weekly  (GDELT + RSS)

Usage:
    python -m railway_lakehouse.bronze.run stats     # one-off stats pull
    python -m railway_lakehouse.bronze.run news      # one-off news pull
    python -m railway_lakehouse.bronze.run all       # both, once
    python -m railway_lakehouse.bronze.run schedule  # run continuously
"""
import sys
import time
import logging
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

import schedule
import s3fs

from .config import BRONZE_BUCKET, S3_ENDPOINT, S3_KEY, S3_SECRET
from .lander import RawLander
from .sources import eurostat, worldbank, gdelt, rss_media

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bronze.run")

DEFAULT_EVIDENCE_DIR = Path(os.environ.get("SCHEDULER_EVIDENCE_DIR", "output/evidence/scheduler"))


class _Scheduler(Protocol):
    def run_pending(self) -> object:
        ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _storage_reachable() -> bool:
    try:
        fs = s3fs.S3FileSystem(
            key=S3_KEY,
            secret=S3_SECRET,
            client_kwargs={"endpoint_url": S3_ENDPOINT},
        )
        fs.exists(BRONZE_BUCKET)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bronze storage preflight failed: %r", exc)
        return False


def _is_storage_exception(exc: Exception) -> bool:
    storage_exception_names = (
        "ConnectionError",
        "EndpointConnectionError",
        "ClientConnectorError",
        "ConnectTimeout",
        "ReadTimeout",
    )
    return isinstance(exc, (ConnectionError, OSError, TimeoutError)) or any(
        name in type(exc).__name__ for name in storage_exception_names
    )


def _write_scheduler_manifest(evidence_dir: str | Path, payload: dict) -> Path:
    out = Path(evidence_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = payload["timestamp_utc"].replace("+00:00", "Z").replace("-", "").replace(":", "")
    manifest_path = out / f"{payload['batch']}-{timestamp}.json"
    payload["evidence_path"] = manifest_path.as_posix()
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def _run_batch(
    name: str,
    fn: Callable[[], None],
    *,
    evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR,
    clock: Callable[[], datetime] = _utcnow,
) -> dict:
    now = clock()
    base_payload = {
        "batch": name,
        "timestamp_utc": now.isoformat(),
        "endpoint": S3_ENDPOINT,
        "bucket": BRONZE_BUCKET,
    }

    if not _storage_reachable():
        logger.warning("Bronze %s batch degraded: storage is unreachable", name)
        payload = {
            **base_payload,
            "status": "degraded",
            "storage_reachable": False,
            "error": "storage preflight failed",
        }
        _write_scheduler_manifest(evidence_dir, payload)
        return payload

    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        storage_reachable = not _is_storage_exception(exc)
        logger.warning("Bronze %s batch degraded: %r", name, exc, exc_info=True)
        payload = {
            **base_payload,
            "status": "degraded",
            "storage_reachable": storage_reachable,
            "error": repr(exc),
        }
        _write_scheduler_manifest(evidence_dir, payload)
        return payload

    payload = {
        **base_payload,
        "status": "ok",
        "storage_reachable": True,
    }
    _write_scheduler_manifest(evidence_dir, payload)
    return payload


def _run_stats_batch() -> None:
    logger.info("=== Bronze STATS batch ===")
    lander = RawLander()
    eurostat.ingest(lander)
    worldbank.ingest(lander)
    # GAP-005: national agencies are present but not scheduled yet.
    logger.info("=== STATS batch complete ===")


def _run_news_batch() -> None:
    logger.info("=== Bronze NEWS batch ===")
    lander = RawLander()
    gdelt.ingest(lander, timespan="1w")
    rss_media.ingest(lander)
    logger.info("=== NEWS batch complete ===")


def run_stats(*, evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR) -> dict:
    return _run_batch("stats", _run_stats_batch, evidence_dir=evidence_dir)


def run_news(*, evidence_dir: str | Path = DEFAULT_EVIDENCE_DIR) -> dict:
    return _run_batch("news", _run_news_batch, evidence_dir=evidence_dir)


def _tick(scheduler: _Scheduler | None = None) -> bool:
    active_scheduler = scheduler or schedule
    try:
        active_scheduler.run_pending()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Scheduler tick degraded: %r", exc, exc_info=True)
        return False


def _run_scheduler_loop() -> None:
    run_stats()
    run_news()
    schedule.every().sunday.at("02:00").do(run_news)          # weekly
    schedule.every(365).days.at("03:00").do(run_stats)        # yearly
    logger.info("Scheduler started (news weekly, stats yearly).")
    while True:
        _tick()
        time.sleep(60)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "stats":
        run_stats()
    elif mode == "news":
        run_news()
    elif mode == "all":
        run_stats()
        run_news()
    elif mode == "schedule":
        _run_scheduler_loop()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
