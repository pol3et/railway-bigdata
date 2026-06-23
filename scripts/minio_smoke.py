"""
Smoke-check the live MinIO lakehouse path (GAP-010).

This script verifies that the local Docker MinIO stack is usable by the same
S3-compatible settings used by the project. It performs a bounded write/read
round-trip and records evidence under output/evidence/minio-smoke/manifest.json.

Run after:

    cp .env.example .env
    docker compose up -d
    python scripts/minio_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import s3fs


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()

from railway_lakehouse.bronze.config import (
    BRONZE_BUCKET,
    S3_ENDPOINT,
    S3_KEY,
    S3_SECRET,
)
from railway_lakehouse.silver.config import SILVER_BUCKET


GOLD_BUCKET = os.environ.get("GOLD_BUCKET", "gold")
EVIDENCE_DIR = Path("output/evidence/minio-smoke")
EVIDENCE_PATH = EVIDENCE_DIR / "manifest.json"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    started_at = datetime.now(timezone.utc).isoformat()

    fs = s3fs.S3FileSystem(
        key=S3_KEY,
        secret=S3_SECRET,
        client_kwargs={"endpoint_url": S3_ENDPOINT},
    )

    buckets = [BRONZE_BUCKET, SILVER_BUCKET, GOLD_BUCKET]
    created_or_existing = []

    for bucket in buckets:
        if not fs.exists(bucket):
            fs.mkdir(bucket)
        created_or_existing.append(bucket)

    payload = b"railway-lakehouse minio smoke ok"
    smoke_key = f"{BRONZE_BUCKET}/_smoke/hello.txt"

    with fs.open(smoke_key, "wb") as f:
        f.write(payload)

    with fs.open(smoke_key, "rb") as f:
        data = f.read()

    roundtrip_ok = data == payload

    # Keep the bucket clean: the manifest below is local evidence, not a MinIO object.
    fs.rm(smoke_key)

    manifest = {
        "status": "passed" if roundtrip_ok else "failed",
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": S3_ENDPOINT,
        "buckets": created_or_existing,
        "smoke_key": smoke_key,
        "bytes_written": len(payload),
        "bytes_read": len(data),
        "roundtrip_ok": roundtrip_ok,
        "evidence_path": EVIDENCE_PATH.as_posix(),
        "notes": (
            "MinIO Docker stack is reachable through s3fs; bronze/silver/gold "
            "buckets exist; bounded write/read/delete round-trip succeeded."
        ),
    }

    _write_json(EVIDENCE_PATH, manifest)

    if not roundtrip_ok:
        print(f"FAILED: round-trip mismatch; evidence written to {EVIDENCE_PATH}", file=sys.stderr)
        return 1

    print(f"OK: wrote+read {len(data)} bytes at {S3_ENDPOINT}/{smoke_key}")
    print(f"Evidence: {EVIDENCE_PATH}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        manifest = {
            "status": "failed",
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "endpoint": S3_ENDPOINT,
            "error": str(exc),
            "hint": "Is MinIO up? Run: docker compose up -d",
            "evidence_path": EVIDENCE_PATH.as_posix(),
        }
        _write_json(EVIDENCE_PATH, manifest)
        print(f"FAILED: {exc}", file=sys.stderr)
        print("Is MinIO up? Run: docker compose up -d", file=sys.stderr)
        print(f"Evidence: {EVIDENCE_PATH}", file=sys.stderr)
        sys.exit(1)
