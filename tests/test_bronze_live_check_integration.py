import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from railway_lakehouse.bronze import live_check


pytestmark = pytest.mark.integration


FIXED_NOW = datetime(2026, 6, 22, 10, 15, tzinfo=timezone.utc)


def _xlsx_bytes():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<Relationships/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


def test_ksh_live_check_writes_manifest_and_bronze_artifact(monkeypatch, tmp_path):
    workbook = _xlsx_bytes()
    table = live_check.ksh.KshTable(
        "ksh_rail_fixture",
        "fixture",
        "Fixture rail table",
        "rail_fixture_metric",
    )

    class Response:
        status_code = 200
        content = workbook
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

    def fake_get(url, timeout, headers):
        assert url == table.url
        assert timeout == 3
        assert headers["User-Agent"] == live_check.USER_AGENT
        return Response()

    monkeypatch.setattr(live_check.ksh, "KSH_RAIL_TABLES", [table])
    monkeypatch.setattr(live_check.requests, "get", fake_get)

    manifest_path = live_check.run_live_check(
        sources=["ksh"],
        out=tmp_path / "evidence",
        max_artifacts=1,
        timeout_seconds=3,
        clock=lambda: FIXED_NOW,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "live-check-20260622-101500"
    assert manifest["artifact_count"] == 1
    assert manifest["byte_count"] == len(workbook)
    assert manifest["sources"][0]["source"] == "ksh"
    assert manifest["sources"][0]["status"] == "passed"
    assert manifest["sources"][0]["artifact_count"] == 1
    assert manifest["sources"][0]["http_statuses"] == [200]
    assert manifest["sources"][0]["failures"] == []

    artifact = manifest["artifacts"][0]
    raw_path = Path(artifact["path"])
    meta_path = Path(artifact["meta_path"])
    assert raw_path.read_bytes() == workbook
    assert meta_path.exists()

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["source_system"] == "ksh"
    assert meta["domain"] == "stats"
    assert meta["dataset_id"] == "ksh_rail_fixture"
    assert meta["original_filename"] == "fixture.xlsx"
    assert meta["extra"]["stadat_code"] == "fixture"
    assert meta["extra"]["discovery"] == "curated_rail_table"
