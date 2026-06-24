import json
from datetime import datetime, timezone

import pytest

from railway_lakehouse.bronze import run as bronze_run

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 6, 24, 2, 0, tzinfo=timezone.utc)


def _read_manifest(tmp_path):
    manifests = list(tmp_path.glob("*.json"))
    assert len(manifests) == 1
    return json.loads(manifests[0].read_text(encoding="utf-8"))


def test_run_batch_degrades_connection_error_and_writes_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(bronze_run, "_storage_reachable", lambda: True)

    def failing_batch():
        raise ConnectionError("minio unavailable")

    result = bronze_run._run_batch(
        "stats",
        failing_batch,
        evidence_dir=tmp_path,
        clock=lambda: FIXED_NOW,
    )

    assert result["status"] == "degraded"
    assert result["storage_reachable"] is False

    manifest = _read_manifest(tmp_path)
    assert manifest["batch"] == "stats"
    assert manifest["status"] == "degraded"
    assert manifest["storage_reachable"] is False
    assert "ConnectionError" in manifest["error"]


def test_storage_reachable_returns_false_when_exists_raises(monkeypatch):
    class UnreachableS3:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def exists(self, bucket):
            raise OSError(f"{bucket} unavailable")

    monkeypatch.setattr(bronze_run.s3fs, "S3FileSystem", UnreachableS3)

    assert bronze_run._storage_reachable() is False


def test_tick_swallows_scheduler_exception():
    class FailingScheduler:
        def run_pending(self):
            raise RuntimeError("scheduled batch failed")

    assert bronze_run._tick(FailingScheduler()) is False


def test_run_batch_success_writes_ok_manifest(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(bronze_run, "_storage_reachable", lambda: True)

    result = bronze_run._run_batch(
        "news",
        lambda: calls.append("ran"),
        evidence_dir=tmp_path,
        clock=lambda: FIXED_NOW,
    )

    assert calls == ["ran"]
    assert result["status"] == "ok"
    assert result["storage_reachable"] is True

    manifest = _read_manifest(tmp_path)
    assert manifest["batch"] == "news"
    assert manifest["status"] == "ok"
    assert manifest["storage_reachable"] is True
    assert "error" not in manifest
